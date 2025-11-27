
import sys
import os
import time

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bill_handler.python.pi_bill_handler import PiBillHandler

def main():
    print("Initializing PiBillHandler...")
    try:
        handler = PiBillHandler()
    except Exception as e:
        print(f"Failed to init handler: {e}")
        return

    print(f"Handler initialized. ON_RPI={handler.use_hardware}")

    # Register dispenser (same as main_controller.py)
    print("Registering dispenser for 20...")
    handler.register_dispenser(
        denomination=20,
        motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16, motor1_speed=0.6,
        motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13, motor2_speed=1.0,
        ir_sensor_pin=12
    )

    # Add some bills to storage so we can dispense
    handler.storage.add(20, 10)
    print("Storage added. Dispensing 1 bill of 20...")

    try:
        success, msg = handler.dispense_bill(20, 1)
        print(f"Dispense result: {success}, {msg}")
    except Exception as e:
        print(f"Exception during dispense: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
