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
