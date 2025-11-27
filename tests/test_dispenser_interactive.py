
import sys
import os
import time

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bill_handler.python.pi_bill_handler import PiBillHandler

def main():
    print("=== Interactive Dispenser Test ===")
    print("Initializing PiBillHandler...")
    try:
        handler = PiBillHandler()
    except Exception as e:
        print(f"Failed to init handler: {e}")
        return

    print(f"Handler initialized. Hardware Mode: {'ON' if handler.use_hardware else 'MOCK'}")

    # Register dispenser (same as main_controller.py)
    # 20 Peso dispenser
    print("Registering dispenser for 20 Pesos...")
    handler.register_dispenser(
        denomination=20,
        motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16, motor1_speed=0.6,
        motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13, motor2_speed=1.0,
        ir_sensor_pin=12
    )
    
    # Add initial stock for testing
    handler.storage.add(20, 100)
    print("Added 100 bills of 20 to virtual storage.")

    while True:
        print("\n--------------------------------")
        print("Options:")
        print("1. Dispense Bill")
        print("2. Check Storage")
        print("3. Exit")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            try:
                denom_str = input("Enter denomination (default 20): ").strip()
                if not denom_str:
                    denom = 20
                else:
                    denom = int(denom_str)
                
                qty_str = input("Enter quantity (default 1): ").strip()
                if not qty_str:
                    qty = 1
                else:
                    qty = int(qty_str)
                
                print(f"Attempting to dispense {qty} x {denom}...")
                success, msg = handler.dispense_bill(denom, qty)
                
                if success:
                    print(f"SUCCESS: {msg}")
                else:
                    print(f"FAILURE: {msg}")
                    
            except ValueError:
                print("Invalid input. Please enter numbers.")
            except Exception as e:
                print(f"An error occurred during dispense: {e}")
                import traceback
                traceback.print_exc()
                
        elif choice == '2':
            print("Current Storage:")
            print(handler.storage.get_storage())
            
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice.")

    # Cleanup
    handler.cleanup()

if __name__ == "__main__":
    main()
