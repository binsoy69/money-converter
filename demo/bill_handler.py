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
