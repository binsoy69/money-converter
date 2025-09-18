# ir_motor_control.py
from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice
from time import sleep

# Pin definitions (adjust if needed)
MOTOR_FORWARD_PIN = 24
MOTOR_BACKWARD_PIN = 23
MOTOR_ENABLE_PIN = 18   # ENA (PWM pin)
IR_SENSOR_PIN = 17      # IR sensor signal pin

# Setup
motor = Motor(forward=MOTOR_FORWARD_PIN, backward=MOTOR_BACKWARD_PIN)
enable_pin = PWMOutputDevice(MOTOR_ENABLE_PIN)
ir_sensor = DigitalInputDevice(IR_SENSOR_PIN)

speed = 0.3  # Set your desired motor speed (0.0 to 1.0)
motor_run_time = 0.4  # Seconds to run motor when bill is detected

print("[READY] Waiting for bill insertion...")

try:
    while True:
        if not ir_sensor.value:  # IR beam broken → bill inserted
            print("[DETECTED] Bill inserted!")
            enable_pin.value = speed
            sleep(1)
            motor.forward()
            sleep(motor_run_time)
            motor.stop()
            enable_pin.off()
            print("[DONE] Bill accepted. Waiting for next...")
        
        sleep(0.05)

except KeyboardInterrupt:
    print("\n[INTERRUPTED] Stopping motor...")

finally:
    motor.stop()
    enable_pin.off()
