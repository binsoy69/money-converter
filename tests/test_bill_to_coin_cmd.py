import os
import sys
import pprint

# ensure project root on path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from demo import bill_to_coin_converter as btc
from bill_handler.python.pi_bill_handler import PiBillHandler

# Simple in-memory coin storage used by dispense_coins()
class DummyCoinStorage:
    def __init__(self, storage):
        self._storage = storage

    def get_storage(self):
        return dict(self._storage)

    def dispense(self, denom, count):
        available = self._storage.get(denom, 0)
        to_dispense = min(count, available)
        self._storage[denom] = available - to_dispense
        return to_dispense

def choose_bill():
    valid = [20,50,100,200,500,1000]
    while True:
        try:
            v = int(input(f"Choose bill to convert {valid}: ").strip())
            if v in valid:
                return v
        except Exception:
            pass
        print("Invalid choice.")

def main():
    print("=== Test: Bill -> Coin ===")
    bill = choose_bill()

    # Preferred coin denoms (example); empty -> AUTO
    preferred = [20,10,5,1]
    # Sample coin storage counts
    coin_storage = {20: 10, 10: 20, 5: 50, 1: 100}

    print("Converting bill to coin (simulation)...")
    breakdown = btc.convert_bill_to_coin(bill, preferred, coin_storage)
    print("Planned coin breakdown:")
    pprint.pprint(breakdown)

    handler = PiBillHandler()  # hardware abstraction (mock if not on Pi)
    print("Please insert bill now (PiBillHandler will wait/detect)...")
    ok, denom_or_none, reason = handler.accept_bill(bill)
    if not ok:
        print("Bill acceptance failed:", denom_or_none, reason)
        return

    print("Bill accepted and sorted:", denom_or_none)

    # Dispense coins via dummy storage using utility function
    storage_wrapper = DummyCoinStorage(coin_storage)
    print("Dispensing coins (simulation)...")
    btc.dispense_coins(breakdown, storage_wrapper)
    print("Remaining coin storage:", storage_wrapper.get_storage())

if __name__ == "__main__":
    main()