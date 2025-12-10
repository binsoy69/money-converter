"""
PiBillHandler - hardware abstraction for bill acceptance, sorting, dispensing.

Now uses gpiozero for hardware primitives:
 - IR sensor -> DigitalInputDevice (active-low)
 - Motor -> Motor + PWMOutputDevice for speed control
 - White LED -> LED
 
Bill dispensing uses modular BillDispenser units:
 - Each denomination has its own dispenser (2 motors + 1 IR sensor)
 - Easy to add new denominations by registering new dispensers
 - Arduino only handles bill acceptance sorting (not dispensing)
"""

import time
import os
from typing import Optional, Tuple, Dict

# --- GPIOZero setup ---
try:
    from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice, DigitalOutputDevice, LED, Device
    ON_RPI = True
except Exception as e:
    print(f"[PiBillHandler] gpiozero import failed or factory init failed: {e}")
    print("[PiBillHandler] Falling back to MOCK mode.")
    ON_RPI = False
    # mocks for dev/off-Pi testing
    class Motor:
        def __init__(self, forward, backward): pass
        def forward(self): print("[MockMotor] forward")
        def backward(self): print("[MockMotor] backward")
        def stop(self): print("[MockMotor] stop")
        def close(self): pass
    class PWMOutputDevice:
        def __init__(self, pin): self.value = 0
        def off(self): self.value = 0
        def close(self): pass
    class DigitalInputDevice:
        def __init__(self, pin, pull_up=True): self.value = 1
        def close(self): pass
    class DigitalOutputDevice:
        def __init__(self, pin, active_high=True, initial_value=False): self.value = 0
        def on(self): self.value = 1
        def off(self): self.value = 0
        def close(self): pass
    class LED:
        def __init__(self, pin): pass
        def on(self): print("[MockWhite] ON")
        def off(self): print("[MockWhite] OFF")
        def close(self): pass

# Serial
try:
    import serial
except Exception:
    serial = None

# OpenCV + YOLO
try:
    import cv2
    from ultralytics import YOLO
except Exception:
    cv2 = None
    YOLO = None

# Storage
from .bill_storage import BillStorage


