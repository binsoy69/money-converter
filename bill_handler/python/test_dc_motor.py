# motor_arrow_control_with_speed
import keyboard
from gpiozero import Motor, PWMOutputDevice
from time import sleep

# Define motor with PWM speed control (adjust pins as needed)
motor = Motor(forward=23, backward=24)
enable_pin = PWMOutputDevice(18)  # ENA pin connected to GPIO 18 (PWM-capable)

speed = 0.5  # Initial speed (0.0 to 1.0)
speed_step = 0.1

def apply_speed():
    enable_pin.value = speed
    print(f"[SPEED] Current speed: {speed:.1f}")

print("Use arrow keys to control the motor and speed:")
print("→ Right: Forward\n← Left: Backward\n↓ Down: Stop")
print("↑ Up: Increase speed\n↓ Down: Decrease speed\nESC: Quit")

apply_speed()

try:
    while True:
        if keyboard.is_pressed("right"):
            motor.forward()
            print("[FORWARD] Motor running forward")
            sleep(0.2)

        elif keyboard.is_pressed("left"):
            motor.backward()
            print("[BACKWARD] Motor running backward")
            sleep(0.2)

        elif keyboard.is_pressed("down"):
            motor.stop()
            print("[STOP] Motor stopped")
            sleep(0.2)

        elif keyboard.is_pressed("up"):
            if speed < 1.0:
                speed = min(1.0, speed + speed_step)
                apply_speed()
                sleep(0.2)

        elif keyboard.is_pressed("down"):
            if speed > 0.0:
                speed = max(0.0, speed - speed_step)
                apply_speed()
                sleep(0.2)

        elif keyboard.is_pressed("esc"):
            print("[EXIT] Exiting program")
            break

except KeyboardInterrupt:
    print("\n[INTERRUPTED] Stopping motor...")

finally:
    motor.stop()
    enable_pin.off()
