
import os
import sys
import json
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from bill_handler.python.bill_storage import BillStorage
from coin_handler.python.coin_storage import CoinStorage

def test_bill_storage():
    print("\n--- Testing Bill Storage ---")
    storage = BillStorage()
    print(f"File path: {os.path.abspath(storage.filepath)}")
    
    initial_counts = storage.get_storage()
    print(f"Initial counts: {initial_counts}")
    
    # Test Add
    print("Adding 1 x 20...")
    storage.add(20, 1)
    
    # Verify file update
    with open(storage.filepath, 'r') as f:
        data = json.load(f)
        print(f"File content after add: {data}")
    
    if int(data['20']) != initial_counts.get(20, 0) + 1:
        print("FAIL: File was not updated correctly after ADD.")
    else:
        print("SUCCESS: File updated after ADD.")

    # Test Deduct
    print("Deducting 1 x 20...")
    success = storage.deduct(20, 1)
    if not success:
        print("FAIL: Deduct returned False (insufficient funds?)")
    
    # Verify file update
    with open(storage.filepath, 'r') as f:
        data = json.load(f)
        print(f"File content after deduct: {data}")

    if int(data['20']) != initial_counts.get(20, 0):
        print("FAIL: File was not updated correctly after DEDUCT.")
    else:
        print("SUCCESS: File updated after DEDUCT.")

def test_coin_storage():
    print("\n--- Testing Coin Storage ---")
    storage = CoinStorage()
    print(f"File path: {os.path.abspath(storage.storage_file)}")
    
    initial_counts = storage.get_storage()
    print(f"Initial counts: {initial_counts}")
    
    # Test Add
    print("Adding 1 x 5...")
    storage.add(5, 1)
    
    # Verify file update
    with open(storage.storage_file, 'r') as f:
        data = json.load(f)
        # keys in coin_storage might be strings in json, CoinStorage handles int conversion
        print(f"File content after add: {data}")
    
    # JSON keys are always strings
    val_in_file = int(data.get('5', data.get(5, 0)))
    if val_in_file != initial_counts.get(5, 0) + 1:
        print("FAIL: File was not updated correctly after ADD.")
    else:
        print("SUCCESS: File updated after ADD.")

if __name__ == "__main__":
    try:
        test_bill_storage()
        test_coin_storage()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
