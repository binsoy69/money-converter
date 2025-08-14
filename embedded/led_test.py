import RPi.GPIO as GPIO
import time

# GPIO pin assignments
RED_PIN = 17
GREEN_PIN = 27
BLUE_PIN = 22

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)

# Setup PWM on each pin at 100Hz
red = GPIO.PWM(RED_PIN, 100)
green = GPIO.PWM(GREEN_PIN, 100)
blue = GPIO.PWM(BLUE_PIN, 100)

# Start with 0% duty cycle (off)
red.start(0)
green.start(0)
blue.start(0)

def set_color(r, g, b):
    """Set color intensity from 0 to 100 (duty cycle %)"""
    red.ChangeDutyCycle(r)
    green.ChangeDutyCycle(g)
    blue.ChangeDutyCycle(b)

try:
    while True:
       
        
        print("White")
        set_color(100, 100, 100)
        time.sleep(1)

except KeyboardInterrupt:
    pass
