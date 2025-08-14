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
            

        elif bill_inserted and not is_bill_detected(baseline, threshold):
            print("Bill removed. Stopping motor.")
            bill_inserted = False

        time.sleep(0.5)
    
    
# Run main
main()
