import RPi.GPIO as GPIO
import time

# Define GPIO pins
DIR = 20     # Direction pin
STEP = 21    # Step pin
CW = 1       # Clockwise
CCW = 0      # Counterclockwise

# Constants
STEPS_PER_REV =300   # Adjust based on your motor and microstepping
REVOLUTIONS = 2       # Number of full revolutions to rotate
DELAY = 0.001         # Delay between steps (seconds)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)

def rotate_motor(steps, direction):
    GPIO.output(DIR, direction)
    for step in range(steps):
        GPIO.output(STEP, GPIO.HIGH)
        time.sleep(DELAY)
        GPIO.output(STEP, GPIO.LOW)
        time.sleep(DELAY)


total_steps = STEPS_PER_REV * REVOLUTIONS

print(f"Rotating clockwise for {REVOLUTIONS} revolutions...")
rotate_motor(total_steps, CCW)

time.sleep(1)

print(f"Rotating counterclockwise for {REVOLUTIONS} revolutions...")
rotate_motor(total_steps, CW)
    
time.sleep(1)
    


