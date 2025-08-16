# test_bill_handler.py
from bill_handler import BillHandler

def main():
    handler = BillHandler(
        ir_sensor_pin=4,
        intake_in1=16,   # GPIO pins for DC intake motor
        intake_in2=20,
        intake_pwm_pin=21,
        # Placeholder dispenser motor pins
        dispense_in1=27,
        dispense_in2=22,
        dispense_pwm_pin=19,
        serial_port='/dev/ttyUSB0',  # Adjust if /dev/ttyACM0
        baud=9600,
        motor_speed=0.9
    )

    try:
        while True:
            handler.process_bill()

    except KeyboardInterrupt:
        print("\n[Exit] Stopping.")
    finally:
        handler.cleanup()

if __name__ == '__main__':
    main()
