from gpiozero import AngularServo
from time import sleep

# Setup: adjust pulse widths if needed for your servo model
servo = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0023)

print("Servo ready. Enter angle between -90 and 90 (or 'q' to quit).")

try:
    while True:
        user_input = input("Enter angle: ")
        if user_input.lower() == 'q':
            print("Exiting...")
            break
        try:
            angle = float(user_input)
            if -90 <= angle <= 90:
                servo.angle = angle
                print(f"Moved to {angle}°")
                sleep(1)
            else:
                print("⚠️ Angle must be between -90 and 90.")
        except ValueError:
            print("⚠️ Invalid input. Please enter a number or 'q'.")
except KeyboardInterrupt:
    print("\nInterrupted by user.")