"""
Verification script for updated BillDispenser logic.
Mocks hardware to verify continuous transport and pulsing feeder logic.
"""
import sys
import os
import time
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Mock gpiozero before importing pi_bill_handler
sys.modules["gpiozero"] = MagicMock()
sys.modules["gpiozero"].Motor = MagicMock()
sys.modules["gpiozero"].PWMOutputDevice = MagicMock()
sys.modules["gpiozero"].DigitalInputDevice = MagicMock()
sys.modules["gpiozero"].LED = MagicMock()

from bill_handler.python.pi_bill_handler import PiBillHandler

def verify_dispenser_logic():
    print("--- Verifying Bill Dispenser Logic ---")
    
    # Initialize handler with mocks
    handler = PiBillHandler(use_hardware=True)
    
    # Register a test dispenser
    handler.register_dispenser(
        denomination=100,
        motor1_forward_pin=1, motor1_backward_pin=2, motor1_enable_pin=3, motor1_speed=0.5,
        motor2_forward_pin=4, motor2_backward_pin=5, motor2_enable_pin=6, motor2_speed=0.8,
        ir_sensor_pin=7
    )
    
    dispenser = handler.dispensers[100]
    
    # Mock IR sensor to detect bill on 2nd check
    # We need to simulate:
    # 1. check_ir() called in wait_for_bill loop
    # 2. Returns False initially, then True
    ir_mock = dispenser.ir_sensor
    ir_mock.value = 1 # Active-low: 1=No Bill
    
    # Helper to simulate IR detection after some time
    def simulate_ir_detection():
        time.sleep(0.1)
        print("    [Sim] IR Sensor detects bill!")
        ir_mock.value = 0 # Active-low: 0=Bill Detected
    
    import threading
    t = threading.Thread(target=simulate_ir_detection)
    t.start()
    
    # Run dispense
    print("\nCalling dispense_bill(qty=1)...")
    success, msg = handler.dispense_bill(denom=100, qty=1, dispense_duration_s=0.1, ir_poll_timeout_s=0.5)
    
    t.join()
    
    if success:
        print("\n✅ Dispense successful!")
    else:
        print(f"\n❌ Dispense failed: {msg}")
        
    # Verify Motor calls
    print("\nVerifying Motor Calls:")
    
    # Motor 2 (Transport) should be started once and stopped once
    print(f"  Motor 2 Forward calls: {dispenser.motor2.forward.call_count}")
    print(f"  Motor 2 Stop calls: {dispenser.motor2.stop.call_count}")
    
    if dispenser.motor2.forward.call_count == 1 and dispenser.motor2.stop.call_count == 1:
        print("  ✅ Motor 2 (Transport) logic correct (Continuous run)")
    else:
        print("  ❌ Motor 2 logic incorrect")

    # Motor 1 (Feeder) should be pulsed once (forward then stop)
    print(f"  Motor 1 Forward calls: {dispenser.motor1.forward.call_count}")
    print(f"  Motor 1 Stop calls: {dispenser.motor1.stop.call_count}")
    
    if dispenser.motor1.forward.call_count >= 1:
        print("  ✅ Motor 1 (Feeder) logic correct (Pulsing)")
    else:
        print("  ❌ Motor 1 logic incorrect")

if __name__ == "__main__":
    verify_dispenser_logic()
