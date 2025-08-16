import cv2
import time
import serial
import os
from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice
from ultralytics import YOLO

class BillHandler:
    def __init__(self,
                 ir_sensor_pin=4,
                 # Intake motor pins
                 intake_in1=16,
                 intake_in2=20,
                 intake_pwm_pin=21,
                 # Dispenser motor pins (placeholders!)
                 dispense_in1=27,
                 dispense_in2=22,
                 dispense_pwm_pin=19,
                 # Serial to Arduino
                 serial_port="/dev/ttyUSB0",
                 baud=9600,
                 motor_speed=0.9):

        # Serial connection to Arduino
        self.ser = serial.Serial(serial_port, baud, timeout=1)
        time.sleep(2)  # allow Arduino to reset

        # IR Sensor
        self.ir_sensor = DigitalInputDevice(ir_sensor_pin)

        # Intake DC motor (for feeding/ejecting bills)
        self.intake_motor = Motor(forward=intake_in1, backward=intake_in2)
        self.intake_pwm = PWMOutputDevice(intake_pwm_pin)
        self.intake_pwm.value = motor_speed

        # Dispenser DC motor (for giving bills out) - Placeholder pins
        self.dispense_motor = Motor(forward=dispense_in1, backward=dispense_in2)
        self.dispense_pwm = PWMOutputDevice(dispense_pwm_pin)
        self.dispense_pwm.value = motor_speed

        # YOLO models
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.uv_model_path = os.path.join(self.script_dir, '..', 'models', "uv_cls_v2_ncnn_model")
        self.denom_model_path = os.path.join(self.script_dir, '..', 'models', "denom-cls-v2_ncnn_model")
        self.uv_model = YOLO(self.uv_model_path, task='classify')
        self.denom_model = YOLO(self.denom_model_path, task='classify')
        self.uv_labels = self.uv_model.names
        self.denom_labels = self.denom_model.names

        print("[BillHandler] Initialized (Pi controls intake, rejection, dispensing).")

    # ---------- Motor Helpers on Pi ----------
    def feed_bill(self, duration):
        print(f"[Intake] Forward for {duration}s")
        self.intake_motor.forward()
        time.sleep(duration)
        self.intake_motor.stop()

    def reject_bill(self, duration):
        print(f"[Reject] Reverse for {duration}s")
        self.intake_motor.backward()
        time.sleep(duration)
        self.intake_motor.stop()

    def dispense_bill(self, duration):
        print(f"[Dispense] DC motor dispensing for {duration}s")
        self.dispense_motor.forward()
        time.sleep(duration)
        self.dispense_motor.stop()

    # ---------- Serial to Arduino ----------
    def sort_via_arduino(self, denom):
        cmd = f"SORT:{denom}"
        print(f"[PI → ARDUINO] {cmd}")
        self.ser.write((cmd + "\n").encode())

    # ------------ Detection ---------------
    def is_bill_inserted(self):
        return not self.ir_sensor.value  # IR active LOW

    def capture_image(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Camera] Failed to open")
            return None
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None

    def run_inference(self, model, frame, labels):
        resized = cv2.resize(frame, (480, 480))
        result = model.predict(resized, verbose=False)[0]
        if result.probs is None: return None, 0
        label_idx = int(result.probs.top1)
        return labels[label_idx], float(result.probs.top1conf)

    def authenticate_bill(self):
        print("[Auth] UV Scan...")
        frame = self.capture_image()
        if frame is None: return False
        label, conf = self.run_inference(self.uv_model, frame, self.uv_labels)
        print(f"[UV] {label} ({conf*100:.1f}%)")
        return conf >= 0.8 and label == "genuine"

    def classify_denomination(self):
        print("[Classify] White light scan...")
        frame = self.capture_image()
        if frame is None: return None
        label, conf = self.run_inference(self.denom_model, frame, self.denom_labels)
        if conf < 0.8: return None
        print(f"[Denom] {label} ({conf*100:.1f}%)")
        return label

    # ------------ Process Flow ---------------
    def process_bill(self,
                     feed_time=1.5,
                     reject_time=1.2,
                     dispense_time=1.0):
        print("[Wait] Insert bill...")
        while not self.is_bill_inserted():
            time.sleep(0.05)

        print("[Detected] Feeding bill...")
        self.feed_bill(feed_time)

        if not self.authenticate_bill():
            print("[Fake] Reversing...")
            self.reject_bill(reject_time)
            return

        denom = self.classify_denomination()
        if denom is None:
            print("[Unknown Denom] Rejecting...")
            self.reject_bill(reject_time)
            return

        print(f"[Real] Commanding sort: {denom}")
        self.sort_via_arduino(denom)

        # Optional: Once sorted, you could also call dispense_bill() if this is a pay-out process
        # self.dispense_bill(dispense_time)

    def cleanup(self):
        print("[Cleanup] Closing serial and stopping motors")
        self.intake_motor.stop()
        self.dispense_motor.stop()
        self.ser.close()
