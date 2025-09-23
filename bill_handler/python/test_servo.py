import pigpio
from time import sleep

SERVO_PIN = 21
MIN_PW = 500   # 0 degrees
MAX_PW = 2500  # 180 degrees

def angle_to_pulse(angle):
    return int(MIN_PW + (angle / 180.0) * (MAX_PW - MIN_PW))

pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon. Did you run 'sudo pigpiod'?")
    exit()

try:
    while True:
        angle = input("Enter angle (0-180, or 'q' to quit): ").strip()
        if angle.lower() == "q":
            break
        try:
            angle = float(angle)
            if 0 <= angle <= 180:
                pi.set_servo_pulsewidth(SERVO_PIN, angle_to_pulse(angle))
            else:
                print("⚠️ Please enter a value between 0 and 180")
        except ValueError:
            print("⚠️ Invalid input. Enter a number or 'q' to quit.")

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    pi.set_servo_pulsewidth(SERVO_PIN, 0)  # turn off servo
    pi.stop()
    print("Servo released and pigpio stopped.")
