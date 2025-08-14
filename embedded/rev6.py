import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from gpiozero import DistanceSensor
import RPi.GPIO as GPIO
import time


# GPIO setup for stepper motor
ACCEPTOR_DIR = 14
ACCEPTOR_STEP = 15
SORTER_DIR = 24
SORTER_STEP = 25
GPIO.setmode(GPIO.BCM)
GPIO.setup(ACCEPTOR_DIR, GPIO.OUT)
GPIO.setup(ACCEPTOR_STEP, GPIO.OUT)
GPIO.setup(SORTER_DIR, GPIO.OUT)
GPIO.setup(SORTER_STEP, GPIO.OUT)

delay = 0.001  # Delay between steps / motor speed

# White LED
WHITE_LED_PIN = 5
GPIO.setup(WHITE_LED_PIN, GPIO.OUT)
GPIO.output(WHITE_LED_PIN, GPIO.LOW)

# DistanceSensor setup for bill acceptor
TRIG1=27 
ECHO1=17
acceptor_sensor = DistanceSensor(echo=ECHO1, trigger=TRIG1, max_distance=2.0)  # max_distance in meters

# DistanceSensor setup for bill sorter
SORTER_TRIG=6 
SORTER_ECHO=23
sorter_sensor = DistanceSensor(echo=SORTER_ECHO, trigger=SORTER_TRIG, max_distance=2.0)  # max_distance in meters

# Expected distances to bins from sorter sensor (in cm, must be calibrated)
BIN_DISTANCES = {
    "50php": 5.7,
    "100php": 14.05,
    "200php": 22.4,
    "500php": 30.8,
    "1000php": 36.8,
    "1000php_polymer": 37.0
}

ACCEPTOR_THRESHOLD = 0.088
SORTER_BIN_TOLERANCE = 1.5    # Acceptable margin for bin alignment

# Load YOLOv11 classification model for UV
uv_model_path = "uv_cls_v2_ncnn_model"  # Change to your model file name
uv_model = YOLO(uv_model_path, task='classify')

# Load YOLOv11 classification model for denomination
denom_model_path = "denom-cls-v2_ncnn_model"  # Change to your model file name
denom_model = YOLO(denom_model_path, task='classify')

# Access the class labels
uv_labels = uv_model.names
denom_labels = denom_model.names  

# Function to get distance in cm using gpiozero
def get_distance(sensor:DistanceSensor):
    return round(sensor.distance * 100, 2)  # convert from meters to cm

# Get average of several readings
def get_average_distance(sensor:DistanceSensor, samples=5):
    distances = []
    for _ in range(samples):
        distances.append(get_distance(sensor))
        time.sleep(0.02)
    return round(sum(distances) / len(distances), 2)

# Function for checking if bill is inserted
def is_bill_inserted(baseline):
    distance = get_average_distance(acceptor_sensor)
    print(f"Measured: {distance} cm")
    return (baseline - distance) > ACCEPTOR_THRESHOLD
    
def align_sorter_to_bin(denomination):
    target_distance = BIN_DISTANCES[str(denomination)]

    max_attempts = 1000
    for _ in range(max_attempts):
        current_distance = get_average_distance(sorter_sensor)

        error = current_distance - target_distance

        if abs(error) <= SORTER_BIN_TOLERANCE:
            return True  # Aligned

        # Move forward if current < target, backward if current > target
        if error < 0:
            move_stepper(SORTER_STEP, SORTER_DIR, direction=False, steps=200, delay=0.002)
        else:
            move_stepper(SORTER_STEP, SORTER_DIR, direction=True, steps=200, delay=0.002)

    return False  # Failed to align


def move_stepper(step_pin, dir_pin, direction=True, steps=200, delay=0.001):
    GPIO.output(dir_pin, GPIO.LOW if direction else GPIO.HIGH)
    for _ in range(steps):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)

def authenticate_bill():
    print("Capturing UV image for authentication...")
    frame = capture_image()
    if frame is None:
        return False

    label, confidence = run_inference(uv_model, frame, uv_labels)
    if confidence >= 0.8 and label == "genuine":
        print("Authentication passed.")
        return True
    else:
        print("Authentication failed.")
        return False

    
def classify_denomination():
    print("Capturing white-light image for denomination...")
    GPIO.output(WHITE_LED_PIN, GPIO.HIGH)
    frame = capture_image()
    if frame is None:
        return None

    label, confidence = run_inference(denom_model, frame, denom_labels)
    GPIO.output(WHITE_LED_PIN, GPIO.LOW)
    if confidence >= 0.8:
        print("Denomination validated.")
        return label
    else:
        print("Low confidence in denomination prediction.")
        return None

    
def capture_image():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to access camera")
        return None

    ret, frame = cap.read()
    cap.release()

    if ret:
        return frame  # Return as NumPy array
    else:
        print("Failed to capture image")
        return None

def run_inference(model, frame, labels):
    resized_frame = cv2.resize(frame, (480, 480))

    # Run prediction
    results = model.predict(resized_frame, verbose=False)
    pred = results[0]

    if pred.probs is None:
        print("No prediction probabilities available.")
        return None

    # Get predicted class index and confidence
    class_id = int(pred.probs.top1)
    confidence = float(pred.probs.top1conf)
    label = labels[class_id]

    print(f"Prediction: {label} ({confidence * 100:.2f}%)")
    return label, confidence
    
# Main Process
def process_bill(baseline):
    print("Waiting for bill insertion...")
    while not is_bill_inserted(baseline):
        time.sleep(0.3)

    print("Bill detected. Feeding to scanner...")
    move_stepper(ACCEPTOR_STEP, ACCEPTOR_DIR, direction=True, steps=200, delay=0.001)

    print("Bill aligned. Turning on UV light...")
    

    if not authenticate_bill():
        print("FAKE bill detected. Rejecting...")
        move_stepper(ACCEPTOR_STEP, ACCEPTOR_DIR, direction=False, steps=300, delay=0.001)
        return

    print("REAL bill detected. Turning on white light...")

    denom = classify_denomination()

    if denom not in BIN_DISTANCES:
        print("Invalid or undetected denomination. Rejecting...")
        move_stepper(ACCEPTOR_STEP, ACCEPTOR_DIR, direction=False, steps=300, delay=0.001)
        return

    print(f"Sorting to bin for {denom}...")
    if align_sorter_to_bin(denom):
        print("Sorter aligned. Sending bill to bin...")
        move_stepper(ACCEPTOR_STEP, ACCEPTOR_DIR, direction=True, steps=600, delay=0.001)
        time.sleep(1)
    else:
        print("Failed to align sorter. Rejecting...")
        move_stepper(ACCEPTOR_STEP, ACCEPTOR_DIR, direction=False, steps=300, delay=0.001)
        time.sleep(1)
	

try:
	print("Initializing baseline...")
	baseline = get_average_distance(acceptor_sensor)
	print(f"Baseline (no bill): {baseline} cm")
	while True:
		process_bill(baseline)
		time.sleep(3)  # Brief delay before accepting next bill
except KeyboardInterrupt:
    print("System stopped.")
