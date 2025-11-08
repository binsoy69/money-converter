import time
import sys

# --- Configuration ---
# GPIO pins for Motor 1 (adjust as needed)
MOTOR1_FORWARD_PIN = 20
MOTOR1_BACKWARD_PIN = 21
MOTOR1_ENABLE_PIN = 16 # PWM capable pin for speed control
MOTOR1_SPEED = 0.8     # Speed for motor 1 (0.0 to 1.0)

# GPIO pins for Motor 2 (adjust as needed)
MOTOR2_FORWARD_PIN = 19
MOTOR2_BACKWARD_PIN = 26
MOTOR2_ENABLE_PIN = 13 # PWM capable pin for speed control
MOTOR2_SPEED = 0.6     # Speed for motor 2 (0.0 to 1.0)

# Dispense duration
DISPENSE_DURATION_SECONDS = 10

# --- GPIOZero setup ---
try:
    from gpiozero import Motor, PWMOutputDevice
    ON_RPI = True
except ImportError:
    print("gpiozero not found. Running in mock mode.")
    ON_RPI = False
    # Mock classes for development/testing off-Pi
    class MockMotor:
        def __init__(self, forward, backward):
            self.forward_pin = forward
            self.backward_pin = backward
            print(f"[MockMotor] Initialized with FWD:{forward}, BWD:{backward}")
        def forward(self):
            print(f"[MockMotor] Motor on FWD (pins {self.forward_pin}, {self.backward_pin})")
        def backward(self):
            print(f"[MockMotor] Motor on BWD (pins {self.forward_pin}, {self.backward_pin})")
        def stop(self):
            print(f"[MockMotor] Motor stopped (pins {self.forward_pin}, {self.backward_pin})")
        def close(self):
            print(f"[MockMotor] Closed (pins {self.forward_pin}, {self.backward_pin})")

    class MockPWMOutputDevice:
        def __init__(self, pin):
            self.pin = pin
            self._value = 0.0
            print(f"[MockPWM] Initialized on pin {pin}")
        @property
        def value(self):
            return self._value
        @value.setter
        def value(self, speed):
            self._value = speed
            print(f"[MockPWM] Pin {self.pin} speed set to {speed}")
        def off(self):
            self._value = 0.0
            print(f"[MockPWM] Pin {self.pin} turned off")
        def close(self):
            print(f"[MockPWM] Closed on pin {self.pin}")

    Motor = MockMotor
    PWMOutputDevice = MockPWMOutputDevice


class BillDispenserTester:
    def __init__(self):
        print("Initializing BillDispenserTester...")
        if ON_RPI:
            print("Running on Raspberry Pi with real GPIO.")
        else:
            print("Running in mock mode (gpiozero not found).")

        # Motor 1 setup
        self.motor1 = Motor(forward=MOTOR1_FORWARD_PIN, backward=MOTOR1_BACKWARD_PIN)
        self.motor1_enable = PWMOutputDevice(MOTOR1_ENABLE_PIN)

        # Motor 2 setup
        self.motor2 = Motor(forward=MOTOR2_FORWARD_PIN, backward=MOTOR2_BACKWARD_PIN)
        self.motor2_enable = PWMOutputDevice(MOTOR2_ENABLE_PIN)

        print("BillDispenserTester initialized.")

    def dispense(self):
        print(f"\n--- Dispensing for {DISPENSE_DURATION_SECONDS} seconds ---")
        
        # Set speeds
        self.motor1_enable.value = MOTOR1_SPEED
        self.motor2_enable.value = MOTOR2_SPEED

        # Run motors forward
        self.motor1.forward()
        self.motor2.forward()
        print(f"Motor 1 running at {MOTOR1_SPEED*100:.0f}%")
        print(f"Motor 2 running at {MOTOR2_SPEED*100:.0f}%")

        time.sleep(DISPENSE_DURATION_SECONDS)

        # Stop motors
        self.motor1.stop()
        self.motor2.stop()
        self.motor1_enable.off()
        self.motor2_enable.off()
        print("Motors stopped.")
        print("--- Dispense cycle complete ---")

    def cleanup(self):
        print("\nCleaning up GPIO resources...")
        self.motor1.stop()
        self.motor2.stop()
        self.motor1_enable.off()
        self.motor2_enable.off()
        self.motor1.close()
        self.motor2.close()
        self.motor1_enable.close()
        self.motor2_enable.close()
        print("Cleanup complete.")


if __name__ == "__main__":
    tester = None
    try:
        tester = BillDispenserTester()
        print("\nPress ENTER to dispense bills. Press CTRL+C to exit.")
        while True:
            input("") # Wait for user to press Enter
            tester.dispense()

    except KeyboardInterrupt:
        print("\nExiting program.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if tester:
            tester.cleanup()
        sys.exit(0)
