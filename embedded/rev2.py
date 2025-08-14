
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
delay = 0.001  # Delay between steps

# DistanceSensor setup (TRIG=27, ECHO=17)
sensor = DistanceSensor(echo=17, trigger=27, max_distance=2.0)  # max_distance in meters

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

try:
    print("Initializing baseline...")
    baseline = get_average_distance()
    print(f"Baseline (no paper): {baseline} cm")

    threshold = 0.05  # Thin paper detection sensitivity
    paper_detected = False

    while True:
        distance = get_average_distance()
        print(f"Measured: {distance} cm")

        if not paper_detected and (baseline - distance > threshold):
            print("📄 Paper detected! Moving motor...")
            paper_detected = True
            step_motor(200 * 6)  # Move paper

        elif paper_detected and (baseline - distance <= threshold):
            print("✅ Paper removed. Stopping motor.")
            paper_detected = False

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

