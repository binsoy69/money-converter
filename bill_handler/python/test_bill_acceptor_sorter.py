#!/usr/bin/env python3
"""
Automated test for PiBillHandler bill acceptance & sorting
"""

import time
from pi_bill_handler import PiBillHandler


def run_acceptance_test(required_denom=100, trials=3):
    handler = PiBillHandler(use_hardware=False)  # set True on Raspberry Pi
    print("=== Automated Bill Acceptance & Sorting Test ===")
    print(f"Required denomination: {required_denom}")
    print(f"Trials: {trials}\n")

    results = []
    try:
        for i in range(trials):
            print(f"\n--- Trial {i+1} ---")
            ok, denom, reason = handler.accept_bill(required_denom=required_denom)
            print(f"Result: ok={ok}, denom={denom}, reason={reason}")
            results.append((ok, denom, reason))
            time.sleep(2)  # pause before next trial
    finally:
        handler.cleanup()

    print("\n=== Summary ===")
    for i, (ok, denom, reason) in enumerate(results, 1):
        print(f"Trial {i}: ok={ok}, denom={denom}, reason={reason}")


if __name__ == "__main__":
    # Example: require ₱100 bill, test 3 times
    run_acceptance_test(required_denom=100, trials=3)
