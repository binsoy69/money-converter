import RPi.GPIO as GPIO
import time

# GPIO setup for ultrasonic sensor
ECHO = 17
TRIG = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# GPIO setup for stepper motor
DIR = 14
STEP = 15
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)

GPIO.output(DIR, GPIO.HIGH)  # Set direction (can be LOW for reverse)
delay = 0.001  # Delay between steps

# Function to get distance
def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.05)
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()

    pulse_end = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)

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

    threshold = 0.3
    paper_detected = False

    while True:
        distance = get_average_distance()
        print(f"Measured: {distance} cm")

        if not paper_detected and (baseline - distance > threshold):
            print("? Paper detected! Moving motor...")
            paper_detected = True
            step_motor(200*6)  # Rotate 1 full revolution (adjust as needed)

        elif paper_detected and (baseline - distance <= threshold):
            print("? Paper removed. Stopping motor.")
            paper_detected = False

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

