import json
import os
class CoinHandler:
    def __init__(self, required_fee):
        self.required_fee = required_fee
        self.coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        self.total_value = 0
        self._callbacks = []   # functions to call on coin insert

    def add_callback(self, callback):
        """Register a callback to notify on each coin insertion."""
        self._callbacks.append(callback)

    def insert_coin(self, denom: int):
        """Simulate inserting a coin of given denomination."""
        if denom not in self.coin_counts:
            print(f"[CoinHandler] Invalid denomination: {denom}")
            return False

        # Update state
        self.coin_counts[denom] += 1
        self.total_value += denom

        # Notify listeners
        for cb in self._callbacks:
            cb(denom, self.coin_counts[denom], self.total_value)

        # Return True if fee already reached/exceeded
        return self.total_value >= self.required_fee

    def finalize(self):
        """Manually finalize (like user pressing 'done')."""
        return self.total_value

class CoinStorage:
    def __init__(self, initial_count=30, storage_file="coin_storage.json"):
        self.storage_file = storage_file
        self.default_count = initial_count

        # Try loading from file, otherwise reset
        if os.path.exists(self.storage_file):
            self.load()
        else:
            self.reset_storage(initial_count)
            self.save()

    def get_storage(self):
        """Return a copy of the current storage state."""
        return self.storage.copy()

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

    def dispense(self, denomination, count):
        """
        Deduct coins from storage.
        Returns the actual number dispensed (in case storage < requested).
        """
        if denomination not in self.storage:
            raise ValueError(f"Unknown denomination: {denomination}")

        available = self.storage[denomination]
        to_dispense = min(count, available)
        self.storage[denomination] -= to_dispense
        self.save()  # persist after update

        if to_dispense < count:
            print(f"[CoinStorage] Warning: insufficient {denomination}s. Dispensed {to_dispense}/{count}.")
        else:
            print(f"[CoinStorage] Dispensed {to_dispense} of {denomination}.")

        return to_dispense

    # --- Persistence --- #
    def save(self):
        """Save storage state to JSON file."""
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.storage, f)
            print("[CoinStorage] Storage saved to file.")
        except Exception as e:
            print(f"[CoinStorage] Error saving storage: {e}")

    def load(self):
        """Load storage state from JSON file."""
        try:
            with open(self.storage_file, "r") as f:
                self.storage = {int(k): v for k, v in json.load(f).items()}
            print("[CoinStorage] Storage loaded from file.")
        except Exception as e:
            print(f"[CoinStorage] Error loading storage, resetting. {e}")
            self.reset_storage()
