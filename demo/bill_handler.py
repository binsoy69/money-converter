class BillHandler:
    def __init__(self, selected_bill):
        self.required_bill = selected_bill

    def verify_bill(self):
        """
        Simulate bill verification.
        Returns:
            (success: bool)
        """
        raw = input("Insert bill (20/50/100/200/500/1000) or 'bad': ").strip().lower()
        inserted_bill = int(raw)
        if raw in ("20","50","100","200","500","1000"):
            success = (self.required_bill is None) or (inserted_bill == int(self.required_bill))
            return success, raw
        elif raw in ("bad","fake"):
            return False, "0"
        else:
            print("Invalid input. Try again.")

        print(f"[BillHandler] Verification result: success={success}, amount_expected={self.required_bill}, amount_inserted={raw}")
        return success, raw


import json
import os

class BillStorage:
    STORAGE_FILE = "bill_storage.json"

    def __init__(self):
        # Initialize with default values if no file exists
        if not os.path.exists(self.STORAGE_FILE):
            self.data = {
                20: 30,
                50: 30,
                100: 30,
                200: 30,
                500: 30,
                1000: 30
            }
            self._save()
        else:
            self._load()

    def _save(self):
        with open(self.STORAGE_FILE, "w") as f:
            json.dump(self.data, f)

    def _load(self):
        with open(self.STORAGE_FILE, "r") as f:
            self.data = json.load(f)

    # --- Getters & Setters ---
    def get_count(self, denom):
        return self.data.get(str(denom), 0)

    def set_count(self, denom, count):
        self.data[denom] = max(0, count)  # prevent negative
        self._save()

    def add(self, denom, amount=1):
        self.data[denom] = self.get_count(denom) + amount
        self._save()

    def deduct(self, denom, amount=1):
        if self.get_count(denom) >= amount:
            self.data[denom] -= amount
            self._save()
            return True
        return False

    def get_all(self):
        return dict(self.data)
