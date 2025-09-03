from PyQt5.QtCore import QThread, pyqtSignal
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_handler import BillHandler

# Worker thread for handling bill verification
class BillHandlerWorker(QThread):
    billProcessed = pyqtSignal(bool, int)  # success, amount

    def __init__(self, amount_expected, amount_inserted=None, bill_handler=None):
        super().__init__()
        self.bill_handler = bill_handler if bill_handler else BillHandler()
        self.amount_expected = amount_expected
        self.amount_inserted = amount_inserted if amount_inserted is not None else amount_expected
        self._running = True

    def run(self):
        """Run once for this simulation."""
        result = self.bill_handler.verify_bill(self.amount_inserted, self.amount_expected)
        if isinstance(result, tuple) and len(result) == 2:
            success, amount = result
        else:
            success, amount = False, 0
        self.billProcessed.emit(success, amount)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()

# Worker thread for handling coin verification

class CoinHandlerWorker(QThread):
    # success, total_value_in_pesos
    coinsProcessed = pyqtSignal(bool, int)
    # denomination, count_for_that_denom, total_value_in_pesos
    coinInserted  = pyqtSignal(int, int, int)

    def __init__(self, required_fee):
        super().__init__()
        self.required_fee = max(0, int(required_fee))  # the transaction fee to cover
        self._running = True

    def run(self):
        """
        Simulate coin insertion via console:
        - Accepts 1, 5, 10, 20
        - Type 'done' to stop early
        """
        coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        total_value = 0

        while self._running and total_value < self.required_fee:
            try:
                raw = input(f"Insert coin (1/5/10/20), 'done' to finish "
                            f"[Current total: P{total_value} / Needed: P{self.required_fee}]: ").strip().lower()
            except EOFError:
                break

            if raw in ("done", "d", "q", "quit"):
                break

            try:
                denom = int(raw)
            except ValueError:
                print("[CoinHandlerWorker] Invalid input. Use 1/5/10/20 or 'done'.")
                continue

            if denom not in coin_counts:
                print("[CoinHandlerWorker] Invalid denomination. Use 1/5/10/20.")
                continue

            # update counts and total
            coin_counts[denom] += 1
            total_value += denom

            # emit denomination, denom_count, and running peso total
            self.coinInserted.emit(denom, coin_counts[denom], total_value)

        success = (total_value >= self.required_fee)
        self.coinsProcessed.emit(success, total_value)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()
