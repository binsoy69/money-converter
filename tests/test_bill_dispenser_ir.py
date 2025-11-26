import time
import sys

# --- Configuration ---
# GPIO pins for Motor 1 (adjust as needed)
MOTOR1_FORWARD_PIN = 20
MOTOR1_BACKWARD_PIN = 21
MOTOR1_ENABLE_PIN = 16  # PWM capable pin for speed control
MOTOR1_SPEED = 0.5      # Speed for motor 1 (0.0 to 1.0)

# GPIO pins for Motor 2 (adjust as needed)
MOTOR2_FORWARD_PIN = 19
MOTOR2_BACKWARD_PIN = 26
MOTOR2_ENABLE_PIN = 13  # PWM capable pin for speed control
MOTOR2_SPEED = 0.6      # Speed for motor 2 (0.0 to 1.0)

# IR Sensor pin (for detecting dispensed bill)
IR_SENSOR_PIN = 12      # IR sensor at dispenser output

# Dispense settings
DISPENSE_DURATION_SECONDS = 0.25  # Duration per dispense attempt
MAX_RETRY_ATTEMPTS = 5           # Maximum retry attempts if bill not detected
IR_CHECK_DELAY = 0.5             # Delay before checking IR sensor after motor stops
IR_POLL_TIMEOUT = 2.0            # Max time to wait for IR detection per bill

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

    def start_motor2(self):
        """Start Motor 2 continuously."""
        self.motor2_enable.value = MOTOR2_SPEED
        self.motor2.forward()
        print(f"  Motor 2 started at {MOTOR2_SPEED*100:.0f}%")

    def stop_motor2(self):
        """Stop Motor 2."""
        self.motor2.stop()
        self.motor2_enable.off()
        print("  Motor 2 stopped.")

    def pulse_motor1(self, duration):
        """Run Motor 1 forward for specified duration."""
        self.motor1_enable.value = MOTOR1_SPEED
        self.motor1.forward()
        print(f"    Motor 1 pulsing for {duration}s at {MOTOR1_SPEED*100:.0f}%...")
        time.sleep(duration)
        self.motor1.stop()
        self.motor1_enable.off()
        print("    Motor 1 stopped.")

    def wait_for_bill(self, timeout=IR_POLL_TIMEOUT):
        """
        Wait for IR sensor to detect a bill within timeout.
        Returns True if detected, False if timeout.
        """
        start_time = time.time()
        print(f"    Waiting for bill detection (timeout {timeout}s)...")
        while time.time() - start_time < timeout:
            if self.check_ir_sensor():
                return True
            time.sleep(0.05)  # Small delay to prevent CPU hogging
        return False

    def dispense_bills(self, count):
        """
        Dispense a specified number of bills.
        Motor 2 runs continuously. Motor 1 pulses to feed bills.
        """
        print(f"\n{'='*60}")
        print(f"DISPENSING {count} BILL(S)")
        print(f"{'='*60}")

        successful_dispenses = 0
        
        try:
            # Start Motor 2 (Transport)
            self.start_motor2()
            
            # Give Motor 2 a moment to spin up
            time.sleep(0.5)

            for i in range(1, count + 1):
                print(f"\n--- Dispensing Bill {i}/{count} ---")
                bill_dispensed = False
                
                for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                    if attempt > 1:
                        print(f"    Retry attempt {attempt}/{MAX_RETRY_ATTEMPTS}...")
                    
                    # Pulse Motor 1 (Feeder)
                    self.pulse_motor1(DISPENSE_DURATION_SECONDS)
                    
                    # Wait for IR detection
                    if self.wait_for_bill(timeout=IR_POLL_TIMEOUT):
                        print(f"    SUCCESS: Bill {i} detected!")
                        bill_dispensed = True
                        successful_dispenses += 1
                        # Small delay between bills to ensure separation
                        time.sleep(0.5) 
                        break
                    else:
                        print("    No bill detected.")
                
                if not bill_dispensed:
                    print(f"    FAILED: Could not dispense bill {i} after {MAX_RETRY_ATTEMPTS} attempts.")
                    # Optional: Stop if one fails? Or continue? 
                    # For now, we'll continue trying the next one but note the failure.
        
        except KeyboardInterrupt:
            print("\nDispense interrupted by user!")
        finally:
            # Always stop Motor 2 at the end
            self.stop_motor2()

        print(f"\n{'='*60}")
        print(f"DISPENSE COMPLETE. Success: {successful_dispenses}/{count}")
        print(f"{'='*60}\n")
        return successful_dispenses == count

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
        print("BILL DISPENSER WITH IR SENSOR TEST (MULTI-BILL)")
        print("="*60)
        print("Commands:")
        print("  - Enter a number to dispense that many bills")
        print("  - Press ENTER alone to dispense 1 bill")
        print("  - Press CTRL+C to exit")
        print("="*60 + "\n")

        while True:
            user_input = input("Enter number of bills to dispense (default 1): ").strip().lower()
            
            count = 1
            if user_input == '':
                count = 1
            elif user_input.isdigit():
                count = int(user_input)
                if count <= 0:
                    print("Please enter a positive number.")
                    continue
            else:
                print("Invalid input. Please enter a number.")
                continue

            tester.dispense_bills(count)

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
