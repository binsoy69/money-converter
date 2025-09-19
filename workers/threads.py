# threads.py
from PyQt5.QtCore import QThread, pyqtSignal

# from demo.bill_handler import BillHandler
# from demo.coin_handler import CoinHandler
from coin_handler.python.coin_handler_serial import * 
from bill_handler.python.pi_bill_handler import *
import traceback

class BillAcceptorWorker(QThread):
    bill_result = pyqtSignal(bool, int)
    finished = pyqtSignal()

    def __init__(self, required_denom: int, handler: PiBillHandler):
        super().__init__()
        self.required_denom = required_denom
        self.handler = handler  # reuse controller’s handler

    def run(self):
        try:
            accepted, denom, msg = self.handler.accept_bill(self.required_denom)
            if accepted:
                self.bill_result.emit(True, denom or self.required_denom)
            else:
                print(msg)
                self.bill_result.emit(False, denom or 0)
        except Exception as e:
            print("[BillAcceptorWorker] Exception:", e)
            traceback.print_exc()
            self.bill_result.emit(False, 0)
        finally:
            self.finished.emit()  # no cleanup, since handler persists


    def stop(self):
        self._running = False


class BillDispenserWorker(QThread):
    dispenseAck = pyqtSignal(int, int)   # denom, qty
    dispenseDone = pyqtSignal(int, int)
    dispenseError = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, breakdown: dict, handler: Optional[PiBillHandler] = None, storage: Optional[BillStorage] = None, dispense_time_ms: int = 1500):
        super().__init__()
        self.breakdown = breakdown.copy()
        self.handler = handler or PiBillHandler()
        self.storage = storage or BillStorage()
        self.dispense_time_ms = dispense_time_ms
        self._running = True

    def run(self):
        # Reserve storage first
        ok = self.storage.reserve_bulk(self.breakdown)
        if not ok:
            self.dispenseError.emit("insufficient_storage")
            self.finished.emit()
            return

        try:
            for denom, qty in self.breakdown.items():
                if qty <= 0:
                    continue
                self.dispenseAck.emit(denom, qty)
                ok_disp, msg = self.handler.dispense_bill(denom, qty, self.dispense_time_ms)
                if not ok_disp:
                    # rollback previous denoms
                    for d2, q2 in self.breakdown.items():
                        if d2 == denom:
                            break
                        self.storage.rollback_add(d2, q2)
                    # also restore current denom
                    self.storage.rollback_add(denom, qty)
                    self.dispenseError.emit(f"motor_failed:{msg}")
                    self.finished.emit()
                    return
                self.dispenseDone.emit(denom, qty)
            self.finished.emit()
        except Exception as e:
            traceback.print_exc()
            # rollback whole breakdown
            for d, q in self.breakdown.items():
                self.storage.rollback_add(d, q)
            self.dispenseError.emit(str(e))
            self.finished.emit()

    def stop(self):
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