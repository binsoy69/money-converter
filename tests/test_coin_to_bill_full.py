#!/usr/bin/env python3
"""
Coin to Bill Conversion Test - Command Line Version
This program tests the full coin-to-bill conversion flow using actual handlers.
"""

import sys
import os
import time
import threading

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bill_handler.python.pi_bill_handler import PiBillHandler
from coin_handler.python.coin_handler_serial import CoinHandlerSerial
from demo.coin_to_bill_converter import convert_coins_to_bills

# Fee mapping (same as in coinToBill_controller.py)
AMOUNT_FEE_MAPPING = {
    20: 3, 40: 3,
    50: 5, 60: 5, 70: 5,
    80: 8, 90: 8, 100: 8,
    110: 10, 120: 10, 150: 10,
    160: 15, 170: 15, 200: 15
}

class CoinToBillTest:
    def __init__(self):
        print("=" * 60)
        print("Coin to Bill Conversion Test")
        print("=" * 60)
        
        # Initialize handlers
        print("\n[1/3] Initializing Bill Handler...")
        self.bill_handler = PiBillHandler()
        
        print("[2/3] Initializing Coin Handler...")
        self.coin_handler = CoinHandlerSerial()
        
        print("[3/3] Registering Bill Dispenser (20 Peso)...")
        self.bill_handler.register_dispenser(
            denomination=20,
            motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16, motor1_speed=0.6,
            motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13, motor2_speed=1.0,
            ir_sensor_pin=12
        )
        
        # State tracking
        self.coin_insertion_done = threading.Event()
        self.total_inserted = 0
        self.required_amount = 0
        self.selected_amount = 0
        
        print("\n[✓] Initialization complete!\n")
    
    def get_bill_amount(self):
        """Prompt user for bill amount to dispense."""
        valid_amounts = sorted(AMOUNT_FEE_MAPPING.keys())
        print("Available bill amounts:")
        for amt in valid_amounts:
            fee = AMOUNT_FEE_MAPPING[amt]
            print(f"  ₱{amt} (Fee: ₱{fee}, Total: ₱{amt + fee})")
        
        while True:
            try:
                choice = input("\nEnter bill amount to dispense: ₱").strip()
                amount = int(choice)
                if amount in AMOUNT_FEE_MAPPING:
                    return amount
                else:
                    print(f"Invalid amount. Please choose from: {valid_amounts}")
            except ValueError:
                print("Please enter a valid number.")
    
    def on_coin_inserted(self, denom, count, total):
        """Callback when a coin is inserted."""
        self.total_inserted = total
        print(f"\n[COIN] ₱{denom} inserted (Total: ₱{total} / ₱{self.required_amount})")
        
        if total >= self.required_amount:
            print(f"[✓] Required amount reached! (₱{total})")
            self.coin_insertion_done.set()
    
    def on_coins_finalized(self, total):
        """Callback when coin insertion is complete."""
        print(f"[INFO] Coin insertion finalized. Total: ₱{total}")
        self.coin_insertion_done.set()
    
    def run(self):
        """Run the coin-to-bill conversion test."""
        try:
            # Step 1: Get bill amount from user
            self.selected_amount = self.get_bill_amount()
            fee = AMOUNT_FEE_MAPPING[self.selected_amount]
            self.required_amount = self.selected_amount + fee
            
            print("\n" + "=" * 60)
            print(f"Bill Amount: ₱{self.selected_amount}")
            print(f"Service Fee: ₱{fee}")
            print(f"Total Required: ₱{self.required_amount}")
            print("=" * 60)
            
            # Step 2: Accept coins
            print(f"\n[COIN INSERTION] Please insert ₱{self.required_amount} in coins...")
            print("Insert coins now. The system will detect them automatically.\n")
            
            # Register callbacks
            self.coin_handler.add_callback(self.on_coin_inserted)
            self.coin_handler.add_reached_callback(self.on_coins_finalized)
            
            # Start coin acceptance
            self.coin_handler.start_accepting(self.required_amount)
            
            # Wait for enough coins or timeout (120 seconds)
            if not self.coin_insertion_done.wait(timeout=120):
                print("\n[TIMEOUT] Coin insertion timed out.")
                self.coin_handler.stop_accepting()
                return
            
            # Stop accepting coins
            self.coin_handler.stop_accepting()
            time.sleep(0.5)
            
            # Step 3: Calculate change and bills/coins to dispense
            excess = self.total_inserted - self.required_amount
            amount_to_dispense = self.selected_amount + excess
            
            print("\n" + "=" * 60)
            print(f"Coins Inserted: ₱{self.total_inserted}")
            print(f"Required: ₱{self.required_amount}")
            print(f"Excess: ₱{excess}")
            print(f"Amount to Dispense: ₱{amount_to_dispense}")
            print("=" * 60)
            
            # Step 4: Convert to bills/coins
            print("\n[CONVERSION] Calculating bill/coin breakdown...")
            
            # For now, assume user wants 20 peso bills
            selected_denoms = [20]
            
            coin_storage = self.coin_handler.storage.get_storage()
            bill_storage = self.bill_handler.storage.get_storage()
            
            bill_breakdown, coin_breakdown = convert_coins_to_bills(
                amount=amount_to_dispense,
                selected_denoms=selected_denoms,
                bill_storage=bill_storage,
                coin_storage=coin_storage
            )
            
            print(f"Bill Breakdown: {bill_breakdown}")
            print(f"Coin Breakdown: {coin_breakdown}")
            
            if not bill_breakdown and not coin_breakdown:
                print("\n[ERROR] Cannot dispense with available storage.")
                return
            
            # Step 5: Dispense bills
            if bill_breakdown:
                print("\n[DISPENSING] Dispensing bills...")
                for denom, qty in bill_breakdown.items():
                    print(f"  Dispensing ₱{denom} x{qty}...")
                    success, msg = self.bill_handler.dispense_bill(denom, qty)
                    if success:
                        print(f"  [✓] Successfully dispensed ₱{denom} x{qty}")
                    else:
                        print(f"  [✗] Failed to dispense ₱{denom} x{qty}: {msg}")
                        return
            
            # Step 6: Dispense coins if needed
            if coin_breakdown:
                print("\n[DISPENSING] Dispensing coins...")
                for denom, qty in coin_breakdown.items():
                    print(f"  Dispensing ₱{denom} x{qty}...")
                    self.coin_handler.dispense(denom, qty)
                    # Wait a bit for dispense to complete
                    time.sleep(2)
                    print(f"  [✓] Dispensed ₱{denom} x{qty}")
            
            print("\n" + "=" * 60)
            print("[✓] TRANSACTION COMPLETE!")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n[CANCELLED] User cancelled the operation.")
        except Exception as e:
            print(f"\n[ERROR] An error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            print("\n[CLEANUP] Cleaning up...")
            try:
                self.coin_handler.stop_accepting()
            except:
                pass
            self.bill_handler.cleanup()
            print("[✓] Cleanup complete.")

def main():
    test = CoinToBillTest()
    test.run()

if __name__ == "__main__":
    main()
