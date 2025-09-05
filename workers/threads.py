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
    coinInserted = pyqtSignal(int, int, int)   # denom, count, total_value
    finishedWithTotal = pyqtSignal(int)        # total_value

    def __init__(self, required_fee):
        super().__init__()
        self.required_fee = required_fee
        self._running = True
        self.coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        self.total_value = 0

    def run(self):
        print("[CoinHandlerWorker] Started simulation")
        while self._running and self.total_value < self.required_fee:
            try:
                raw = input(f"Insert coin (1/5/10/20) or 'done' [Total={self.total_value}]: ").strip()
            except EOFError:
                break

            if raw.lower() in ("done", "q", "quit"):
                break

            try:
                denom = int(raw)
            except ValueError:
                print("[CoinHandlerWorker] Invalid input.")
                continue

            if denom not in self.coin_counts:
                print("[CoinHandlerWorker] Invalid denomination.")
                continue

            self.coin_counts[denom] += 1
            self.total_value += denom
            self.coinInserted.emit(denom, self.coin_counts[denom], self.total_value)

        # Always emit the total at the end
        self.finishedWithTotal.emit(self.total_value)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()
