import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_handler import BillStorage
from demo.coin_handler import CoinStorage

bill_storage = BillStorage()
coin_storage = CoinStorage()

def convert_coins_to_bills(amount, selected_denoms=None):
    """
    Conversion of coin amount into bills (and coins if needed).

    Args:
        amount (int): The total amount to convert.
        selected_denoms (list[int] | None): User-selected bill denominations.
                                            If None or empty, auto mode uses all bills.

    Returns:
        tuple: (success: bool, breakdown: dict)
               breakdown = {bill_denom: count, "coin_X": count}
    """
    print(f"[convert_coins_to_bills] Requested convert: {amount}, user selected={selected_denoms}")

    if amount <= 0:
        print("[convert_coins_to_bills] ERROR: Amount must be positive")
        return False, {}
    
    # Auto mode → use all bill denominations
    if not selected_denoms:
        denoms = [500, 200, 100, 50, 20]
    else:
        denoms = selected_denoms

    # Sort descending
    denoms = sorted(denoms, reverse=True)

    breakdown = {}
    remaining = amount

    # --- Case 1: Single denom selected → greedy ---
    if len(denoms) == 1:
        denom = denoms[0]
        available = bill_storage.get_count(denom)
        print(f"[simulate_convert_coins_to_bills] Single denom selected: {denom} available={available}")
        needed = remaining // denom
        print(f"[simulate_convert_coins_to_bills] Need {needed} of {denom}")
        to_use = min(available, needed)
        print(f"[simulate_convert_coins_to_bills] Will use {to_use} of {denom}")

        if to_use > 0:
            breakdown[denom] = to_use
            remaining -= denom * to_use

        # Fallback to smaller bills if still remainder
        for smaller in [d for d in [500, 200, 100, 50, 20] if d < denom]:
            if remaining <= 0:
                break
            available = bill_storage.get_count(smaller)
            needed = remaining // smaller
            to_use = min(available, needed)
            if to_use > 0:
                breakdown[smaller] = breakdown.get(smaller, 0) + to_use
                remaining -= smaller * to_use

    # --- Case 2: Multiple denoms (or auto) → fair distribution ---
    else:
        # Track a temporary copy of availability (don’t modify real storage here)
        availability = {d: bill_storage.get_count(d) for d in denoms}

        while remaining > 0 and any(availability[d] > 0 for d in denoms):
            progress = False
            for denom in denoms:
                if remaining >= denom and availability[denom] > 0:
                    breakdown[denom] = breakdown.get(denom, 0) + 1
                    remaining -= denom
                    availability[denom] -= 1
                    progress = True
                if remaining <= 0:
                    break
            if not progress:
                break

    # --- Phase 2: Fallback to coins if bills insufficient ---
    if remaining > 0:
        print(f"[simulate_convert_coins_to_bills] Bills insufficient, checking coins for remainder={remaining}")

        # 🔹 IMPORTANT: Only use coins smaller than the smallest bill denom used
        min_bill = min(denoms) if denoms else 1000  # fallback if somehow empty

        for coin in [10, 5, 1] if min_bill <= 20 else [20, 10, 5, 1]:
            if remaining <= 0:
                break
            available = coin_storage.get_count(coin)
            needed = remaining // coin
            to_use = min(available, needed)
            if to_use > 0:
                breakdown[f"coin_{coin}"] = breakdown.get(f"coin_{coin}", 0) + to_use
                remaining -= coin * to_use

    # --- Final check ---
    if remaining > 0:
        print("[convert_coins_to_bills] ERROR: Not enough bills/coins to convert")
        return False, {}

    print(f"[convert_coins_to_bills] SUCCESS: breakdown={breakdown}")
    return True, breakdown


def commit_dispense(breakdown):
    """
    Deduct bills and coins from storage based on breakdown.

    Args:
        breakdown (dict): {bill_denom: count, "coin_X": count}
    """
    for denom, count in breakdown.items():
        if isinstance(denom, int):  # bill
            bill_storage.deduct(denom, count)
        elif str(denom).startswith("coin_"):
            coin_value = int(denom.replace("coin_", ""))
            coin_storage.deduct(coin_value, count)

    print(f"[commit_dispense] Dispensed successfully: {breakdown}")
