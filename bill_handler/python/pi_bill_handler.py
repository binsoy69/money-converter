# workers/pi_bill_handler.py
"""
PiBillHandler - hardware abstraction for bill acceptance, sorting, dispensing.

Assumptions / defaults (configurable in constructor):
 - IR (active-low) pin default: 17
 - Motor IN1 default: 22
 - Motor IN2 default: 27
 - Motor PWM pin default: None (no PWM)
 - White LED pin default: 5
 - UV LED is manually controlled (not toggled by this class)
 - Sorter serial: /dev/ttyUSB0 @ 9600 (adjust if needed)
 - motor timings default values used in accept/dismiss/dispense flows
 - YOLO models loaded using your snippet paths - ensure YOLO class available
"""

import time
import os
from typing import Optional, Tuple

# GPIO fallback
try:
    import RPi.GPIO as GPIO
    ON_RPI = True
except Exception:
    ON_RPI = False

    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        OUT = "OUT"
        PUD_UP = "PUD_UP"
        HIGH = 1
        LOW = 0

        def __init__(self):
            self._pins = {}

        def setmode(self, m): pass

        def setup(self, pin, mode, pull_up_down=None):
            self._pins[pin] = self.LOW

        def input(self, pin):
            return self._pins.get(pin, self.LOW)

        def output(self, pin, val):
            self._pins[pin] = val

        def PWM(self, pin, freq):
            class PWMInner:
                def __init__(self, pin): pass
                def start(self, duty): pass
                def ChangeDutyCycle(self, d): pass
                def stop(self): pass
            return PWMInner(pin)

        def cleanup(self): pass

    GPIO = MockGPIO()

# Serial fallback
try:
    import serial
except Exception:
    serial = None

    class MockSerialObj:
        def __init__(self, *args, **kwargs):
            self._in = []
            self._open = True

        def write(self, b):
            print("[MockSerial] write:", b)

        def readline(self):
            if self._in:
                return self._in.pop(0).encode("utf-8")
            time.sleep(0.1)
            return b""

        def close(self):
            self._open = False

    serial = MockSerialObj

# OpenCV and YOLO imports (your environment should have these available)
try:
    import cv2
except Exception:
    cv2 = None

# You provided a YOLO usage snippet; try to import YOLO (replace depending on your package)
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# BillStorage import (adjust path if needed)
from .bill_storage import BillStorage


