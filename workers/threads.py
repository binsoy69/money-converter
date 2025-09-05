from PyQt5.QtCore import QThread, pyqtSignal
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_handler import BillHandler

# Worker thread for handling bill verification
class BillHandlerWorker(QThread):
    bill_inserted = pyqtSignal(str)   # emits denomination string (e.g., "100")
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        print("[BillHandlerWorker] Simulation started. Waiting for user input...")
        while self._running:
            try:
                bill = input("Enter inserted bill (20/50/100/200/500/1000 or 'q' to quit): ").strip()
                if bill.lower() == "q":
                    print("[BillHandlerWorker] Quit signal received.")
                    self._running = False
                    break
                if bill in ["20", "50", "100", "200", "500", "1000"]:
                    print(f"[BillHandlerWorker] Simulated bill accepted: {bill}")
                    self.bill_inserted.emit(bill)
                    break   # Stop after 1 bill
                else:
                    print("[BillHandlerWorker] Invalid input. Please enter a valid denomination.")
            except Exception as e:
                print(f"[BillHandlerWorker] Error: {e}")
                break

        self.finished.emit()

    def stop(self):
        print("[BillHandlerWorker] Stopping...")
        self._running = False

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
