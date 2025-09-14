"""
coin_converter.py

Utility module for converting bills into coins.
Includes simulation and dispensing logic.
"""

from typing import Dict, Tuple, List


def simulate_dispense(amount: int, denoms: List[int], storage: Dict[int, int]) -> Tuple[Dict[int, int], int]:
    """
    Simulate dispensing coins for a given amount using selected denominations.

    Args:
        amount: The target amount to dispense.
        denoms: List of allowed denominations (e.g., [20, 10, 5, 1]).
        storage: Dict of available coins {denom: count}.

    Returns:
        breakdown: Dict {denom: count} showing how many coins to use.
        remaining: Amount that could not be dispensed.
    """
    breakdown = {}
    remaining = amount

    if len(denoms) == 1:  # Single denom → greedy then fallback
        denom = denoms[0]
        count_needed = remaining // denom
        can_use = min(count_needed, storage.get(denom, 0))
        if can_use > 0:
            breakdown[denom] = can_use
            remaining -= can_use * denom
            storage[denom] -= can_use

        # fallback to smaller denoms
        for smaller in [d for d in [20, 10, 5, 1] if d < denom]:
            count_needed = remaining // smaller
            can_use = min(count_needed, storage.get(smaller, 0))
            if can_use > 0:
                breakdown[smaller] = breakdown.get(smaller, 0) + can_use
                remaining -= can_use * smaller
                storage[smaller] -= can_use

    else:  # Multiple denoms → fair distribution
        while remaining > 0 and any(storage.get(d, 0) > 0 for d in denoms):
            progress = False
            for denom in denoms:
                if remaining >= denom and storage.get(denom, 0) > 0:
                    breakdown[denom] = breakdown.get(denom, 0) + 1
                    remaining -= denom
                    storage[denom] -= 1
                    progress = True
                if remaining <= 0:
                    break
            if not progress:
                break

        # fallback if still remainder
        if remaining > 0:
            for denom in [20, 10, 5, 1]:
                while remaining >= denom and storage.get(denom, 0) > 0:
                    breakdown[denom] = breakdown.get(denom, 0) + 1
                    remaining -= denom
                    storage[denom] -= 1

    return breakdown, remaining


def convert_bill_to_coin(amount: int, selected_denoms: List[int], storage: Dict[int, int]) -> Dict[int, int]:
    """
    Convert a bill amount into coins based on available storage.

    Args:
        amount: The bill amount to convert.
        selected_denoms: List of preferred denominations.
        storage: Dict {denom: count} of available coins.

    Returns:
        Dict {denom: count} representing the breakdown of coins dispensed.
        If not enough coins → returns empty dict.
    """
    if amount <= 0:
        print("[Convert] Nothing to dispense.")
        return {}

    # Rule: if selected amount is exactly 20, exclude 20-peso coins
    if amount == 20 and 20 in selected_denoms:
        selected_denoms.remove(20)
        print("[Convert] Rule applied: 20-peso coins excluded (amount = 20).")

    # Sort denoms (highest first)
    selected_denoms = sorted(selected_denoms, reverse=True) if selected_denoms else [20, 10, 5, 1]

    # --- Simulation phase ---
    sim_storage = storage.copy()
    breakdown, remaining = simulate_dispense(amount, selected_denoms, sim_storage)

    if remaining > 0:
        print(f"[Convert] Not enough coins with selected denoms. Remainder={remaining}. Trying AUTO...")
        sim_storage = storage.copy()
        breakdown, remaining = simulate_dispense(amount, [20, 10, 5, 1], sim_storage)

    if remaining > 0:
        print(f"[Convert] ERROR: Cannot dispense {amount}. Not enough coins in storage.")
        return {}

    return breakdown


def dispense_coins(breakdown: Dict[int, int], coin_storage, dispense_callback=None) -> None:
    """
    Actually dispense coins based on the breakdown.

    Args:
        breakdown: Dict {denom: count} from convert_bill_to_coin().
        coin_storage: CoinStorage object (must have get_storage() and dispense()).
        dispense_callback: Optional function (denom, count) -> None for extra hardware logic.
    """
    print("[Dispense] Dispensing coins:")

    for denom, count in breakdown.items():
        current_storage = coin_storage.get_storage()
        if current_storage.get(denom, 0) < count:
            print(f"  [ERROR] Not enough {denom}-peso coins in storage!")
            continue

        # Use coin_storage's dispense (updates internal state)
        dispensed = coin_storage.dispense(denom, count)

        # Trigger optional hardware callback
        if dispense_callback:
            dispense_callback(denom, dispensed)

        print(f"  {denom}: {dispensed} coin(s) dispensed")

    print("[Dispense] Remaining storage:", coin_storage.get_storage())