class PiBillHandler:
    def __init__(
        self,
        ir_pin: int = 17,
        motor_in1: int = 22,
        motor_in2: int = 27,
        motor_pwm_pin: Optional[int] = None,
        white_led_pin: Optional[int] = 5,
        sorter_serial_port: str = "/dev/ttyUSB0",
        sorter_baud: int = 9600,
        use_hardware: Optional[bool] = None,
        uv_model_path: Optional[str] = None,
        denom_model_path: Optional[str] = None,
    ):
        self.ir_pin = ir_pin
        self.motor_in1 = motor_in1
        self.motor_in2 = motor_in2
        self.motor_pwm_pin = motor_pwm_pin
        self.white_led_pin = white_led_pin
        self.sorter_serial_port = sorter_serial_port
        self.sorter_baud = sorter_baud

        if use_hardware is None:
            self.use_hardware = ON_RPI
        else:
            self.use_hardware = use_hardware

        # Setup GPIO pins
        if self.use_hardware and ON_RPI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.ir_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # active-low
            GPIO.setup(self.motor_in1, GPIO.OUT)
            GPIO.setup(self.motor_in2, GPIO.OUT)
            if motor_pwm_pin is not None:
                GPIO.setup(motor_pwm_pin, GPIO.OUT)
                self._pwm = GPIO.PWM(motor_pwm_pin, 1000)
                self._pwm.start(0)
            else:
                self._pwm = None
            if self.white_led_pin is not None:
                GPIO.setup(self.white_led_pin, GPIO.OUT)
        else:
            self._pwm = None

        # Serial sorter - try to open (mock ok)
        self.sorter_serial = None
        self._open_sorter_serial()

        # Storage
        self.storage = BillStorage()

        # model loading (you provided paths previously)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        # if caller provided paths, prefer those; otherwise try defaults relative to scripts
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
                # load models (if present)
                self.uv_model = YOLO(uv_model_path, task='classify')
                self.denom_model = YOLO(denom_model_path, task='classify')
                self.uv_labels = getattr(self.uv_model, "names", [])
                self.denom_labels = getattr(self.denom_model, "names", [])
            except Exception as e:
                print("[PiBillHandler] YOLO model load failed:", e)

    # -------------------------
    # GPIO & motor primitives
    # -------------------------
    def read_ir(self) -> bool:
        """Return True if bill detected (active-low)."""
        if self.use_hardware and ON_RPI:
            return GPIO.input(self.ir_pin) == GPIO.LOW
        else:
            return GPIO.input(self.ir_pin) == GPIO.LOW

    def motor_forward(self, speed_pct: int = 80):
        if self.use_hardware and ON_RPI:
            GPIO.output(self.motor_in1, GPIO.HIGH)
            GPIO.output(self.motor_in2, GPIO.LOW)
            if self._pwm:
                self._pwm.ChangeDutyCycle(speed_pct)
        else:
            GPIO.output(self.motor_in1, GPIO.HIGH)
            GPIO.output(self.motor_in2, GPIO.LOW)
            print(f"[MockMotor] forward @ {speed_pct}%")

    def motor_reverse(self, speed_pct: int = 80):
        if self.use_hardware and ON_RPI:
            GPIO.output(self.motor_in1, GPIO.LOW)
            GPIO.output(self.motor_in2, GPIO.HIGH)
            if self._pwm:
                self._pwm.ChangeDutyCycle(speed_pct)
        else:
            GPIO.output(self.motor_in1, GPIO.LOW)
            GPIO.output(self.motor_in2, GPIO.HIGH)
            print(f"[MockMotor] reverse @ {speed_pct}%")

    def motor_stop(self):
        if self.use_hardware and ON_RPI:
            GPIO.output(self.motor_in1, GPIO.LOW)
            GPIO.output(self.motor_in2, GPIO.LOW)
            if self._pwm:
                self._pwm.ChangeDutyCycle(0)
        else:
            GPIO.output(self.motor_in1, GPIO.LOW)
            GPIO.output(self.motor_in2, GPIO.LOW)
            print("[MockMotor] stop")

    def white_on(self):
        if self.white_led_pin is None:
            return
        if self.use_hardware and ON_RPI:
            GPIO.output(self.white_led_pin, GPIO.HIGH)
        else:
            GPIO.output(self.white_led_pin, GPIO.HIGH)
            print("[MockWhite] ON")

    def white_off(self):
        if self.white_led_pin is None:
            return
        if self.use_hardware and ON_RPI:
            GPIO.output(self.white_led_pin, GPIO.LOW)
        else:
            GPIO.output(self.white_led_pin, GPIO.LOW)
            print("[MockWhite] OFF")

    # -------------------------
    # Serial sorter
    # -------------------------
    def _open_sorter_serial(self, attempts: int = 3, delay_s: float = 1.0):
        for attempt in range(attempts):
            try:
                if serial is None:
                    self.sorter_serial = None
                    return
                # If serial is a class (pyserial), instantiate; else assume mock class was assigned
                if hasattr(serial, "Serial"):
                    self.sorter_serial = serial.Serial(self.sorter_serial_port, self.sorter_baud, timeout=1)
                else:
                    # serial is a mock class
                    self.sorter_serial = serial(self.sorter_serial_port, self.sorter_baud)
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
                if isinstance(raw, bytes):
                    line = raw.decode("utf-8", errors="ignore").strip()
                else:
                    line = str(raw).strip()
                print("[PiBillHandler] sorter reply:", line)
                if "[OK]" in line or "OK" == line or line.endswith("OK"):
                    return True
                if "Error" in line or "ERR" in line:
                    return False
            except Exception:
                time.sleep(0.1)
        return False

    # -------------------------
    # Camera & YOLO helpers (use your snippet)
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
        # follow your provided snippet
        try:
            resized = None
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
        # UV is manually ON externally per your note
        frame = self.capture_image()
        if frame is None:
            return False
        if not self.uv_model:
            # if model unavailable, default to True for mock/testing
            print("[PiBillHandler] UV model missing; assuming real (mock).")
            return True
        label, conf = self.run_inference(self.uv_model, frame, self.uv_labels)
        print(f"[UV] {label} ({conf*100:.1f}%)")
        return (conf >= 0.8) and (label == "genuine")

    def classify_denomination(self) -> Optional[int]:
        print("[PiBillHandler] White-light denomination classification...")
        frame = self.capture_image()
        if frame is None:
            return None
        if not self.denom_model:
            print("[PiBillHandler] denom model missing; returning default 100 (mock).")
            return 100
        label, conf = self.run_inference(self.denom_model, frame, self.denom_labels)
        if conf < 0.8:
            return None
        print(f"[Denom] {label} ({conf*100:.1f}%)")
        # label may be string; attempt to map to int
        try:
            return int(label)
        except Exception:
            # if label is like "100.0" or "PHP100", attempt parse digits
            digits = ''.join(ch for ch in str(label) if ch.isdigit())
            return int(digits) if digits else None

    # -------------------------
    # High-level flows
    # -------------------------
    def accept_bill(
        self,
        required_denom: int,
        motor_forward_ms: int = 1000,
        motor_reverse_ms: int = 1000,
        push_after_sort_ms: int = 500,
        wait_for_ir_timeout_s: int = 60,
    ) -> Tuple[bool, Optional[int], str]:
        """
        Full accept flow (blocking) — meant to be invoked from a worker thread.

        Returns: (accepted_bool, denom_or_None, message)
        message examples: "accepted", "fake_bill", "denom_not_required", "sorter_no_ack", "camera_failed", "timeout_no_bill"
        """
        # Wait for IR (active-low)
        start = time.time()
        while time.time() - start < wait_for_ir_timeout_s:
            if self.read_ir():
                break
            time.sleep(0.05)
        else:
            return False, None, "timeout_no_bill"

        # Pull bill in
        self.motor_forward()
        time.sleep(motor_forward_ms / 1000.0)
        self.motor_stop()

        # UV authenticity — note: you said UV is manual, so we don't toggle UV here
        ok_auth = self.authenticate_bill()
        if not ok_auth:
            # reject
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, None, "fake_bill"

        # White LED on -> classify denom
        if self.white_led_pin is not None:
            self.white_on()
            time.sleep(0.1)  # settle

        denom = self.classify_denomination()

        if self.white_led_pin is not None:
            self.white_off()

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

        # denom matches -> send sorter command
        sorter_ok = self.sort_via_arduino(denom)
        if not sorter_ok:
            self.motor_reverse()
            time.sleep(motor_reverse_ms / 1000.0)
            self.motor_stop()
            return False, denom, "sorter_no_ack"

        # accepted: add to storage and push slightly to finalize
        self.storage.add(denom, 1)
        self.motor_forward()
        time.sleep(push_after_sort_ms / 1000.0)
        self.motor_stop()
        return True, denom, "accepted"

    def dispense_bill(self, denom: int, qty: int = 1, dispense_time_ms: int = 1500) -> Tuple[bool, str]:
        """
        Dispense bills by timed motor runs. Time-based approach; adjust dispense_time_ms by calibration.
        Returns (True, "ok") or (False, "err").
        """
        for i in range(qty):
            try:
                self.motor_forward()
                time.sleep(dispense_time_ms / 1000.0)
                self.motor_stop()
                time.sleep(0.3)
            except Exception as e:
                return False, f"motor_error:{e}"
        return True, "dispensed"

    def cleanup(self):
        try:
            if self.sorter_serial and hasattr(self.sorter_serial, "close"):
                self.sorter_serial.close()
        except Exception:
            pass
        if self.use_hardware and ON_RPI:
            GPIO.cleanup()
