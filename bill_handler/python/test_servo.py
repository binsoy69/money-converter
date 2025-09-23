import RPi.GPIO as GPIO
import time

# Setup
servo_pin = 21  # Use a PWM-capable GPIO pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)

# Initialize PWM at 50Hz
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)

def angle_to_duty_cycle(angle):
    # Convert angle (0-180) to duty cycle (2.5-12.5)
    return 2.5 + (angle / 180.0) * 10

try:
    while True:
        user_input = input("Enter angle (0 to 180, or 'q' to quit): ")
        if user_input.lower() == 'q':
            break
        try:
            angle = float(user_input)
            if 0 <= angle <= 180:
                duty_cycle = angle_to_duty_cycle(angle)
                pwm.ChangeDutyCycle(duty_cycle)
                time.sleep(0.5)
                pwm.ChangeDutyCycle(0)  # Stop signal to avoid jitter
            else:
                print("Angle must be between 0 and 180.")
        except ValueError:
            print("Invalid input. Please enter a number.")
finally:
    pwm.stop()
    GPIO.cleanup()
    print("Program terminated.")