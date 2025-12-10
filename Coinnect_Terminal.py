#!/usr/bin/env python3
"""
Coinnect Terminal - Integrated Money Converter System
This program integrates Coin to Bill, Bill to Coin, and Bill to Bill conversion flows.
"""

import sys
import os
import time
import threading

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from bill_handler.python.pi_bill_handler import PiBillHandler
from coin_handler.python.coin_handler_serial import CoinHandlerSerial
from demo.coin_to_bill_converter import convert_coins_to_bills
from demo.bill_to_coin_converter import convert_bill_to_coin
from demo.bill_to_bill_converter import convert_bill_to_bills

# Fee mappings
COIN_TO_BILL_FEES = {
    20: 3, 40: 3,
    50: 5, 60: 5, 70: 5,
    80: 8, 90: 8, 100: 8,
    110: 10, 120: 10, 150: 10,
    160: 15, 170: 15, 200: 15
}

BILL_CONVERSION_FEES = {
    20: 2,
    50: 2, # Adjusted to match billToCoin/billToBill commonalities if any, using billToBill for now
    100: 3,
    200: 5,
    500: 7,
    1000: 10
}
# Note: BillToCoin used specific fees in test: 20:2, 50:3, 100:5, 200:7. 
# BillToBill used: 50:2, 100:3, 200:5, 500:7, 1000:10.
# I will use a unified mapping or specific ones per flow.
# Let's use specific ones to match the tests exactly.

BILL_TO_COIN_FEES = {
    20: 2,
    50: 3,
    100: 5,
    200: 7
}

BILL_TO_BILL_FEES = {
    50: 2,
    100: 3,
    200: 5,
    500: 7,
    1000: 10
}

COIN_INSERTION_TIMEOUT = 120

