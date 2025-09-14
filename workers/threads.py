# threads.py
from PyQt5.QtCore import QThread, pyqtSignal
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_handler import BillHandler
from demo.coin_handler import CoinHandler

class BillAcceptorWorker(QThread):
    bill_result = pyqtSignal(bool, str)   # success flag, denomination
    finished = pyqtSignal()

    def __init__(self, selected_bill):
        super().__init__()
        self._running = True
        self.selected_bill = selected_bill
        self.handler = BillHandler(selected_bill)   # your imported class

    def run(self):
        print("[BillAcceptorWorker] Starting with BillHandler...")
        success, inserted_bill = self.handler.verify_bill()
        self.bill_result.emit(success, str(inserted_bill))
        self.finished.emit()

    def stop(self):
        print("[BillAcceptorWorker] Stopping...")
        self._running = False

class CoinHandlerWorker(QThread):
    coinInserted = pyqtSignal(int, int, int)   # denom, count, total
    coinsProcessed = pyqtSignal(int)           # final total value

    def __init__(self, required_fee):
        super().__init__()
        self.required_fee = required_fee
        self.handler = CoinHandler(required_fee)
        self._running = True

        # Register callback for live updates
        self.handler.add_callback(self._emit_coin_inserted)

    def _emit_coin_inserted(self, denom, count, total):
        self.coinInserted.emit(denom, count, total)
        if total >= self.required_fee:
            self.stop()
            
            

    def run(self):
        print("[CoinHandlerWorker] Waiting for coins...")

        # Nothing to do here — now we just wait until insert_coin is called externally
        while self._running:
            self.msleep(100)

        self.coinsProcessed.emit(self.handler.total_value)

    def stop(self):
        print("[CoinHandlerWorker] Stopping...")
        self._running = False
        self.quit()