class BillDispenser:
    """
    Modular bill dispenser unit for a specific denomination.
    Each dispenser has 2 motors and 1 IR sensor.
    """
    def __init__(
        self,
        denomination: int,
        motor1_forward_pin: int,
        motor1_backward_pin: int,
        motor1_enable_pin: int,
        motor1_speed: float,
        motor2_forward_pin: int,
        motor2_backward_pin: int,
        motor2_enable_pin: int,
        motor2_speed: float,
        ir_sensor_pin: int,
        use_hardware: bool = True
    ):
        self.denomination = denomination
        self.motor1_speed = motor1_speed
        self.motor2_speed = motor2_speed
        
        if use_hardware and ON_RPI:
            try:
                # Try PWM first
                self.motor1 = Motor(forward=motor1_forward_pin, backward=motor1_backward_pin)
                self.motor1_enable = PWMOutputDevice(motor1_enable_pin)
                
                self.motor2 = Motor(forward=motor2_forward_pin, backward=motor2_backward_pin)
                self.motor2_enable = PWMOutputDevice(motor2_enable_pin)
            except Exception as e:
                print(f"[Dispenser-{denomination}] PWM init failed ({e}), falling back to Digital (Non-PWM).")
                # Fallback to non-PWM
                self.motor1 = Motor(forward=motor1_forward_pin, backward=motor1_backward_pin, pwm=False)
                self.motor1_enable = DigitalOutputDevice(motor1_enable_pin)
                
                self.motor2 = Motor(forward=motor2_forward_pin, backward=motor2_backward_pin, pwm=False)
                self.motor2_enable = DigitalOutputDevice(motor2_enable_pin)

            self.ir_sensor = DigitalInputDevice(ir_sensor_pin)
        else:
            self.motor1 = Motor(forward=0, backward=0)
            self.motor1_enable = PWMOutputDevice(0)
            self.motor2 = Motor(forward=0, backward=0)
            self.motor2_enable = PWMOutputDevice(0)
            self.ir_sensor = DigitalInputDevice(0)
    
    def check_ir(self) -> bool:
        """
        Check if bill is detected by IR sensor.
        Returns True if bill detected, False otherwise.
        IR sensor is active-low: LOW (False) = bill detected
        """
        return not self.ir_sensor.value

    def start_transport(self):
        """Start Motor 2 (Transport) continuously."""
        self.motor2_enable.value = self.motor2_speed
        self.motor2.forward()
        print(f"[Dispenser-{self.denomination}] Transport (M2) started at {self.motor2_speed*100:.0f}%")

    def stop_transport(self):
        """Stop Motor 2 (Transport)."""
        self.motor2.stop()
        self.motor2_enable.off()
        print(f"[Dispenser-{self.denomination}] Transport (M2) stopped")

    def pulse_feeder(self, duration_s: float):
        """Run Motor 1 (Feeder) forward for specified duration."""
        self.motor1_enable.value = self.motor1_speed
        self.motor1.forward()
        print(f"[Dispenser-{self.denomination}] Feeder (M1) pulsing for {duration_s}s at {self.motor1_speed*100:.0f}%...")
        time.sleep(duration_s)
        self.motor1.stop()
        self.motor1_enable.off()
        print(f"[Dispenser-{self.denomination}] Feeder (M1) stopped")

    def wait_for_bill(self, timeout_s: float = 1.0) -> bool:
        """
        Wait for IR sensor to detect a bill within timeout.
        Returns True if detected, False if timeout.
        """
        start_time = time.time()
        # print(f"[Dispenser-{self.denomination}] Waiting for bill detection (timeout {timeout_s}s)...")
        while time.time() - start_time < timeout_s:
            if self.check_ir():
                return True
            time.sleep(0.05)  # Small delay to prevent CPU hogging
        return False

    def dispense(
        self,
        qty: int,
        dispense_duration_s: float = 0.25,
        max_retry_attempts: int = 5,
        ir_poll_timeout_s: float = 1.0
    ) -> Tuple[bool, str]:
        """
        Dispense a specified number of bills using the logic from test_bill_dispenser_ir.py.
        Motor 2 (Transport) runs continuously. Motor 1 (Feeder) pulses to feed bills.
        """
        print(f"\n[Dispenser-{self.denomination}] Starting dispense of {qty} bill(s)")
        
        successful_dispenses = 0
        # if UI is used code will stop here, code 134, unhandled exception aborted
        try:
            # Start Motor 2 (Transport)
            self.start_transport()
            
            # Give Motor 2 a moment to spin up
            time.sleep(0.5)
            for i in range(1, qty + 1):
                print(f"\n[Dispenser-{self.denomination}] --- Dispensing Bill {i}/{qty} ---")
                bill_dispensed = False
                
                for attempt in range(1, max_retry_attempts + 1):
                    if attempt > 1:
                        print(f"[Dispenser-{self.denomination}] Retry attempt {attempt}/{max_retry_attempts}...")
                    
                    # Pulse Motor 1 (Feeder)
                    print("DISPENSE BEFORE MOTOR 1")
                    self.pulse_feeder(dispense_duration_s)
                    print("DISPENSE AFTER MOTOR 1")
                    
                    # Wait for IR detection
                    if self.wait_for_bill(timeout_s=ir_poll_timeout_s):
                        print(f"[Dispenser-{self.denomination}] SUCCESS: Bill {i} detected!")
                        bill_dispensed = True
                        successful_dispenses += 1
                        # Small delay between bills to ensure separation
                        time.sleep(0.5) 
                        break
                    else:
                        print(f"[Dispenser-{self.denomination}] No bill detected.")
                
                if not bill_dispensed:
                    error_msg = f"bill_{i}_not_detected_after_{max_retry_attempts}_attempts"
                    print(f"[Dispenser-{self.denomination}] FAILED: {error_msg}")
                    return False, error_msg
        
        except Exception as e:
            print(f"[Dispenser-{self.denomination}] Exception during dispense: {e}")
            return False, str(e)
        finally:
            # Always stop Motor 2 at the end
            self.stop_transport()

        print(f"[Dispenser-{self.denomination}] Dispense complete. Success: {successful_dispenses}/{qty}")
        return True, "dispensed"
    
    def cleanup(self):
        """Release GPIO resources."""
        try:
            self.motor1.close()
            self.motor2.close()
            self.motor1_enable.close()
            self.motor2_enable.close()
            self.ir_sensor.close()
        except Exception as e:
            print(f"[Dispenser-{self.denomination}] Cleanup failed: {e}")


