from gpiozero import Servo
from time import sleep

# === CONFIG ===
SERVO_PIN = 21            # BCM GPIO pin where servo is connected
PUSH_ANGLE = 90           # degrees
RESET_ANGLE = 0           # degrees
DISPENSE_TIME = 0.02      # seconds (20 ms, adjust as needed)
COUNT = 3                 # how many cycles

# gpiozero Servo expects values from -1 to +1, so convert degrees to range
def angle_to_value(angle):
    return (angle / 90.0) - 1  # 0° -> -1, 90° -> 0, 180° -> +1

servo = Servo(SERVO_PIN)

for i in range(COUNT):
    # Sweep from PUSH_ANGLE to RESET_ANGLE
    for pos in range(PUSH_ANGLE, RESET_ANGLE - 1, -1):
        servo.value = angle_to_value(pos)
        sleep(DISPENSE_TIME)
    
    # Sweep from RESET_ANGLE to PUSH_ANGLE
    for pos in range(RESET_ANGLE, PUSH_ANGLE + 1):
        servo.value = angle_to_value(pos)
        sleep(DISPENSE_TIME)
    
    sleep(0.3)
