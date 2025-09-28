"""
PiBillHandler - hardware abstraction for bill acceptance, sorting, dispensing.

Now uses gpiozero for hardware primitives:
 - IR sensor -> DigitalInputDevice (active-low)
 - Motor -> Motor + PWMOutputDevice for speed control
 - White LED -> LED
"""

import time
import os
from typing import Optional, Tuple

# --- GPIOZero setup ---
try:
    from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice, LED, Device
    ON_RPI = True
except Exception:
    ON_RPI = False
    # mocks for dev/off-Pi testing
    class Motor:
        def __init__(self, forward, backward): pass
        def forward(self): print("[MockMotor] forward")
        def backward(self): print("[MockMotor] backward")
        def stop(self): print("[MockMotor] stop")
    class PWMOutputDevice:
        def __init__(self, pin): self.value = 0
        def off(self): self.value = 0
    class DigitalInputDevice:
        def __init__(self, pin, pull_up=True): self.value = 1
    class LED:
        def __init__(self, pin): pass
        def on(self): print("[MockWhite] ON")
        def off(self): print("[MockWhite] OFF")

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
        speed: float = 0.3,  # Motor speed (0.0–1.0)
        use_hardware: Optional[bool] = None,
        uv_model_path: Optional[str] = None,
        denom_model_path: Optional[str] = None,
    ):
        self.ir_pin = ir_pin
        self.motor_forward_pin = motor_forward_pin
        self.motor_backward_pin = motor_backward_pin
        self.motor_enable_pin = motor_enable_pin
        self.white_led_pin = white_led_pin
        self.sorter_serial_port = sorter_serial_port
        self.sorter_baud = sorter_baud
        self.speed = speed

        self.use_hardware = ON_RPI if use_hardware is None else use_hardware

        if self.use_hardware and ON_RPI:
            self.motor = Motor(forward=self.motor_forward_pin, backward=self.motor_backward_pin)
            self.enable_pin = PWMOutputDevice(self.motor_enable_pin)
            self.ir_sensor = DigitalInputDevice(self.ir_pin)  # active-low
            self.white_led = LED(self.white_led_pin)
        else:
            self.motor = Motor(forward=0, backward=0)
            self.enable_pin = PWMOutputDevice(0)
            self.ir_sensor = DigitalInputDevice(0)
            self.white_led = LED(0)

        # Serial sorter
        self.sorter_serial = None
        self._open_sorter_serial()

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

    def sort_via_arduino(self, denom: int, timeout_s: float = 10.0) -> bool:
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
        motor_forward_ms: int = 800,
        motor_reverse_ms: int = 1000,
        push_after_sort_ms: int = 500,
        wait_for_ir_timeout_s: int = 60,
    ) -> Tuple[bool, Optional[int], str]:
        """Full accept flow (blocking)."""
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

        self.storage.add(denom, 1)
        self.motor_forward()
        time.sleep(push_after_sort_ms / 1000.0)
        self.motor_stop()
        return True, denom, "accepted"

    def dispense_bill(self, denom: int, qty: int = 1, dispense_time_ms: int = 1500, serial_timeout_s: float = 10.0) -> Tuple[bool, str]:
        """
        Step-by-step handshake dispensing:
        1) Send PREP_DISPENSE:{denom}:{qty} to Arduino
        2) Wait for 'READY'
        3) For each bill: run DC motor for dispense_time_ms, send MOTOR_DONE:{i}, wait for 'ACK'
        4) After all, wait for 'DONE' from Arduino
        Returns (True,"dispensed") or (False,"reason")
        """
        try:
            # If no Arduino connected, just run motor cycles (mock/fallback)
            if self.sorter_serial is None:
                for i in range(qty):
                    self.motor_forward()
                    time.sleep(dispense_time_ms / 1000.0)
                    self.motor_stop()
                    time.sleep(0.3)
                return True, "dispensed_no_arduino"

            # 1) ask Arduino to prepare (H-bot down, move to denom, servo A push-in, servo B angle)
            prep_cmd = f"PREP_DISPENSE:{denom}:{qty}\n"
            try:
                self.sorter_serial.write(prep_cmd.encode("utf-8"))
            except Exception as e:
                return False, f"serial_write_failed:{e}"

            # helper: read lines until timeout
            deadline = time.time() + serial_timeout_s
            ready = False
            while time.time() < deadline:
                raw = self.sorter_serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
                if not line:
                    continue
                # Arduino should reply 'READY' when it's positioned
                if "READY" in line:
                    ready = True
                    break
                if "ERR" in line or "ERROR" in line:
                    return False, f"arduino_prep_error:{line}"
            if not ready:
                return False, "no_ready_from_arduino"

            # 2) For each bill: run DC motor then notify Arduino
            for i in range(qty):
                # run DC motor (time-based)
                self.motor_forward()
                time.sleep(dispense_time_ms / 1000.0)
                self.motor_stop()

                # notify Arduino that motor cycle finished
                done_cmd = f"MOTOR_DONE:{denom}:{i+1}\n"
                try:
                    self.sorter_serial.write(done_cmd.encode("utf-8"))
                except Exception as e:
                    return False, f"serial_write_failed_after_motor:{e}"

                # wait for ACK before next cycle
                ack_deadline = time.time() + serial_timeout_s
                ack_ok = False
                while time.time() < ack_deadline:
                    raw = self.sorter_serial.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
                    if not line:
                        continue
                    if "ACK" in line or "OK" == line or line.endswith("OK"):
                        ack_ok = True
                        break
                    if "ERR" in line or "ERROR" in line:
                        return False, f"arduino_error_during_cycle:{line}"
                if not ack_ok:
                    return False, "no_ack_from_arduino"

            # 3) Wait for Arduino to finish retracting / moving away after all cycles
            finish_deadline = time.time() + serial_timeout_s
            finished = False
            while time.time() < finish_deadline:
                raw = self.sorter_serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
                if not line:
                    continue
                if "DONE" in line or "FINISHED" in line:
                    finished = True
                    break
                if "ERR" in line or "ERROR" in line:
                    return False, f"arduino_finish_error:{line}"
            if not finished:
                return False, "no_done_from_arduino"

            return True, "dispensed"
        except Exception as e:
            return False, f"exception:{e}"


    def cleanup(self):
        try:
            if self.sorter_serial and hasattr(self.sorter_serial, "close"):
                self.sorter_serial.close()
        except Exception:
            pass

        try:
            self.motor.close()
            print("[PiBillHandler] gpiozero pins released")
        except Exception as e:
            print("[PiBillHandler] gpiozero cleanup failed:", e)

        