# test_ir_sensor.py
import RPi.GPIO as GPIO
import time

IR_PIN = 17  # Update this to your actual IR pin

GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN)

print("[READY] Waiting for bill insertion...")

try:
    while True:
        if GPIO.input(IR_PIN) == GPIO.LOW:  # IR beam is broken
            print("[DETECTED] Bill inserted!")
            time.sleep(0.5)  # debounce delay
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n[EXIT] Exiting IR test.")
finally:
    GPIO.cleanup()
