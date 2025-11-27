# test_converter.py

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_to_coin_converter import convert_bill_to_coin
from demo.bill_to_bill_converter import convert_bill_to_bills
from demo.coin_to_bill_converter import convert_coins_to_bills


def run_tests():
    bill_storage = {500: 2, 200: 3, 100: 5, 50: 10, 20: 20}
    coin_storage = {20: 15, 10: 30, 5: 40, 1: 50}

    print("\n=== Test 1: Coins → Bills (amount=780, prefer [500,200]) ===")
    bills, coins = convert_coins_to_bills(780, [500, 200], bill_storage, coin_storage)
    print("Bills:", bills)
    print("Coins:", coins)

    print("\n=== Test 2: Coins → Bills (amount=135, AUTO mode) ===")
    bills, coins = convert_coins_to_bills(23, [20], bill_storage, coin_storage)
    print("Bills:", bills)
    print("Coins:", coins)

    print("\n=== Test 3: Bill → Bills (amount=500, prefer [200,100,50,20]) ===")
    bills, coins = convert_bill_to_bills(500, [200, 100, 50, 20], bill_storage, coin_storage)
    print("Bills:", bills)
    print("Coins:", coins)

    print("\n=== Test 4: Bill → Bills (amount=200, AUTO mode) ===")
    bills, coins = convert_bill_to_bills(200, [], bill_storage, coin_storage)
    print("Bills:", bills)
    print("Coins:", coins)

if __name__ == "__main__":
    run_tests()