class CoinnectTerminal:
    def __init__(self):
        print("=" * 60)
        print("Coinnect Terminal - Money Converter System")
        print("=" * 60)
        
        # Initialize handlers
        print("\n[1/3] Initializing Coin Handler (and Shared Serial)...")
        self.coin_handler = CoinHandlerSerial()
        
        print("[2/3] Initializing Bill Handler...")
        self.bill_handler = PiBillHandler(serial_manager=self.coin_handler)
        
        print("[3/3] Registering Bill Dispenser (20 Peso)...")
        # Register dispenser as done in test_coin_to_bill_full.py
        self.bill_handler.register_dispenser(
            denomination=20,
            motor1_forward_pin=20, motor1_backward_pin=21, motor1_enable_pin=16, motor1_speed=0.6,
            motor2_forward_pin=19, motor2_backward_pin=26, motor2_enable_pin=13, motor2_speed=1.0,
            ir_sensor_pin=12
        )
        self.bill_handler.register_dispenser(
            denomination=50,
            motor1_forward_pin=9, motor1_backward_pin=11, motor1_enable_pin=10, motor1_speed=0.6,
            motor2_forward_pin=8, motor2_backward_pin=7, motor2_enable_pin=25, motor2_speed=1.0,
            ir_sensor_pin=5
        )
        
        
        # State tracking
        self.coin_insertion_done = threading.Event()
        self.total_coin_inserted = 0
        self.required_amount = 0 # For coin to bill
        self.required_fee = 0 # For bill flows
        
        print("\nInitialization complete!\n")

    def cleanup(self):
        print("\n[CLEANUP] Cleaning up handlers...")
        try:
            self.coin_handler.stop_accepting()
        except:
            pass
        self.bill_handler.cleanup()
        print("Cleanup complete.")

    def on_coin_inserted(self, denom, count, total):
        """Callback when a coin is inserted."""
        self.total_coin_inserted = total
        target = self.required_amount if self.required_amount > 0 else self.required_fee
        print(f"\nCoin inserted (Total: {total} / {target})")
        
        if total >= target:
            print(f"Target amount reached! ({total})")
            self.coin_insertion_done.set()
    
    def on_coins_finalized(self, total):
        """Callback when coin insertion is complete."""
        print(f"Coin insertion finalized. Total: {total}")
        self.coin_insertion_done.set()

    def get_bill_selection(self, fee_mapping):
        """Prompt user for bill amount to convert."""
        valid_amounts = sorted(fee_mapping.keys())
        print("Available bill amounts:")
        for amt in valid_amounts:
            fee = fee_mapping[amt]
            print(f"  {amt} (Fee: {fee})")
        
        while True:
            try:
                choice = input("\nEnter bill amount: ").strip()
                amount = int(choice)
                if amount in fee_mapping:
                    return amount
                else:
                    print(f"Invalid amount. Please choose from: {valid_amounts}")
            except ValueError:
                print("Please enter a valid number.")

    def get_coin_to_bill_amount(self):
        """Prompt user for bill amount to dispense (Coin to Bill)."""
        valid_amounts = sorted(COIN_TO_BILL_FEES.keys())
        print("Available bill amounts to dispense:")
        for amt in valid_amounts:
            fee = COIN_TO_BILL_FEES[amt]
            print(f"  {amt} (Fee: {fee}, Total Required: {amt + fee})")
        
        while True:
            try:
                choice = input("\nEnter bill amount to dispense: ").strip()
                amount = int(choice)
                if amount in COIN_TO_BILL_FEES:
                    return amount
                else:
                    print(f"Invalid amount. Please choose from: {valid_amounts}")
            except ValueError:
                print("Please enter a valid number.")

    def get_denomination_selection(self, amount_to_dispense, is_coin=False):
        """Prompt user to select preferred denominations."""
        if is_coin:
            available_denoms = [20, 10, 5, 1]
            storage = self.coin_handler.storage.get_storage()
            type_str = "Coin"
        else:
            available_denoms = [500, 200, 100, 50, 20]
            storage = self.bill_handler.storage.get_storage()
            type_str = "Bill"
            
        selected = set(available_denoms) # Default all selected
        
        while True:
            print("\n" + "-" * 40)
            print(f"Select {type_str} Denominations to Dispense:")
            print("-" * 40)
            
            valid_options = []
            for denom in available_denoms:
                # Rule 1: Denom <= amount to dispense
                if denom > amount_to_dispense:
                    status = "[DISABLED - Amount too low]"
                # Rule 2: Storage >= 5
                elif storage.get(denom, 0) < 5:
                    status = f"[DISABLED - Low Storage ({storage.get(denom, 0)})]"
                else:
                    status = "[SELECTED]" if denom in selected else "[ ]"
                    valid_options.append(denom)
                
                print(f"  {denom}: {status}")
            
            print("-" * 40)
            print("Enter denomination to toggle, 'all' to select all, 'none' to clear, or 'done' to finish.")
            choice = input("Choice: ").strip().lower()
            
            if choice == 'done':
                if not selected:
                    print("You must select at least one denomination (or we will default to auto).")
                    retry = input("Proceed with AUTO selection? (y/n): ").lower()
                    if retry == 'y':
                        return available_denoms
                else:
                    return sorted(list(selected), reverse=True)
            
            elif choice == 'all':
                selected = set(valid_options)
            
            elif choice == 'none':
                selected.clear()
                
            else:
                try:
                    denom = int(choice)
                    if denom in valid_options:
                        if denom in selected:
                            selected.remove(denom)
                        else:
                            selected.add(denom)
                    else:
                        print("Invalid denomination or not available.")
                except ValueError:
                    print("Invalid input.")

    def run_coin_to_bill(self):
        print("\n--- Coin to Bill Conversion ---")
        try:
            selected_amount = self.get_coin_to_bill_amount()
            fee = COIN_TO_BILL_FEES[selected_amount]
            self.required_amount = selected_amount + fee
            self.required_fee = 0 # Not used here
            
            print("\n" + "=" * 60)
            print(f"Bill Amount: {selected_amount}")
            print(f"Service Fee: {fee}")
            print(f"Total Required: {self.required_amount}")
            print("=" * 60)
            
            print(f"\nPlease insert {self.required_amount} in coins...")
            
            self.coin_insertion_done.clear()
            self.total_coin_inserted = 0
            
            self.coin_handler.add_callback(self.on_coin_inserted)
            self.coin_handler.add_reached_callback(self.on_coins_finalized)
            
            # Reset session counters to track this specific transaction
            self.coin_handler.session_counts = {k: 0 for k in self.coin_handler.session_counts}
            self.coin_handler.total_value = 0

            self.coin_handler.start_accepting(self.required_amount)
            
            if not self.coin_insertion_done.wait(timeout=COIN_INSERTION_TIMEOUT):
                print("\n[TIMEOUT] Coin insertion timed out.")
                self.coin_handler.stop_accepting()
                
                # Refund logic
                if self.total_coin_inserted > 0:
                    print(f"\n[REFUND] You inserted: {self.total_coin_inserted}")
                    print("Returning your coins...")
                    # Construct refund breakdown from session counts
                    refund_breakdown = {k: v for k, v in self.coin_handler.session_counts.items() if v > 0}
                    self.dispense_items(bill_breakdown={}, coin_breakdown=refund_breakdown)
                else:
                    print("\n[INFO] No coins inserted. Returning to menu.")
                    
                return

            self.coin_handler.stop_accepting()
            time.sleep(0.5)
            
            excess = self.total_coin_inserted - self.required_amount
            amount_to_dispense = selected_amount + excess
            
            print("\n" + "=" * 60)
            print(f"Coins Inserted: {self.total_coin_inserted}")
            print(f"Required: {self.required_amount}")
            print(f"Excess: {excess}")
            print(f"Amount to Dispense: {amount_to_dispense}")
            print("=" * 60)
            
            # Select denominations (Bills)
            # Note: Test used hardcoded [20], but we can ask user if they want
            # However, Coin to Bill usually dispenses specific bills.
            # Let's use the selection logic but for bills.
            selected_denoms = self.get_denomination_selection(amount_to_dispense, is_coin=False)
            
            print("\n[CONVERSION] Calculating breakdown...")
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

            # Dispense
            self.dispense_items(bill_breakdown, coin_breakdown)
            
        except Exception as e:
            print(f"Error in Coin to Bill: {e}")
            import traceback
            traceback.print_exc()

    def run_bill_to_coin(self):
        print("\n--- Bill to Coin Conversion ---")
        try:
            selected_amount = self.get_bill_selection(BILL_TO_COIN_FEES)
            self.required_fee = BILL_TO_COIN_FEES[selected_amount]
            self.required_amount = 0 # Not used
            
            print("\n" + "=" * 60)
            print(f"Selected Amount: {selected_amount}")
            print(f"Service Fee: {self.required_fee}")
            print("=" * 60)
            
            print(f"\nPlease insert a {selected_amount} peso bill...")
            success, denom, msg = self.bill_handler.accept_bill(
                required_denom=selected_amount,
                wait_for_ir_timeout_s=60
            )
            
            if success:
                print(f"\n[SUCCESS] Bill accepted: {denom}")
            else:
                print(f"\n[FAILED] Bill acceptance failed: {msg}")
                return

            # Fee Payment
            pay_with_coins = self.ask_pay_fee_with_coins()
            
            if pay_with_coins:
                self.process_fee_payment()
            else:
                print("\n[INFO] Fee will be deducted from the bill amount.")
                self.total_coin_inserted = 0
            
            excess_coins = self.total_coin_inserted - self.required_fee
            if excess_coins < 0:
                print("\n[INFO] Insufficient coins for fee. Deducting fee from bill amount.")
                amount_to_dispense = selected_amount - self.required_fee + self.total_coin_inserted
            else:
                amount_to_dispense = selected_amount + excess_coins
            
            print(f"Total Amount to Dispense: {amount_to_dispense}")
            
            selected_denoms = self.get_denomination_selection(amount_to_dispense, is_coin=True)
            
            print("\n[CONVERSION] Calculating breakdown...")
            coin_storage = self.coin_handler.storage.get_storage()
            
            breakdown = convert_bill_to_coin(
                amount=amount_to_dispense,
                selected_denoms=selected_denoms,
                storage=coin_storage
            )
            
            print(f"Coin Breakdown: {breakdown}")
            
            if not breakdown:
                print("\n[ERROR] Cannot dispense with available storage.")
                return
                
            self.dispense_items({}, breakdown)

        except Exception as e:
            print(f"Error in Bill to Coin: {e}")
            import traceback
            traceback.print_exc()

    def run_bill_to_bill(self):
        print("\n--- Bill to Bill Conversion ---")
        try:
            selected_amount = self.get_bill_selection(BILL_TO_BILL_FEES)
            self.required_fee = BILL_TO_BILL_FEES[selected_amount]
            self.required_amount = 0
            
            print("\n" + "=" * 60)
            print(f"Selected Amount: {selected_amount}")
            print(f"Service Fee: {self.required_fee}")
            print("=" * 60)
            
            print(f"\nPlease insert a {selected_amount} peso bill...")
            success, denom, msg = self.bill_handler.accept_bill(
                required_denom=selected_amount,
                wait_for_ir_timeout_s=60
            )
            
            if success:
                print(f"\n[SUCCESS] Bill accepted: {denom}")
            else:
                print(f"\n[FAILED] Bill acceptance failed: {msg}")
                return

            pay_with_coins = self.ask_pay_fee_with_coins()
            
            if pay_with_coins:
                self.process_fee_payment()
            else:
                print("\n[INFO] Fee will be deducted from the bill amount.")
                self.total_coin_inserted = 0
            
            excess_coins = self.total_coin_inserted - self.required_fee
            if excess_coins < 0:
                print("\n[INFO] Insufficient coins for fee. Deducting fee from bill amount.")
                amount_to_dispense = selected_amount - self.required_fee + self.total_coin_inserted
            else:
                amount_to_dispense = selected_amount + excess_coins
            
            print(f"Total Amount to Dispense: {amount_to_dispense}")
            
            selected_denoms = self.get_denomination_selection(amount_to_dispense, is_coin=False)
            
            print("\n[CONVERSION] Calculating breakdown...")
            bill_storage = self.bill_handler.storage.get_storage()
            coin_storage = self.coin_handler.storage.get_storage()
            
            bill_breakdown, coin_breakdown = convert_bill_to_bills(
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
            
            self.dispense_items(bill_breakdown, coin_breakdown)

        except Exception as e:
            print(f"Error in Bill to Bill: {e}")
            import traceback
            traceback.print_exc()

    def ask_pay_fee_with_coins(self):
        print("\n" + "=" * 60)
        print(f"Service Fee: {self.required_fee}")
        print("=" * 60)
        while True:
            choice = input("Do you want to insert coins for the fee? (y/n) [y]: ").strip().lower()
            if choice in ['', 'y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False

    def process_fee_payment(self):
        print(f"\nPlease insert {self.required_fee} in coins for the service fee...")
        self.coin_insertion_done.clear()
        self.total_coin_inserted = 0
        
        # Reset coin handler state
        self.coin_handler.session_counts = {k: 0 for k in self.coin_handler.session_counts}
        self.coin_handler.total_value = 0
        
        self.coin_handler.add_callback(self.on_coin_inserted)
        self.coin_handler.add_reached_callback(self.on_coins_finalized)
        
        self.coin_handler.start_accepting(self.required_fee)
        
        if not self.coin_insertion_done.wait(timeout=COIN_INSERTION_TIMEOUT):
            print("\n[TIMEOUT] Coin insertion timed out.")
        
        self.coin_handler.stop_accepting()
        time.sleep(0.5)

    def dispense_items(self, bill_breakdown, coin_breakdown):
        # Dispense Bills
        if bill_breakdown:
            print("\nDispensing bills...")
            for denom, qty in bill_breakdown.items():
                print(f"  Dispensing {denom} x{qty}...")
                success, msg = self.bill_handler.dispense_bill(denom, qty)
                if success:
                    print(f"  [DONE] Successfully dispensed {denom} x{qty}")
                else:
                    print(f"  [FAILED] Failed to dispense {denom} x{qty}: {msg}")
                    return

        # Dispense Coins
        if coin_breakdown:
            print("\nDispensing coins...")
            dispense_done_event = threading.Event()
            
            def on_dispense_ack(denom, qty):
                print(f"  [ACK] Dispensing {denom} x{qty}...")
            
            def on_dispense_done(denom, qty):
                print(f"  [DONE] Successfully dispensed {denom} x{qty}")
                dispense_done_event.set()
                
            self.coin_handler.add_dispense_callback(on_dispense_ack)
            self.coin_handler.add_dispense_done_callback(on_dispense_done)
            
            for denom, qty in coin_breakdown.items():
                print(f"  Requesting dispense: {denom} x{qty}...")
                dispense_done_event.clear()
                self.coin_handler.dispense(denom, qty)
                
                if not dispense_done_event.wait(timeout=15):
                    print(f"  [TIMEOUT] Dispense timed out for {denom} x{qty}")
                
                time.sleep(1)
        
        print("\n" + "=" * 60)
        print("TRANSACTION COMPLETE!")
        print("=" * 60)

    def run(self):
        while True:
            print("\n" + "=" * 60)
            print("MAIN MENU")
            print("=" * 60)
            print("1. Coin to Bill")
            print("2. Bill to Coin")
            print("3. Bill to Bill")
            print("4. Exit")
            
            choice = input("\nSelect operation (1-4): ").strip()
            
            if choice == '1':
                self.run_coin_to_bill()
            elif choice == '2':
                self.run_bill_to_coin()
            elif choice == '3':
                self.run_bill_to_bill()
            elif choice == '4':
                print("Exiting...")
                break
            else:
                print("Invalid selection. Please try again.")
            
            # Small delay before showing menu again
            time.sleep(1)

def main():
    terminal = CoinnectTerminal()
    try:
        terminal.run()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    finally:
        terminal.cleanup()

if __name__ == "__main__":
    main()
