import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO
from gpiozero import DistanceSensor
import RPi.GPIO as GPIO
import time


# GPIO setup for stepper motor
DIR = 14
STEP = 15
GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)

GPIO.output(DIR, GPIO.HIGH)  # Set direction (can be LOW for reverse)
delay = 0.001  # Delay between steps / motor speed

# DistanceSensor setup 
TRIG1=27 
ECHO1=17
sensor = DistanceSensor(echo=ECHO1, trigger=TRIG1, max_distance=2.0)  # max_distance in meters


# Load YOLOv11 classification model for UV
uv_model_path = "uv_cls_v2_ncnn_model"  # Change to your model file name
uv_model = YOLO(uv_model_path, task='classify')

# Load YOLOv11 classification model for denomination
denom_model_path = "denom-cls-v2_ncnn_model"  # Change to your model file name
denom_model = YOLO(denom_model_path, task='classify')

# Access the class labels
uv_labels = uv_model.names
denom_labels = denom_model.names  

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
    return label


def classify_denomination():
    print("Capturing white-light image for denomination...")
    frame = capture_image()
    if frame is None:
        return None

    result = run_inference(denom_model, frame, denom_labels)
    print(f"Detected denomination: {result}")
    return result  # 20, 50, 100, etc.

def authenticate_bill():
    print("Capturing UV image for authentication...")
    frame = capture_image()
    if frame is None:
        return False

    result = run_inference(uv_model, frame, uv_labels)
    print(f"Authentication result: {result}")
    return result == "genuine"


# Function to get distance in cm using gpiozero
def get_distance():
    return round(sensor.distance * 100, 2)  # convert from meters to cm

# Get average of several readings
def get_average_distance(samples=5):
    distances = []
    for _ in range(samples):
        distances.append(get_distance())
        time.sleep(0.02)
    return round(sum(distances) / len(distances), 2)

# Stepper motor move function
def step_motor(steps):
    for _ in range(steps):
        GPIO.output(STEP, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(STEP, GPIO.LOW)
        time.sleep(delay)

# Function for checking if bill is inserted
def is_bill_detected(baseline, threshold):
    distance = get_average_distance()
    print(f"Measured: {distance} cm")
    return (baseline - distance) > threshold



def main():
    print("Initializing baseline...")
    baseline = get_average_distance()
    print(f"Baseline (no bill): {baseline} cm")

    threshold = 0.05  # Thin paper detection sensitivity
    bill_inserted = False

    while True:
        
        if not bill_inserted and is_bill_detected(baseline, threshold):
            print("Bill detected! Moving motor...")
            bill_inserted = True
            step_motor(200 * 3)  # Move the bill
            auth = authenticate_bill()
            denomination = classify_denomination()
            

        elif bill_inserted and not is_bill_detected(baseline, threshold):
            print("Bill removed. Stopping motor.")
            bill_inserted = False

        time.sleep(0.5)
    
    
# Run main
main()
