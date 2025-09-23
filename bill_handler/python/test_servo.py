import pigpio
from time import sleep

SERVO_PIN = 21
PUSH_ANGLE = 90
RESET_ANGLE = 0
DISPENSE_TIME = 0.02
COUNT = 3

# Servo pulse widths (microseconds) – adjust if needed
MIN_PW = 500   # 0 degrees
MAX_PW = 2500  # 180 degrees

def angle_to_pulse(angle):
    return int(MIN_PW + (angle / 180.0) * (MAX_PW - MIN_PW))

pi = pigpio.pi()
if not pi.connected:
    exit()

while True:
    angle = input("Enter angle (0-180): ")
    pi.set_servo_pulsewidth(SERVO_PIN, angle_to_pulse(angle))


pi.set_servo_pulsewidth(SERVO_PIN, 0)  # turn off servo
pi.stop()
