
import json
import os

class CoinStorage:
    def __init__(self, initial_count=30, storage_file="coin_storage.json"):
        self.storage_file = storage_file
        self.default_count = initial_count

        # Try loading from file, otherwise reset and save default
        if os.path.exists(self.storage_file):
            self.load()
        else:
            self.reset_storage(initial_count)
            self.save()

    # --- Basic accessors --- #
    def get_storage(self):
        """Return a copy of the current storage state."""
        return self.storage.copy()

    def get_all(self):
        """Alias to get_storage for readability."""
        return self.get_storage()

    def get_count(self, denomination):
        """Return available count for a specific coin denomination (int)."""
        return int(self.storage.get(int(denomination), 0))

    # --- Mutators --- #
    def reset_storage(self, initial_count=None):
        """Refill all coin bins back to the initial count."""
        if initial_count is None:
            initial_count = self.default_count
        self.storage = {
            20: initial_count,
            10: initial_count,
            5: initial_count,
            1: initial_count
        }
        print(f"[CoinStorage] Reset storage to {initial_count} per denomination.")
        self.save()

    def add(self, denomination, count=1):
        """Add coins to storage and persist. Returns new count."""
        d = int(denomination)
        self.storage[d] = self.storage.get(d, 0) + int(count)
        self.save()
        print(f"[CoinStorage] Added {count} of {d}. New count = {self.storage[d]}")
        return self.storage[d]

    def deduct(self, denomination, count=1):
        """
        Deduct up to `count` coins from storage.
        Returns the actual number deducted (0..count).
        """
        d = int(denomination)
        if d not in self.storage:
            print(f"[CoinStorage] deduct: Unknown denomination {d}")
            return 0
        available = self.storage[d]
        to_deduct = min(int(count), available)
        self.storage[d] = available - to_deduct
        self.save()
        if to_deduct < count:
            print(f"[CoinStorage] Warning: insufficient {d}s. Deducted {to_deduct}/{count}.")
        else:
            print(f"[CoinStorage] Deducted {to_deduct} of {d}.")
        return to_deduct

    # Keep dispense() for backward compatibility (same semantics as deduct)
    def dispense(self, denomination, count):
        """
        Backwards-compatible method: deduct coins and return actual number dispensed.
        """
        return self.deduct(denomination, count)

    # --- Persistence --- #
    def save(self):
        """Save storage state to JSON file."""
        try:
            # JSON requires string keys; dump will convert ints to strings automatically.
            with open(self.storage_file, "w") as f:
                json.dump(self.storage, f)
            print("[CoinStorage] Storage saved to file.")
        except Exception as e:
            print(f"[CoinStorage] Error saving storage: {e}")

    def load(self):
        """Load storage state from JSON file (converts keys back to int)."""
        try:
            with open(self.storage_file, "r") as f:
                raw = json.load(f)
            # ensure keys are ints
            self.storage = {int(k): int(v) for k, v in raw.items()}
            print("[CoinStorage] Storage loaded from file.")
        except Exception as e:
            print(f"[CoinStorage] Error loading storage, resetting. {e}")
            self.reset_storage()
