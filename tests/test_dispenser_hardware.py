
import time
import sys
import os

# Explicitly try to import gpiozero
try:
    from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice, Device
    from gpiozero.pins.native import NativeFactory
    print(f"gpiozero imported. Default pin factory: {Device.pin_factory}")
except ImportError:
    print("gpiozero not found!")
    sys.exit(1)
except Exception as e:
    print(f"Error importing gpiozero: {e}")
    sys.exit(1)

def test_dispenser_20():
    print("\n=== Testing Dispenser 20 Hardware ===")
    
    # Pin Config (from main_controller.py)
    # 20 Peso dispenser
    # motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16
    # motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13
    # ir_sensor_pin=12
    
    m1_f = 20
    m1_b = 21
    m1_e = 16
    
    m2_f = 19
    m2_b = 26
    m2_e = 13
    
    ir_pin = 12
    
    print(f"Pins: M1(F={m1_f}, B={m1_b}, E={m1_e}), M2(F={m2_f}, B={m2_b}, E={m2_e}), IR={ir_pin}")
    
    try:
        print("Initializing M1 (Feeder)...")
        m1 = Motor(forward=m1_f, backward=m1_b)
        m1_enable = PWMOutputDevice(m1_e)
        
        print("Initializing M2 (Transport)...")
        m2 = Motor(forward=m2_f, backward=m2_b)
        m2_enable = PWMOutputDevice(m2_e)
        
        print("Initializing IR Sensor...")
        ir = DigitalInputDevice(ir_pin)
        
        print("Hardware initialized successfully.")
        
        # Test M1
        print("Testing M1 (Feeder) - Forward for 1s...")
        m1_enable.value = 0.6
        m1.forward()
        time.sleep(1)
        m1.stop()
        m1_enable.off()
        print("M1 test done.")
        
        # Test M2
        print("Testing M2 (Transport) - Forward for 1s...")
        m2_enable.value = 1.0
        m2.forward()
        time.sleep(1)
        m2.stop()
        m2_enable.off()
        print("M2 test done.")
        
        # Test IR
        print("Reading IR Sensor for 5s (Block sensor to test)...")
        start = time.time()
        while time.time() - start < 5:
            val = ir.value
            state = "DETECTED" if val == 0 else "CLEAR" # Active low
            print(f"IR Value: {val} ({state})", end='\r')
            time.sleep(0.1)
        print("\nIR test done.")
        
        print("\n=== Test Complete: SUCCESS ===")
        
    except Exception as e:
        print(f"\n!!! EXCEPTION DURING HARDWARE TEST: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up...")
        try:
            m1.close()
            m1_enable.close()
            m2.close()
            m2_enable.close()
            ir.close()
        except:
            pass

if __name__ == "__main__":
    test_dispenser_20()
