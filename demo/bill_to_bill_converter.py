from typing import List, Dict, Tuple

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

def convert_bill_to_bills(amount: int, selected_denoms: List[int], bill_storage: Dict[int, int], coin_storage: Dict[int, int]) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Convert a larger bill into smaller bills and coins (if applicable).

    Args:
        amount: The bill amount to convert.
        selected_denoms: List of preferred smaller bill denominations (if empty → AUTO).
        bill_storage: Dict {bill: count} available.
        coin_storage: Dict {coin: count} available.

    Returns:
        Tuple (bills_breakdown, coins_breakdown)
        If not enough storage to convert → both dicts empty.
    """
    if amount <= 0:
        print("[Convert] Nothing to convert.")
        return {}, {}

    # Auto mode → all smaller bills
    denoms = sorted(selected_denoms, reverse=True) if selected_denoms else [500, 200, 100, 50, 20]
    # Only allow denominations strictly smaller than the bill being converted
    denoms = [d for d in denoms if d < amount]

    if not denoms:
        print(f"[Convert] ERROR: No valid smaller bill denominations available for {amount}.")
        return {}, {}

    # --- Phase 1: Try to break into smaller bills ---
    sim_bill_storage = bill_storage.copy()
    bills_breakdown, remaining = simulate_dispense(amount, denoms, sim_bill_storage)

    # --- Phase 2: If remainder → try coins ---
    coins_breakdown = {}
    if remaining > 0:
        print(f"[Convert] Bills insufficient. Remainder={remaining}, trying coins...")
        sim_coin_storage = coin_storage.copy()

        # Coins are always smaller than any bill denom
        coins_breakdown, remaining = simulate_dispense(remaining, [20, 10, 5, 1], sim_coin_storage)

    # --- Final check ---
    if remaining > 0:
        print(f"[Convert] ERROR: Cannot break {amount}. Not enough bills/coins in storage.")
        return {}, {}

    return bills_breakdown, coins_breakdown
