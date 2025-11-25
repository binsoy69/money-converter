"""
Example: How to use the modular bill dispensing system

This example shows how to register bill dispensers for different denominations
and use them for dispensing operations.
"""

from bill_handler.python.pi_bill_handler import PiBillHandler

# Initialize the bill handler
handler = PiBillHandler(
    ir_pin=17,
    motor_forward_pin=24,
    motor_backward_pin=23,
    motor_enable_pin=18,
    white_led_pin=27,
    sorter_serial_port="/dev/ttyACM0",
    sorter_baud=9600,
    speed=0.3
)

# Register dispensers for each denomination
# Each dispenser has 2 motors and 1 IR sensor

# 20 Peso dispenser
handler.register_dispenser(
    denomination=20,
    motor1_forward_pin=20,
    motor1_backward_pin=21,
    motor1_enable_pin=16,
    motor1_speed=0.5,
    motor2_forward_pin=19,
    motor2_backward_pin=26,
    motor2_enable_pin=13,
    motor2_speed=0.6,
    ir_sensor_pin=12
)

# 50 Peso dispenser
handler.register_dispenser(
    denomination=50,
    motor1_forward_pin=5,
    motor1_backward_pin=6,
    motor1_enable_pin=25,
    motor1_speed=0.5,
    motor2_forward_pin=22,
    motor2_backward_pin=27,
    motor2_enable_pin=4,
    motor2_speed=0.6,
    ir_sensor_pin=17
)

# 100 Peso dispenser
handler.register_dispenser(
    denomination=100,
    motor1_forward_pin=14,
    motor1_backward_pin=15,
    motor1_enable_pin=18,
    motor1_speed=0.5,
    motor2_forward_pin=23,
    motor2_backward_pin=24,
    motor2_enable_pin=8,
    motor2_speed=0.6,
    ir_sensor_pin=7
)

# You can easily add more denominations in the future:
# handler.register_dispenser(
#     denomination=200,
#     motor1_forward_pin=...,
#     motor1_backward_pin=...,
#     motor1_enable_pin=...,
#     motor1_speed=0.5,
#     motor2_forward_pin=...,
#     motor2_backward_pin=...,
#     motor2_enable_pin=...,
#     motor2_speed=0.6,
#     ir_sensor_pin=...
# )

# Example: Dispense bills
# No Arduino sorting needed - each denomination has its own dispenser

# Dispense 3 bills of 20 pesos
success, message = handler.dispense_bill(denom=20, qty=3)
if success:
    print(f"Successfully dispensed 3x 20 peso bills")
else:
    print(f"Dispense failed: {message}")

# Dispense 1 bill of 100 pesos
success, message = handler.dispense_bill(denom=100, qty=1)
if success:
    print(f"Successfully dispensed 1x 100 peso bill")
else:
    print(f"Dispense failed: {message}")

# Cleanup when done
handler.cleanup()
