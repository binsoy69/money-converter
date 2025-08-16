import cv2
import time
import numpy as np
import RPi.GPIO as GPIO
from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice, DistanceSensor
from ultralytics import YOLO

class BillHandler:
    def __init__(self,
                 ir_sensor_pin=4,
                 motor_in1=16,
                 motor_in2=20,
                 motor_pwm_pin=21,
                 sorter_dir=24,
                 sorter_step=25,
                 sorter_echo=23,
                 sorter_trig=6,
                 white_led_pin=5,
                 forward_time=1.5,
                 reverse_time=1.2,
                 motor_speed=0.9):

        # Assign pins and settings
        self.forward_time = forward_time
        self.reverse_time = reverse_time
        self.motor_speed_value = motor_speed
        self.white_led_pin = white_led_pin

        self.sorter_step = sorter_step
        self.sorter_dir = sorter_dir

        # Set up GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.sorter_dir, GPIO.OUT)
        GPIO.setup(self.sorter_step, GPIO.OUT)
        GPIO.setup(self.white_led_pin, GPIO.OUT)
        GPIO.output(self.white_led_pin, GPIO.LOW)

        # Sensors and motors
        self.ir_sensor = DigitalInputDevice(ir_sensor_pin)
        self.motor = Motor(forward=motor_in1, backward=motor_in2)
        self.motor_speed = PWMOutputDevice(motor_pwm_pin)
        self.motor_speed.value = self.motor_speed_value

        # Sorter sensor
        self.sorter_sensor = DistanceSensor(echo=sorter_echo, trigger=sorter_trig, max_distance=2.0)

        # Bin distances (must match your sorter layout)
        self.BIN_DISTANCES = {
            "50php": 5.7,
            "100php": 14.05,
            "200php": 22.4,
            "500php": 30.8,
            "1000php": 36.8,
            "1000php_polymer": 37.0
        }

        self.SORTER_BIN_TOLERANCE = 1.5  # ± cm

        # Load YOLO models
        self.uv_model = YOLO("uv_cls_v2_ncnn_model", task='classify')
        self.denom_model = YOLO("denom-cls-v2_ncnn_model", task='classify')
        self.uv_labels = self.uv_model.names
        self.denom_labels = self.denom_model.names

        print("[BillHandler] Initialized.")

    # -------- Motor Logic -------- #
    def run_motor_forward(self, duration):
        print(f"[Motor] Forward {duration}s")
        self.motor.forward()
        time.sleep(duration)
        self.motor.stop()

    def run_motor_reverse(self, duration):
        print(f"[Motor] Reverse {duration}s")
        self.motor.backward()
        time.sleep(duration)
        self.motor.stop()

    # -------- Sorter Logic -------- #
    def move_stepper(self, direction=True, steps=200, delay=0.001):
        GPIO.output(self.sorter_dir, GPIO.LOW if direction else GPIO.HIGH)
        for _ in range(steps):
            GPIO.output(self.sorter_step, GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.sorter_step, GPIO.LOW)
            time.sleep(delay)

    def get_sorter_distance(self):
        return round(self.sorter_sensor.distance * 100, 2)

    def get_average_sorter_distance(self, samples=5):
        readings = [self.get_sorter_distance() for _ in range(samples)]
        time.sleep(0.02 * samples)
        return round(sum(readings) / len(readings), 2)

    def align_sorter_to_bin(self, denom):
        target = self.BIN_DISTANCES.get(str(denom))
        if target is None:
            print("[Sorter] Unknown bin.")
            return False

        for _ in range(1000):
            current = self.get_average_sorter_distance()
            error = current - target

            if abs(error) <= self.SORTER_BIN_TOLERANCE:
                print(f"[Sorter] Aligned to {denom}")
                return True

            if error < 0:
                self.move_stepper(direction=False, steps=100)
            else:
                self.move_stepper(direction=True, steps=100)

        print("[Sorter] Failed to align.")
        return False

    # -------- Detection Logic -------- #
    def is_bill_inserted(self):
        return not self.ir_sensor.value  # LOW = bill present

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
        if result.probs is None:
            return None, 0.0
        label = labels[int(result.probs.top1)]
        confidence = float(result.probs.top1conf)
        print(f"[YOLO] {label} ({confidence*100:.2f}%)")
        return label, confidence

    def authenticate_bill(self):
        print("[Auth] UV scan...")
        frame = self.capture_image()
        if frame is None:
            return False
        label, conf = self.run_inference(self.uv_model, frame, self.uv_labels)
        return conf >= 0.8 and label == "genuine"

    def classify_denomination(self):
        print("[Classify] White light scan...")
        GPIO.output(self.white_led_pin, GPIO.HIGH)
        frame = self.capture_image()
        GPIO.output(self.white_led_pin, GPIO.LOW)
        if frame is None:
            return None
        label, conf = self.run_inference(self.denom_model, frame, self.denom_labels)
        return label if conf >= 0.8 else None

    # -------- Process Flow -------- #
    def process_bill(self):
        print("[BillHandler] Waiting for bill...")
        while not self.is_bill_inserted():
            time.sleep(0.05)

        print("[BillHandler] Bill detected. Feeding in...")
        self.run_motor_forward(self.forward_time)

        if not self.authenticate_bill():
            print("[Auth] FAKE bill. Rejecting...")
            self.run_motor_reverse(self.reverse_time)
            return

        denom = self.classify_denomination()
        if denom not in self.BIN_DISTANCES:
            print("[Classify] Unknown denomination. Rejecting...")
            self.run_motor_reverse(self.reverse_time)
            return

        print(f"[Sorter] Sorting {denom}...")
        if self.align_sorter_to_bin(denom):
            self.run_motor_forward(self.forward_time + 0.5)
        else:
            self.run_motor_reverse(self.reverse_time)

    def cleanup(self):
        print("[Cleanup] Shutting down.")
        self.motor.stop()
        self.motor_speed.close()
        GPIO.cleanup()
