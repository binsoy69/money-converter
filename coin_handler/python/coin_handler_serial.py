# coin_handler_serial.py
import serial
import threading
import time
import traceback
from typing import Callable
from .coin_storage import CoinStorage

class CoinHandlerSerial:
    def __init__(self):
        self.port = "/dev/ttyACM0"
        self.baud = 9600
        self.reconnect = True

        self.ser = None
        self._reader_thread = None
        self._running = False
        self._reader_running = False
        

        # session counts (per session / insertion)
        self.session_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        self.total_value = 0

        self._callbacks = []  # callbacks: fn(denom, count_for_denom, total_value)
        self._reached_callbacks = []  # callbacks for when required fee reached: fn(total_value)
        self._dispense_callbacks = []      # fn(denom, qty)
        self._dispense_done_callbacks = [] # fn(denom, qty)
        self._error_callbacks = []         # fn(msg)
        self._reached_emitted = False
        self._lock = threading.Lock()

        # coin storage (persisted)
        self.storage = CoinStorage()  # will persist to JSON
        self._reconnect_wait = 1.0  # start backoff

    def add_callback(self, fn: Callable[[int, int, int], None]):
        self._callbacks.append(fn)

    def add_reached_callback(self, fn):
        """Register a callback called once when required fee is reached. fn(total_value)"""
        self._reached_callbacks.append(fn)

    def add_dispense_callback(self, fn):
        self._dispense_callbacks.append(fn)

    def add_dispense_done_callback(self, fn):
        self._dispense_done_callbacks.append(fn)

    def add_error_callback(self, fn):
        self._error_callbacks.append(fn)

    # ----- Serial open/close/reconnect -----
    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            # give Arduino time to reset on open
            time.sleep(2.0)
            print(f"[CoinHandlerSerial] Opened {self.port}@{self.baud}")
            self._reconnect_wait = 1.0
            return True
        except Exception as e:
            print("[CoinHandlerSerial] open error:", e)
            self.ser = None
            return False

    def close(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.ser = None
        except Exception as e:
            print("[CoinHandlerSerial] close error:", e)

    # ----- Control functions -----
    def start_accepting(self, required_amount):
        """Open port and start reader thread; send ENABLE_COIN."""
        self._running = True

        # reset reached flag for a fresh session
        self._reached_emitted = False

        if not self.open() and self.reconnect:
            # start a background thread to attempt reconnection
            threading.Thread(target=self._reconnect_loop, daemon=True).start()
        else:
            # send enable immediately if serial is open
            self._send_command("ENABLE_COIN")
        # start reader
        if not self._reader_thread or not self._reader_thread.is_alive():
            self._reader_running = True
            self._reader_thread = threading.Thread(target=self._reader_loop, args=(required_amount,), daemon=True)
            self._reader_thread.start()

    def stop_accepting(self):
        """Send DISABLE_COIN and stop reader loop."""
        # Send disable, but keep thread to listen for ACK if desired
        self._send_command("DISABLE_COIN")
        self._running = False
        self._reader_running = False
        # close serial after small delay to allow ACK
        time.sleep(0.2)
        self.close()

    def dispense(self, denom: int, qty: int = 1):
        # Ensure serial is open
        if not self.ser or not self.ser.is_open:
            if not self.open():
                print("[CoinHandlerSerial] dispense failed: port not open")
                return
            # start reader if not running
            if not self._reader_thread or not self._reader_thread.is_alive():
                self._reader_running = True
                self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
                self._reader_thread.start()

        cmd = f"DISPENSE:{denom}:{qty}"
        self._send_command(cmd)
        print(f"[DEBUG] dispense command sent: {cmd}")



    def simulate_coins(self, seq, interval=0.25):
        """Callbacks will be triggered but storage isn't changed here (we call storage in real handler).
           This helper helps testing UI without hardware.
        """
        for d in seq:
            self._handle_coin(denom=d)
            time.sleep(interval)

    # ----- internal utils -----
    def _send_command(self, cmd: str):
        try:
            if self.ser and self.ser.is_open:
                self.ser.write((cmd + "\n").encode("utf-8"))
                print("[RPi -> ARDUINO]", cmd)
            else:
                print("[CoinHandlerSerial] _send_command failed; serial not open:", cmd)
        except Exception as e:
            print("[CoinHandlerSerial] write error:", e)

    def _reconnect_loop(self):
        """Try to open serial repeatedly with backoff while _running is True."""
        while self._running:
            ok = self.open()
            if ok:
                # send enable when reconnected
                time.sleep(0.5)
                self._send_command("ENABLE_COIN")
                break
            else:
                print(f"[CoinHandlerSerial] reconnect failed, retrying in {self._reconnect_wait:.1f}s")
                time.sleep(self._reconnect_wait)
                self._reconnect_wait = min(self._reconnect_wait * 1.5, 10.0)

    def _reader_loop(self, required_amount=0):
        """Continuously read lines and parse them."""
        print("[CoinHandlerSerial] reader started")
        while self._reader_running:
            try:
                if not self.ser or not self.ser.is_open:
                    time.sleep(0.2)
                    continue

                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                print("[ARDUINO]", line)
                self._parse_line(line, required_amount)

            except Exception as e:
                if not self._reader_running:
                    break  # Exit gracefully if stopped
                print("[CoinHandlerSerial] reader exception:", e)
                traceback.print_exc()
                time.sleep(0.5)
        print("[CoinHandlerSerial] reader stopped")


    def _parse_line(self, line: str, required_amount=0):
        # Possible formats expected from Arduino:
        # COIN:<denom>
        # SORT_DONE:<denom>
        # ACK:ENABLE_COIN
        # ACK:DISPENSE:<denom>:<qty>
        # DISPENSE_DONE:<denom>:<qty>
        # ERR:<message>

        parts = line.split(":")
        tag = parts[0].upper()

        if tag == "COIN" and len(parts) >= 2:
            try:
                denom = int(parts[1])
                self._handle_coin(denom, required_amount)
            except Exception as e:
                print("[CoinHandlerSerial] malformed COIN line:", line, e)

        elif tag == "PULSE" and len(parts) >= 2:
            # Fallback support (if Arduino sends pulses instead of denom)
            try:
                pulses = int(parts[1])
                denom = self._map_pulses_to_denom(pulses)
                self._handle_coin(denom, required_amount)
            except Exception as e:
                print("[CoinHandlerSerial] malformed PULSE line:", line, e)

        elif tag == "ACK":
            if len(parts) >= 2 and parts[1].startswith("DISPENSE") and len(parts) >= 4:
                # ACK:DISPENSE:<denom>:<qty>
                try:
                    denom = int(parts[2])
                    qty = int(parts[3])
                    print(f"[CoinHandlerSerial] ACK -> DISPENSE {denom} x{qty}")
                    for cb in self._dispense_callbacks:
                        cb(denom, qty)
                except Exception as e:
                    print("[CoinHandlerSerial] bad ACK DISPENSE:", e)
            else:
                print("[CoinHandlerSerial] ACK ->", ":".join(parts[1:]))

        elif tag == "SORT_DONE" and len(parts) >= 2:
            print("[CoinHandlerSerial] SORT_DONE ->", parts[1])

        elif tag == "DISPENSE_DONE" and len(parts) >= 3:
            try:
                denom = int(parts[1])
                qty = int(parts[2])
                # Deduct from coin storage
                actual = self.storage.deduct(denom, qty)
                print(f"[CoinHandlerSerial] DISPENSE_DONE -> {denom} x{actual}")
                for cb in self._dispense_done_callbacks:
                    cb(denom, actual)
            except Exception as e:
                print("[CoinHandlerSerial] bad DISPENSE_DONE:", e)

        elif tag == "ERR":
            msg = ":".join(parts[1:])
            print("[CoinHandlerSerial] ERR from arduino:", msg)
            for cb in self._error_callbacks:
                cb(msg)

        else:
            # Unknown or debug message
            print("[CoinHandlerSerial] Unknown msg:", line)


    def _handle_coin(self, denom: int, required_amount=0):
        with self._lock:
            if denom not in self.session_counts:
                print("[CoinHandlerSerial] unsupported denom received:", denom)
                return

            # increment session counters and total
            self.session_counts[denom] += 1
            self.total_value += denom

            # Persist to coin storage (machine's stock increases when user inserts coin)
            new_storage_count = self.storage.add(denom, 1)

            # Notify callbacks (denom, count_for_denom_in_session, total_value)
            for cb in self._callbacks:
                try:
                    cb(denom, self.session_counts[denom], self.total_value)
                except Exception as e:
                    print("[CoinHandlerSerial] callback error:", e)

            if required_amount > 0 and self.total_value >= required_amount and not self._reached_emitted:
                self._reached_emitted = True
                print("[CoinHandlerSerial] required fee reached; sending DISABLE_COIN")

                # notify reached-callbacks (UI or worker can use this to proceed)
                for rcb in self._reached_callbacks:
                    try:
                        rcb(self.total_value)
                    except Exception as e:
                        print("[CoinHandlerSerial] reached-callback error:", e)

                # send disable command to arduino (handler will still listen for ACKs)
                self._send_command("DISABLE_COIN")
                # Keep running to catch ACKs and additional messages until controller stops the handler.

    def _map_pulses_to_denom(self, pulses):
        mapping = {1: 1, 5: 5, 10: 10, 20: 20}
        return mapping.get(pulses, 1)