class PiBillHandler:
    def __init__(
        self,
        ir_pin: int = 17,
        motor_forward_pin = 24,
        motor_backward_pin = 23,
        motor_enable_pin: int = 18,   # ENA pin (PWM capable)
        white_led_pin: int = 27,
        sorter_serial_port: str = "/dev/ttyACM0",
        sorter_baud: int = 9600,
        speed: float = 0.4,  # Motor speed (0.0–1.0)
        use_hardware: Optional[bool] = None,
        uv_model_path: Optional[str] = None,
        denom_model_path: Optional[str] = None,
        serial_manager = None, # New shared serial manager (CoinHandlerSerial instance)
    ):
        self.ir_pin = ir_pin
        self.motor_forward_pin = motor_forward_pin
        self.motor_backward_pin = motor_backward_pin
        self.motor_enable_pin = motor_enable_pin
        self.white_led_pin = white_led_pin
        self.sorter_serial_port = sorter_serial_port
        self.sorter_baud = sorter_baud
        self.speed = speed
        self.serial_manager = serial_manager

        self.use_hardware = ON_RPI if use_hardware is None else use_hardware

        if self.use_hardware and ON_RPI:
            try:
                # Try PWM first
                self.motor = Motor(forward=self.motor_forward_pin, backward=self.motor_backward_pin)
                self.enable_pin = PWMOutputDevice(self.motor_enable_pin)
            except Exception as e:
                print(f"[PiBillHandler] PWM init failed ({e}), falling back to Digital (Non-PWM).")
                # Fallback to non-PWM motor control
                self.motor = Motor(forward=self.motor_forward_pin, backward=self.motor_backward_pin, pwm=False)
                # Use DigitalOutputDevice for enable pin (ON/OFF only, no speed control)
                self.enable_pin = DigitalOutputDevice(self.motor_enable_pin)
            
            self.ir_sensor = DigitalInputDevice(self.ir_pin)  # active-low
            self.white_led = LED(self.white_led_pin)
        else:
            self.motor = Motor(forward=0, backward=0)
            self.enable_pin = PWMOutputDevice(0)
            self.ir_sensor = DigitalInputDevice(0)
            self.white_led = LED(0)

        # Bill dispensers registry (denomination -> BillDispenser)
        self.dispensers: Dict[int, BillDispenser] = {}

        # Serial sorter (Shared manager or individual)

        self.sorter_serial = None
        
        # NOTE: serial_manager logic is handled if passed later or we can add it to init now.
        # But to avoid breaking existing signatures too much, we will handle it via setter or optional param.
        # However, plan says modify init. Let's look at init again. It has many params. 
        # I will add it as kwargs or just member variable injection if strictly following plan.
        
        # ACTUALLY, I will add it as a parameter to __init__ in the next chunk, so I'll just init it here.
        # But wait, I need to prevent _open_sorter_serial if manager is used.


        # Storage
        self.storage = BillStorage()

        # Model loading
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        if uv_model_path is None:
            uv_model_path = os.path.join(self.script_dir, '..', 'models', "uv_cls_v2_ncnn_model")
        if denom_model_path is None:
            denom_model_path = os.path.join(self.script_dir, '..', 'models', "denom-cls-v2_ncnn_model")

        self.uv_model = None
        self.denom_model = None
        self.uv_labels = []
        self.denom_labels = []

        if YOLO is not None:
            try:
                self.uv_model = YOLO(uv_model_path, task='classify')
                self.denom_model = YOLO(denom_model_path, task='classify')
                self.uv_labels = getattr(self.uv_model, "names", [])
                self.denom_labels = getattr(self.denom_model, "names", [])
            except Exception as e:
                print("[PiBillHandler] YOLO model load failed:", e)

    # -------------------------
    # Dispenser Management
    # -------------------------
    def register_dispenser(
        self,
        denomination: int,
        motor1_forward_pin: int,
        motor1_backward_pin: int,
        motor1_enable_pin: int,
        motor1_speed: float,
        motor2_forward_pin: int,
        motor2_backward_pin: int,
        motor2_enable_pin: int,
        motor2_speed: float,
        ir_sensor_pin: int
    ):
        """
        Register a bill dispenser for a specific denomination.
        This makes it easy to add new denominations in the future.
        
        Example:
            handler.register_dispenser(
                denomination=20,
                motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16, motor1_speed=0.5,
                motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13, motor2_speed=0.6,
                ir_sensor_pin=12
            )
        """
        dispenser = BillDispenser(
            denomination=denomination,
            motor1_forward_pin=motor1_forward_pin,
            motor1_backward_pin=motor1_backward_pin,
            motor1_enable_pin=motor1_enable_pin,
            motor1_speed=motor1_speed,
            motor2_forward_pin=motor2_forward_pin,
            motor2_backward_pin=motor2_backward_pin,
            motor2_enable_pin=motor2_enable_pin,
            motor2_speed=motor2_speed,
            ir_sensor_pin=ir_sensor_pin,
            use_hardware=self.use_hardware
        )
        self.dispensers[denomination] = dispenser
        print(f"[PiBillHandler] Registered dispenser for denomination: {denomination}")

    # -------------------------
    # Hardware primitives
    # -------------------------
    def read_ir(self) -> bool:
        """Return True if bill detected (active-low)."""
        return not self.ir_sensor.value

    def motor_forward(self):
        self.enable_pin.value = self.speed
        self.motor.forward()
        print("[Motor] Forward")

    def motor_reverse(self):
        self.enable_pin.value = self.speed
        self.motor.backward()
        print("[Motor] Reverse")

    def motor_stop(self):
        self.motor.stop()
        self.enable_pin.off()
        print("[Motor] Stop")

    def white_on(self):
        self.white_led.on()

    def white_off(self):
        self.white_led.off()

    # -------------------------
    # Serial sorter
    # -------------------------
    def _open_sorter_serial(self, attempts: int = 3, delay_s: float = 1.0):
        # If we have a manager, we don't need this.
        if self.serial_manager:
            return

        for attempt in range(attempts):
            try:
                if serial is None:
                    self.sorter_serial = None
                    return
                self.sorter_serial = serial.Serial(self.sorter_serial_port, self.sorter_baud, timeout=1)
                return
            except Exception as e:
                print(f"[PiBillHandler] sorter open attempt {attempt+1} failed: {e}")
                time.sleep(delay_s)
        self.sorter_serial = None
        print("[PiBillHandler] sorter serial not available (mock mode)")

    def sort_via_arduino(self, denom: int, timeout_s: float = 60.0) -> bool:
        """Send SORT command to Arduino (used only for bill acceptance, not dispensing)."""
        
        # 1. Use Shared Manager if valid
        if self.serial_manager:
            return self.serial_manager.send_sort_command(denom, timeout_s=timeout_s)

        # 2. Fallback to individual serial
        cmd = f"SORT:{denom}\n"
        if self.sorter_serial is None:
            print("[PiBillHandler] sorter serial missing; assuming success (mock).")
            return True
        try:
            self.sorter_serial.write(cmd.encode("utf-8"))
        except Exception as e:
            print("[PiBillHandler] sorter write failed:", e)
            return False

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                raw = self.sorter_serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                print("[PiBillHandler] sorter reply:", line)
                if "[OK]" in line or line == "OK" or line.endswith("OK"):
                    return True
                if "Error" in line or "ERR" in line:
                    return False
            except Exception:
                time.sleep(0.1)
        return False

    # -------------------------
    # Camera & YOLO
    # -------------------------
    def capture_image(self):
        if cv2 is None:
            print("[PiBillHandler] OpenCV not available for capture.")
            return None
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[PiBillHandler] Camera failed to open")
            return None
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    def run_inference(self, model, frame, labels):
        try:
            if frame is None:
                return None, 0.0
            resized = cv2.resize(frame, (480, 480))
            result = model.predict(resized, verbose=False)[0]
            if getattr(result, "probs", None) is None:
                return None, 0.0
            label_idx = int(result.probs.top1)
            return labels[label_idx], float(result.probs.top1conf)
        except Exception as e:
            print("[PiBillHandler] run_inference failed:", e)
            return None, 0.0

    def authenticate_bill(self) -> bool:
        print("[PiBillHandler] UV Scan (authenticity)...")
        frame = self.capture_image()
        if frame is None:
            return False
        if not self.uv_model:
            print("[PiBillHandler] UV model missing; assuming real (mock).")
            return True
        label, conf = self.run_inference(self.uv_model, frame, self.uv_labels)
        print(f"[UV] {label} ({conf*100:.1f}%)")
        return (conf >= 0.8) and (label == "genuine")

    def classify_denomination(self) -> Optional[int]:
        print("[PiBillHandler] White-light denomination classification...")
        self.white_on()
        time.sleep(0.3)
        frame = self.capture_image()
        self.white_off()
        if frame is None:
            return None
        if not self.denom_model:
            print("[PiBillHandler] denom model missing; returning default 100 (mock).")
            return 100
        label, conf = self.run_inference(self.denom_model, frame, self.denom_labels)
        if conf < 0.8:
            return None
        print(f"[Denom] {label} ({conf*100:.1f}%)")
        try:
            return int(label)
        except Exception:
            digits = ''.join(ch for ch in str(label) if ch.isdigit())
            return int(digits) if digits else None

    # -------------------------
    # High-level flows
    # -------------------------
    def accept_bill(
        self,
        required_denom: int,
        motor_forward_ms: int = 400,
        motor_reverse_ms: int = 1000,
        push_after_sort_ms: int = 1500,
        wait_for_ir_timeout_s: int = 60,
    ) -> Tuple[bool, Optional[int], str]:
        """Full accept flow (blocking). Uses Arduino SORT for bill acceptance."""
        start = time.time()
        while time.time() - start < wait_for_ir_timeout_s:
            if self.read_ir():
                break
            time.sleep(0.05)
        else:
            return False, None, "timeout_no_bill"
        print("Bill Inserted")
        time.sleep(1)
        self.motor_forward()
        time.sleep(motor_forward_ms / 1000.0)
        self.motor_stop()

        if not self.authenticate_bill():
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, None, "fake_bill"

        denom = self.classify_denomination()
        if denom is None:
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, None, "denom_unknown"

        if denom != required_denom:
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, denom, "denom_not_required"

        sorter_ok = self.sort_via_arduino(denom)
        if not sorter_ok:
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, denom, "sorter_no_ack"

        # Successfully sorted; push into storage
        self.motor_forward()
        self.storage.add(denom, 1)
        time.sleep(push_after_sort_ms / 1000.0)
        self.motor_stop()
        return True, denom, "accepted"

    # -------------------------
    # Bill Dispensing (Modular)
    # -------------------------
    def dispense_bill(
        self, 
        denom: int, 
        qty: int = 1, 
        dispense_duration_s: float = 0.25,
        max_retry_attempts: int = 5,
        ir_poll_timeout_s: float = 1.0
    ) -> Tuple[bool, str]:
        """
        Dispense bills using the registered dispenser for the specified denomination.
        No Arduino sorting needed - each denomination has its own dedicated dispenser.
        
        Args:
            denom: Bill denomination to dispense
            qty: Number of bills to dispense
            dispense_duration_s: Motor 1 (Feeder) pulse duration
            max_retry_attempts: Max retries if bill not detected
            ir_poll_timeout_s: Max time to wait for IR detection per bill
        
        Returns:
            (success: bool, message: str)
        """
        # Check if dispenser is registered
        if denom not in self.dispensers:
            return False, f"no_dispenser_registered_for_{denom}"
        
        dispenser = self.dispensers[denom]
        
        # Delegate to the dispenser's batch logic
        success, message = dispenser.dispense(
            qty=qty,
            dispense_duration_s=dispense_duration_s,
            max_retry_attempts=max_retry_attempts,
            ir_poll_timeout_s=ir_poll_timeout_s
        )
        
        if success:
            # Deduct from storage
            self.storage.deduct(denom, qty)
            return True, "dispensed"
        else:
            return False, message

    def cleanup(self):
        try:
            if self.sorter_serial and hasattr(self.sorter_serial, "close"):
                self.sorter_serial.close()
        except Exception:
            pass

        try:
            self.motor.close()
            self.enable_pin.close()
            self.ir_sensor.close()
            self.white_led.close()
            
            # Cleanup all registered dispensers
            for denom, dispenser in self.dispensers.items():
                dispenser.cleanup()
            
            print("[PiBillHandler] gpiozero pins released")
        except Exception as e:
            print("[PiBillHandler] gpiozero cleanup failed:", e)
