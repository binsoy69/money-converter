#!/usr/bin/env python3
"""
Bill to Bill Conversion Test - Command Line Version
This program tests the full bill-to-bill conversion flow using actual handlers.
"""

import sys
import os
import time
import threading

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bill_handler.python.pi_bill_handler import PiBillHandler
from coin_handler.python.coin_handler_serial import CoinHandlerSerial
from demo.bill_to_bill_converter import convert_bill_to_bills

# Fee mapping (same as in billToBill_controller.py)
AMOUNT_FEE_MAPPING = {
    50: 2,
    100: 3,
    200: 5,
    500: 7,
    1000: 10
}

COIN_INSERTION_TIMEOUT = 120

class BillToBillTest:
    def __init__(self):
        print("=" * 60)
        print("Bill to Bill Conversion Test")
        print("=" * 60)
        
        # Initialize handlers
        print("\n[1/3] Initializing Bill Handler...")
        self.bill_handler = PiBillHandler()
        
        print("[2/3] Initializing Coin Handler...")
        self.coin_handler = CoinHandlerSerial()
        
        # State tracking
        self.coin_insertion_done = threading.Event()
        self.total_coin_inserted = 0
        self.required_fee = 0
        self.selected_amount = 0
        self.inserted_bill_amount = 0
        
        print("\nInitialization complete!\n")
    
    def get_bill_selection(self):
        """Prompt user for bill amount to convert."""
        valid_amounts = sorted(AMOUNT_FEE_MAPPING.keys())
        print("Available bill amounts to convert:")
        for amt in valid_amounts:
            fee = AMOUNT_FEE_MAPPING[amt]
            print(f"  {amt} (Fee: {fee})")
        
        while True:
            try:
                choice = input("\nEnter bill amount to convert: ").strip()
                amount = int(choice)
                if amount in AMOUNT_FEE_MAPPING:
                    return amount
                else:
                    print(f"Invalid amount. Please choose from: {valid_amounts}")
            except ValueError:
                print("Please enter a valid number.")

    def on_coin_inserted(self, denom, count, total):
        """Callback when a coin is inserted."""
        self.total_coin_inserted = total
        print(f"\nCoin inserted (Total: {total} / {self.required_fee})")
        
        if total >= self.required_fee:
            print(f"Required fee reached! ({total})")
            self.coin_insertion_done.set()
    
    def on_coins_finalized(self, total):
        """Callback when coin insertion is complete."""
        print(f"Coin insertion finalized. Total: {total}")
        self.coin_insertion_done.set()

    def get_denomination_selection(self, amount_to_dispense):
        """Prompt user to select preferred denominations."""
        available_denoms = [500, 200, 100, 50, 20]
        selected = set(available_denoms) # Default all selected
        
        while True:
            print("\n" + "-" * 40)
            print("Select Denominations to Dispense:")
            print("-" * 40)
            
            # Check storage availability (mock check based on UI logic)
            bill_storage = self.bill_handler.storage.get_storage()
            
            valid_options = []
            for denom in available_denoms:
                # Rule 1: Denom <= amount to dispense
                if denom > amount_to_dispense:
                    status = "[DISABLED - Amount too low]"
                # Rule 2: Storage >= 5 (from UI controller)
                elif bill_storage.get(denom, 0) < 5:
                    status = f"[DISABLED - Low Storage ({bill_storage.get(denom, 0)})]"
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
                        # Check constraints again
                        if denom > amount_to_dispense:
                            print(f"Cannot select {denom}: Amount to dispense ({amount_to_dispense}) is too low.")
                        elif bill_storage.get(denom, 0) < 5:
                            print(f"Cannot select {denom}: Low storage.")
                        else:
                            if denom in selected:
                                selected.remove(denom)
                            else:
                                selected.add(denom)
                    else:
                        print("Invalid denomination.")
                except ValueError:
                    print("Invalid input.")

    def run(self):
        """Run the bill-to-bill conversion test."""
        try:
            # Step 1: Select Bill Amount
            self.selected_amount = self.get_bill_selection()
            self.required_fee = AMOUNT_FEE_MAPPING[self.selected_amount]
            
            print("\n" + "=" * 60)
            print(f"Selected Amount: {self.selected_amount}")
            print(f"Service Fee: {self.required_fee}")
            print("=" * 60)
            
            # Step 2: Insert Bill
            print(f"\nPlease insert a {self.selected_amount} peso bill...")
            
            # Use accept_bill from PiBillHandler
            success, denom, msg = self.bill_handler.accept_bill(
                required_denom=self.selected_amount,
                wait_for_ir_timeout_s=60
            )
            
            if success:
                self.inserted_bill_amount = denom
                print(f"\n[SUCCESS] Bill accepted: {denom}")
            else:
                print(f"\n[FAILED] Bill acceptance failed: {msg}")
                if denom:
                     print(f"Detected denomination: {denom}")
                return

            # Step 3: Fee Payment Method
            print("\n" + "=" * 60)
            print(f"Service Fee: {self.required_fee}")
            print("=" * 60)
            
            pay_with_coins = False
            while True:
                choice = input("Do you want to insert coins for the fee? (y/n) [y]: ").strip().lower()
                if choice in ['', 'y', 'yes']:
                    pay_with_coins = True
                    break
                elif choice in ['n', 'no']:
                    pay_with_coins = False
                    break
            
            if pay_with_coins:
                print(f"\nPlease insert {self.required_fee} in coins for the service fee...")
                
                # Reset coin handler state
                self.coin_insertion_done.clear()
                self.total_coin_inserted = 0
                
                # Register callbacks
                self.coin_handler.add_callback(self.on_coin_inserted)
                self.coin_handler.add_reached_callback(self.on_coins_finalized)
                
                # Start coin acceptance
                self.coin_handler.start_accepting(self.required_fee)
                
                # Wait for enough coins or timeout
                if not self.coin_insertion_done.wait(timeout=COIN_INSERTION_TIMEOUT):
                    print("\n[TIMEOUT] Coin insertion timed out.")
                
                self.coin_handler.stop_accepting()
                time.sleep(0.5)
            else:
                print("\n[INFO] Fee will be deducted from the bill amount.")
                self.total_coin_inserted = 0
            
            # Step 4: Calculate Totals
            excess_coins = self.total_coin_inserted - self.required_fee
            
            if excess_coins < 0:
                # Insufficient coins, deduct fee from bill
                print("\n[INFO] Insufficient coins for fee. Deducting fee from bill amount.")
                amount_to_dispense = self.selected_amount - self.required_fee + self.total_coin_inserted
                print(f"  Bill Amount: {self.selected_amount}")
                print(f"  Fee Deducted: {self.required_fee}")
                print(f"  Coins Inserted (Added back): {self.total_coin_inserted}")
            else:
                # Sufficient coins
                amount_to_dispense = self.selected_amount + excess_coins
                print(f"\n[INFO] Fee covered.")
                print(f"  Bill Amount: {self.selected_amount}")
                print(f"  Excess Coins: {excess_coins}")

            print(f"  Total Amount to Dispense: {amount_to_dispense}")
            
            # Step 5: Select Denominations
            selected_denoms = self.get_denomination_selection(amount_to_dispense)
            print(f"\nSelected denominations: {selected_denoms}")
            
            # Step 6: Convert and Dispense
            print("\n[CONVERSION] Calculating bill/coin breakdown...")
            
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
                
                # Register dispense callbacks
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
                    
                    # Wait for dispense to complete
                    if not dispense_done_event.wait(timeout=15):
                        print(f"  [TIMEOUT] Dispense timed out for {denom} x{qty}")
                    
                    time.sleep(1)
            
            print("\n" + "=" * 60)
            print("TRANSACTION COMPLETE!")
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
            print("Cleanup complete.")

def main():
    test = BillToBillTest()
    test.run()

if __name__ == "__main__":
    main()
