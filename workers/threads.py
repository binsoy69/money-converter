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
    finished = pyqtSignal()

    def __init__(self, breakdown: dict, serial_port="/dev/ttyACM0", baud=9600,
                 timeout_per_denom=10.0, reconnect_attempts=3, reconnect_delay=2.0):
        """
        breakdown = {denom: qty}
        """
        super().__init__()
        self.breakdown = breakdown.copy()
        self.handler = CoinHandlerSerial(required_fee=0, port=serial_port, baud=baud, reconnect=False)
        self._running = True
        self.timeout = timeout_per_denom
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay

        # Synchronization for waiting
        self._done_event = threading.Event()
        self._expected = None

        # Register callbacks
        self.handler.add_dispense_callback(self._emit_dispense_ack)
        self.handler.add_dispense_done_callback(self._on_dispense_done)
        self.handler.add_error_callback(self._emit_dispense_error)

    def _emit_dispense_ack(self, denom, qty):
        self.dispenseAck.emit(denom, qty)

    def _on_dispense_done(self, denom, qty):
        self.dispenseDone.emit(denom, qty)
        if self._expected and (denom, qty) == self._expected:
            self._done_event.set()

    def _emit_dispense_error(self, msg):
        self.dispenseError.emit(msg)
        self._done_event.set()

    def run(self):
        try:
            # --- Try to open port with retries ---
            connected = False
            for attempt in range(self.reconnect_attempts):
                if self.handler.open():
                    connected = True
                    break
                else:
                    print(f"[CoinDispenserWorker] Serial open failed (attempt {attempt+1}/{self.reconnect_attempts})")
                    time.sleep(self.reconnect_delay)

            if not connected:
                self.dispenseError.emit("Failed to connect to coin dispenser serial port.")
                return

            # start reader thread
            if not getattr(self.handler, "_reader_thread", None) or not self.handler._reader_thread.is_alive():
                self.handler._reader_running = True
                self.handler._reader_thread = threading.Thread(target=self.handler._reader_loop, daemon=True)
                self.handler._reader_thread.start()

            # --- Sequentially dispense ---
            for denom, qty in self.breakdown.items():
                if not self._running:
                    break

                self._expected = (denom, qty)
                self._done_event.clear()

                self.handler.dispense(denom, qty)

                if not self._done_event.wait(timeout=self.timeout):
                    err_msg = f"Timeout waiting for DISPENSE_DONE for ₱{denom} x{qty}"
                    self.dispenseError.emit(err_msg)
                    break

                time.sleep(0.2)  # small delay between commands
            self.finished.emit()
        except Exception as e:
            self.dispenseError.emit(f"Worker exception: {e}")
        finally:
            self._running = False
            self.handler._reader_running = False
            self.handler.close()
            

    def stop(self):
        print("[CoinDispenserWorker] Stopping...")
        self._running = False
        self.handler._reader_running = False
        self.handler.close()
        self.quit()
        self.wait()