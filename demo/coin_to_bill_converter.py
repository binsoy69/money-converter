from typing import List, Dict, Tuple

def simulate_dispense(amount: int, denoms: List[int], storage: Dict[int, int]) -> Tuple[Dict[int, int], int]:
    """
    Simulate dispensing using selected denominations (bills or coins).

    Args:
        amount: Target amount.
        denoms: List of allowed denominations.
        storage: Dict {denom: count} of available items.

    Returns:
        breakdown: Dict {denom: count} used.
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

        # fallback to smaller ones (if dispensing coins/bills)
        for smaller in sorted([d for d in storage.keys() if d < denom], reverse=True):
            if remaining <= 0:
                break
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

    return breakdown, remaining


def convert_coins_to_bills(amount: int, selected_denoms: List[int], bill_storage: Dict[int, int], coin_storage: Dict[int, int]) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Convert coin amount into bills (and coins if needed).

    Args:
        amount: Total amount to convert.
        selected_denoms: List of preferred bill denominations (if empty → AUTO).
        bill_storage: Dict {bill: count} available.
        coin_storage: Dict {coin: count} available.

    Returns:
        Tuple (bills_breakdown, coins_breakdown)
        If conversion not possible → both dicts empty.
    """
    if amount <= 0:
        print("[Convert] Nothing to convert.")
        return {}, {}

    # Auto mode = all bills
    denoms = sorted(selected_denoms, reverse=True) if selected_denoms else [500, 200, 100, 50, 20]

    # --- Phase 1: Try with bills ---
    sim_bill_storage = bill_storage.copy()
    bills_breakdown, remaining = simulate_dispense(amount, denoms, sim_bill_storage)

    # --- Phase 2: If remainder → try coins ---
    coins_breakdown = {}
    if remaining > 0:
        print(f"[Convert] Bills insufficient. Remainder={remaining}, trying coins...")
        sim_coin_storage = coin_storage.copy()

        # Rule: only use coins ≤ smallest bill denom chosen
        min_bill = min(denoms) if denoms else 1000
        coin_denoms = [c for c in [20, 10, 5, 1] if c < min_bill]

        coins_breakdown, remaining = simulate_dispense(remaining, coin_denoms, sim_coin_storage)

    # --- Final check ---
    if remaining > 0:
        print(f"[Convert] ERROR: Cannot convert {amount}. Not enough bills/coins.")
        return {}, {}

    return bills_breakdown, coins_breakdown
