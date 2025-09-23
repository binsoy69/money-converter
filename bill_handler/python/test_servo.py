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

for i in range(COUNT):
    for pos in range(PUSH_ANGLE, RESET_ANGLE - 1, -1):
        pi.set_servo_pulsewidth(SERVO_PIN, angle_to_pulse(pos))
        sleep(DISPENSE_TIME)
    for pos in range(RESET_ANGLE, PUSH_ANGLE + 1):
        pi.set_servo_pulsewidth(SERVO_PIN, angle_to_pulse(pos))
        sleep(DISPENSE_TIME)
    sleep(0.3)

pi.set_servo_pulsewidth(SERVO_PIN, 0)  # turn off servo
pi.stop()
