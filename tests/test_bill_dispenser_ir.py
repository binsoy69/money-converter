import time
import sys

# --- Configuration ---
# GPIO pins for Motor 1 (adjust as needed)
MOTOR1_FORWARD_PIN = 20
MOTOR1_BACKWARD_PIN = 21
MOTOR1_ENABLE_PIN = 16  # PWM capable pin for speed control
MOTOR1_SPEED = 0.8      # Speed for motor 1 (0.0 to 1.0)

# GPIO pins for Motor 2 (adjust as needed)
MOTOR2_FORWARD_PIN = 19
MOTOR2_BACKWARD_PIN = 26
MOTOR2_ENABLE_PIN = 13  # PWM capable pin for speed control
MOTOR2_SPEED = 0.6      # Speed for motor 2 (0.0 to 1.0)

# IR Sensor pin (for detecting dispensed bill)
IR_SENSOR_PIN = 17      # IR sensor at dispenser output

# Dispense settings
DISPENSE_DURATION_SECONDS = 2.5  # Duration per dispense attempt
MAX_RETRY_ATTEMPTS = 3           # Maximum retry attempts if bill not detected
IR_CHECK_DELAY = 0.5             # Delay before checking IR sensor after motor stops

# --- GPIOZero setup ---
try:
    from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice
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

    class MockDigitalInputDevice:
        def __init__(self, pin):
            self.pin = pin
            self._mock_counter = 0
            print(f"[MockIR] Initialized on pin {pin}")
        @property
        def value(self):
            # Simulate bill detection on 2nd attempt for testing
            self._mock_counter += 1
            detected = self._mock_counter % 2 == 0
            print(f"[MockIR] Pin {self.pin} read: {'HIGH (no bill)' if detected else 'LOW (bill detected)'}")
            return detected

    Motor = MockMotor
    PWMOutputDevice = MockPWMOutputDevice
    DigitalInputDevice = MockDigitalInputDevice


class BillDispenserIRTester:
    def __init__(self):
        print("Initializing BillDispenserIRTester...")
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

        # IR Sensor setup (active-low: LOW = bill detected, HIGH = no bill)
        self.ir_sensor = DigitalInputDevice(IR_SENSOR_PIN)

        print("BillDispenserIRTester initialized.")

    def check_ir_sensor(self):
        """
        Check if bill is detected by IR sensor.
        Returns True if bill detected, False otherwise.
        IR sensor is active-low: LOW (False) = bill detected
        """
        return not self.ir_sensor.value

    def run_motors(self, duration):
        """Run both motors forward for specified duration."""
        # Set speeds
        self.motor1_enable.value = MOTOR1_SPEED
        self.motor2_enable.value = MOTOR2_SPEED

        # Run motors forward
        self.motor1.forward()
        self.motor2.forward()
        print(f"  Motors running at Motor1:{MOTOR1_SPEED*100:.0f}%, Motor2:{MOTOR2_SPEED*100:.0f}%")

        time.sleep(duration)

        # Stop motors
        self.motor1.stop()
        self.motor2.stop()
        self.motor1_enable.off()
        self.motor2_enable.off()
        print("  Motors stopped.")

    def dispense_with_verification(self):
        """
        Attempt to dispense a bill with IR sensor verification.
        Retries up to MAX_RETRY_ATTEMPTS if bill not detected.
        Returns True if successful, False otherwise.
        """
        print(f"\n{'='*60}")
        print("DISPENSING BILL WITH IR VERIFICATION")
        print(f"{'='*60}")

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            print(f"\n--- Attempt {attempt}/{MAX_RETRY_ATTEMPTS} ---")
            
            # Run motors for one dispense cycle
            print(f"Running motors for {DISPENSE_DURATION_SECONDS} seconds...")
            self.run_motors(DISPENSE_DURATION_SECONDS)

            # Wait a moment for bill to settle
            print(f"Waiting {IR_CHECK_DELAY}s before checking IR sensor...")
            time.sleep(IR_CHECK_DELAY)

            # Check IR sensor
            print("Checking IR sensor...")
            if self.check_ir_sensor():
                print("✓ SUCCESS: Bill detected by IR sensor!")
                print(f"{'='*60}\n")
                return True
            else:
                print("✗ FAILED: No bill detected by IR sensor.")
                if attempt < MAX_RETRY_ATTEMPTS:
                    print(f"  Retrying... ({MAX_RETRY_ATTEMPTS - attempt} attempts remaining)")
                else:
                    print("  Maximum retry attempts reached.")

        print(f"\n{'='*60}")
        print("DISPENSE FAILED: Bill not detected after all attempts")
        print(f"{'='*60}\n")
        return False

    def cleanup(self):
        """Clean up GPIO resources."""
        print("\nCleaning up GPIO resources...")
        self.motor1.stop()
        self.motor2.stop()
        self.motor1_enable.off()
        self.motor2_enable.off()
        self.motor1.close()
        self.motor2.close()
        self.motor1_enable.close()
        self.ir_sensor.close()
        print("Cleanup complete.")


def main():
    """Main program loop."""
    tester = None
    try:
        tester = BillDispenserIRTester()
        
        print("\n" + "="*60)
        print("BILL DISPENSER WITH IR SENSOR TEST")
        print("="*60)
        print("Commands:")
        print("  - Press 'd' + ENTER to dispense a bill")
        print("  - Press ENTER alone to dispense a bill")
        print("  - Press CTRL+C to exit")
        print("="*60 + "\n")

        while True:
            user_input = input("Ready to dispense (press 'd' or ENTER): ").strip().lower()
            
            # Accept 'd', empty string (just Enter), or any input
            if user_input == 'd' or user_input == '':
                success = tester.dispense_with_verification()
                if success:
                    print("Status: ✓ Dispense successful\n")
                else:
                    print("Status: ✗ Dispense failed\n")
            else:
                print("Invalid input. Press 'd' + ENTER or just ENTER to dispense.\n")

    except KeyboardInterrupt:
        print("\n\nExiting program...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if tester:
            tester.cleanup()
        sys.exit(0)


if __name__ == "__main__":
    main()
