import time

class CoinHandler:
    def __init__(self):
        print("[CoinHandler] Initialized.")
        self.coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}

    def verify_coins(self, coins_inserted, coins_expected):
        """
        Simulate coin verification.
        Returns:
            (success: bool, total_coins: int)
        """
        print("[CoinHandler] Verifying coins...")
        time.sleep(2)  # Simulate processing time

        success = False
        total_coins = coins_inserted
        if coins_inserted == coins_expected:
            success = True

        print(f"[CoinHandler] Verification result: success={success}, coins_expected={coins_expected}, coins_inserted={coins_inserted}")
        return success,