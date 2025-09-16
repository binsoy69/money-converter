# threads.py
from PyQt5.QtCore import QThread, pyqtSignal
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from demo.bill_handler import BillHandler
#from demo.coin_handler import CoinHandler
from coin_handler.python.coin_handler_serial import * 

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

class CoinAcceptorWorker(QThread):
    coinInserted = pyqtSignal(int, int, int)   # denom, count, total
    coinsProcessed = pyqtSignal(int)           # final total value

    def __init__(self, required_fee):
        super().__init__()
        self.required_fee = required_fee
        self.handler = CoinHandlerSerial(required_fee)
        self._running = True

        # Register callbacks
        self.handler.add_callback(self._emit_coin_inserted)
        self.handler.add_reached_callback(self._emit_required_reached)

    def _emit_coin_inserted(self, denom, count, total):
        self.coinInserted.emit(denom, count, total)
        if self.required_fee > 0 and total >= self.required_fee:
            self.stop()

    def _emit_required_reached(self, total_value):
        self.coinsProcessed.emit(int(total_value))

    def run(self):
        try:
            self.handler.start_accepting()
        except Exception as e:
            print("[CoinAcceptorWorker] start_accepting error:", e)

        while self._running:
            time.sleep(0.1)

        try:
            self.handler.stop_accepting()
        except Exception as e:
            print("[CoinAcceptorWorker] stop_accepting error:", e)

    def stop(self):
        print("[CoinAcceptorWorker] Stopping...")
        self._running = False
        self.quit()

class CoinDispenserWorker(QThread):
    dispenseAck = pyqtSignal(int, int)   # denom, qty
    dispenseDone = pyqtSignal(int, int)  # denom, qty
    dispenseError = pyqtSignal(str)      # error message

    def __init__(self, breakdown: dict):
        """
        breakdown = {denom: qty}
        """
        super().__init__()
        self.breakdown = breakdown
        self.handler = CoinHandlerSerial(required_fee=0)  # fee irrelevant for dispensing
        self._running = True

        # Register callbacks
        self.handler.add_dispense_callback(self._emit_dispense_ack)
        self.handler.add_dispense_done_callback(self._emit_dispense_done)
        self.handler.add_error_callback(self._emit_dispense_error)

    def _emit_dispense_ack(self, denom, qty):
        self.dispenseAck.emit(denom, qty)

    def _emit_dispense_done(self, denom, qty):
        self.dispenseDone.emit(denom, qty)

    def _emit_dispense_error(self, msg):
        self.dispenseError.emit(msg)

    def run(self):
        try:
            # open port and reader loop
            self.handler.open()
        except Exception as e:
            print("[CoinDispenserWorker] open error:", e)

        # Send dispense commands one by one
        for denom, qty in self.breakdown.items():
            if qty > 0:
                self.handler.dispense(denom, qty)
                # short pause so Arduino processes sequentially
                time.sleep(0.2)

        # Keep listening until stopped
        while self._running:
            time.sleep(0.1)

    def stop(self):
        print("[CoinDispenserWorker] Stopping...")
        self._running = False
        self.handler.close()
        self.quit()
