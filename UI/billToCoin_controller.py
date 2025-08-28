from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QMessageBox, QStackedWidget
from PyQt5.QtCore import QTime, QDate, QTimer
from PyQt5.QtGui import QColor
from PyQt5 import uic
import os

from PyQt5.QtCore import QThread, pyqtSignal

# Worker thread for handling bill verification
class BillHandlerWorker(QThread):
    billProcessed = pyqtSignal(bool, int)  # success, amount

    def __init__(self, bill_handler):
        super().__init__()
        self.bill_handler = bill_handler
        self._running = True

    def run(self):
        """Run continuously until stopped."""
        while self._running:
            success, amount = self.bill_handler.verify_bill()
            self.billProcessed.emit(success, amount)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()


class BillCoinConverter(QStackedWidget):
    CLICKED_STYLE = """
        QToolButton {
            background-color: #F56600;
            color: white;
            border-radius: 15px;
            padding-top: 15px;
            padding-bottom: 20px;
        }
    """

    NORMAL_STYLE = """
        QToolButton {
            background-color: transparent;
            color: #ff8731;
            border: 2px solid #ff8731;
            border-radius: 15px;
            padding: 20px;
            padding-top: 10px;
            text-align: center;
        }

        QToolButton:hover {
            background-color: #FFC499;
            border: 2px solid #FFC499;
        }
    """

    def __init__(self, parent=None, navigate=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "BillToCoin.ui")
        uic.loadUi(ui_path, self)
        self.navigate_main = navigate
        self.setCurrentIndex(0)

        print("[BillCoinConverter] __init__ called - UI loaded, starting at index 0")

        # Buttons
        self.s_amount_buttons = [
            self.converter_trans_b2cBtn20, self.converter_trans_b2cBtn50, self.converter_trans_b2cBtn100, self.converter_trans_b2cBtn200
        ]

        # Setup
        self.connect_buttons(self.s_amount_buttons, self.select_s_amount_button)
        self.connect_buttons([
            self.converter_select_backBtn
        ], self.go_back_to_service)
        self.connect_buttons([
            self.converter_service_proceed
        ], self.go_to_cb_confirm)
        self.connect_buttons([
            self.cb_confirm_backBtn
        ], self.go_back_to_trans)
        self.connect_buttons([
            self.cb_confirm_proceed
        ], self.go_to_cb_insert)
        self.connect_buttons([
            self.cb_insert_proceed
        ], self.go_to_cb_dashboard)
        self.connect_buttons([
            self.cb_insertCoins_proceed
        ], self.go_to_cb_insertcoins)
        self.connect_buttons([
            self.cb_insert_proceed_3
        ], self.go_to_cb_dashboard2)
        self.connect_buttons([
            self.cb_confirm_deduct
        ], self.go_to_cb_deduct)
        self.connect_buttons([
            self.cb_dashboard_proceed
        ], self.go_to_cb_summary)
        self.connect_buttons([
            self.cb_summary_back
        ], self.go_back_cb_db)
        self.connect_buttons([
            self.cb_summary_proceed
        ], self.go_to_cb_dispnese)
        self.connect_buttons([
            self.cb_insertCoins_proceed_2
        ], self.go_to_main_types)
        self.connect_buttons([
            self.cb_exit
        ], self.go_to_main)


        #to Del
        self.connect_buttons([
            self.converter_select_backBtn_11
        ], self.go_back_cb_insert)
        #to Del
        self.connect_buttons([
            self.converter_select_backBtn_10
        ], self.go_back_cb_confirm)

        self.amount_fee_mapping = {
            20: 3, 40: 3,
            50: 5, 60: 5, 70: 5,
            80: 8, 90: 8, 100: 8,
            110: 10, 120: 10, 150: 10,
            160: 15, 170: 15, 200: 15
        }

        self.button_amount_mapping = {
        self.converter_trans_b2cBtn20: 20,
        self.converter_trans_b2cBtn50: 50,
        self.converter_trans_b2cBtn100: 100,
        self.converter_trans_b2cBtn200: 200
        }

        #CB Transaction / Proceed Button
        self.selected_button = None
        self.converter_service_proceed.setEnabled(False)

        #CB Insert Coins / Progression Bar
        self.timer_duration = 0  # seconds
        self.time_left = self.timer_duration

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer_ui)

        self.setup_progressbar()

        # Time updates
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)

    #for insert coins
    def reset_cb_current_count(self):
        self.bc_current_count_coins.setText("0")
        print("[BillCoinConverter] reset_cb_current_count called - set to 0")

    def update_cb_current_count(self, count):
        self.bc_current_count_coins.setText(str(count))
        print(f"[BillCoinConverter] update_cb_current_count called - updated to {count}")

    #for insert bill
    def reset_cb_current_count(self):
        self.bc_current_count_bill.setText("0")
        print("[BillCoinConverter] reset_cb_current_count called - set to 0")

    def update_cb_current_count(self, count):
        self.bc_current_count_bill.setText(str(count))
        print(f"[BillCoinConverter] update_cb_current_count called - updated to {count}")
        
    def update_dashboard_checkboxes(self):
        # Get displayed selected amount from the label only
        selected_text = self.cb_dashboard_selected.text().replace("P", "").strip()
        try:
            selected_amount = int(selected_text)
        except ValueError:
            selected_amount = 0  # Default if label is empty or invalid

        # Map checkboxes to amounts
        checkbox_mapping = {
            self.cb_dashboard_1: 1,
            self.cb_dashboard_5: 5,
            self.cb_dashboard_10: 10,
            self.cb_dashboard_20: 20
        }

        # Enable only if amount <= what’s shown in the label
        for checkbox, amount in checkbox_mapping.items():
            state = (amount <= selected_amount)
            checkbox.setEnabled(state)

        print(f"[CoinBillConverter] update_dashboard_checkboxes - Selected amount: {selected_amount}")


    #CB Update Progress bar
    def update_timer_ui(self):
        seconds_left = int(self.time_left / 10) if self.time_left > 0 else 0

        if self.time_left > 0:
            self.time_left -= 1
            self.cb_progressbar.setValue(self.time_left)
            self.cb_progressbar_2.setValue(self.time_left)

            # Calculate seconds remaining from progress steps
            self.cb_secondsLabel.setText(f"{seconds_left}s")
            self.cb_secondsLabel_2.setText(f"{seconds_left}s")
        else:
            self.timer.stop()
            self.cb_secondsLabel.setText("Time's up!")
            self.cb_secondsLabel_2.setText(f"{seconds_left}s")
            print("[BillCoinConverter] update_timer_ui called - Timer ended")
            # Execute the callback if provided
            if self.on_timeout:
                self.on_timeout()

            

    #CB Start Timer
    def start_countdown(self, on_timeout=None):
            self.on_timeout = on_timeout  # Store the callback

            self.time_left = self.progress_steps
            self.cb_progressbar.setValue(self.progress_steps)
            self.cb_progressbar_2.setValue(self.progress_steps)
            self.cb_secondsLabel.setText(f"{self.timer_duration}s")
            self.cb_secondsLabel_2.setText(f"{self.timer_duration}s")
            self.timer.start(100)  # 100 ms for smoother progress
            print("[BillCoinConverter] start_countdown called - Timer started")

    #CB Progress Bar Load
    def setup_progressbar(self):
        self.timer_duration = 10  # seconds
        self.progress_steps = self.timer_duration * 10  # 10 steps per second (100ms)
        self.time_left = self.progress_steps

        self.cb_progressbar.setMaximum(self.progress_steps)
        self.cb_progressbar.setValue(self.progress_steps)
        self.cb_progressbar_2.setMaximum(self.progress_steps)
        self.cb_progressbar_2.setValue(self.progress_steps)
        self.cb_secondsLabel.setText(f"{self.timer_duration}s")
        self.cb_secondsLabel_2.setText(f"{self.timer_duration}s")

    # for stopping the timer when nagivating to another page
    def stop_countdown(self):
        if self.timer.isActive():
            self.timer.stop()
            print("[BillCoinConverter] stop_countdown called - Timer manually stopped")


    def connect_buttons(self, buttons, slot_function):
        for btn in buttons:
            btn.clicked.connect(lambda checked=False, b=btn: slot_function(b))

    def apply_shadow(self, buttons):
        for btn in buttons:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 160))
            btn.setGraphicsEffect(shadow)

    # C2B Specific_Amount_Transaction / Styles
    def select_s_amount_button(self, selected_button):
        self.selected_button = selected_button
        self.converter_service_proceed.setEnabled(True)
        for btn in self.s_amount_buttons:
            btn.setStyleSheet(self.CLICKED_STYLE if btn == selected_button else self.NORMAL_STYLE)

        # Logic to display amounts and fees
        amount = self.button_amount_mapping.get(selected_button, 0)
        fee = self.amount_fee_mapping.get(amount, 0)
        total_due = amount + fee

        # Save amount and fee for later use
        self.selected_amount = amount
        self.selected_fee = fee

        self.cb_confirm_amount.setText(f"P{amount}")
        self.cb_confirm_trans.setText(f"P{fee}")
        self.cb_confirm_trans_2.setText(f"P{fee}")
        self.cb_confirm_due.setText(f"P{total_due}")

    def convert(self, _=None):
        pass  # Conversion logic

    #NAVIGATIONS

    def go_to_main(self, _=None):
        if self.navigate_main:
            self.navigate_main(0)
        print("[BillCoinConverter] go_to_main called - navigating main index 0")

    def go_to_main_types(self, _=None):
        if self.navigate_main:
            self.navigate_main(1)
        print("[BillCoinConverter] go_to_main_types called - navigating main index 1")
            
    def reset_to_start(self):
        self.setCurrentIndex(0)
        print("[BillCoinConverter] reset_to_start called - reset to index 0")

    def go_to_cb_dispnese(self, _=None):
        self.navigate(9)
        print("[BillCoinConverter] go_to_cb_dispnese called - navigating main index 9")

    def go_back_cb_db(self, _=None):
        self.navigate(3)
        print("[BillCoinConverter] go_back_cb_db called - navigating index 3")

    def go_to_cb_summary(self, _=None):
        self.cb_summary_transactionType.setText(self.label_116.text())
        self.cb_summary_serviceType.setText(self.label_117.text())
        self.cb_summary_totalMoney.setText(self.cb_dashboard_selected.text())
        self.cb_summary_transactionFee.setText(self.cb_dashboard_tf.text())
        self.cb_summary_moneyDispense.setText(self.cb_dashboard_selected.text())

        # Denomination = collect all checked checkboxes
        denominations = []
        checkbox_mapping = {
            self.cb_dashboard_1: "1",
            self.cb_dashboard_5: "5",
            self.cb_dashboard_10: "10",
            self.cb_dashboard_20: "20"
        }
        for checkbox, label in checkbox_mapping.items():
            if checkbox.isChecked():
                denominations.append(label)

        # Display as comma-separated (or customize formatting)
        self.cb_summary_denomination.setText(", ".join(denominations) if denominations else "None")

        # Finally, navigate to summary tab
        self.navigate(8)

        print(f"[BillCoinConverter] go_to_cb_summary - Denominations: {denominations}")


    def go_to_cb_deduct(self, _=None):
            # Remove "P" and convert to float
            amount_text = self.cb_confirm_amount.text().replace("P", "")
            fee_text = self.cb_confirm_trans.text().replace("P", "")

            amount = int(amount_text)
            fee = int(fee_text)

            # Perform deduction
            total = amount - fee

            # Update dashboard (add "P" for consistency)
            self.cb_dashboard_selected.setText(f"P{total}")

            # Navigate to page 3
            self.navigate(3)

            self.update_dashboard_checkboxes()

            print("[BillCoinConverter] go_to_cb_deduct() called - index 3")


    def go_to_cb_insertcoins(self, _=None):
        self.navigate(4)
        self.start_countdown(on_timeout=self.go_to_cb_dashboard)
        print("[BillCoinConverter] go_to_cb_insertcoins called - navigating index 4")

    def navigate(self, index):
        self.setCurrentIndex(index)
    
    #T0 Del
    def go_back_cb_insert(self, _=None):
        self.navigate(2)

    #T0 Del
    def go_back_cb_confirm(self, _=None):
        self.navigate(1)

    def go_to_cb_dashboard2(self, _=None):
        self.stop_countdown()
        self.on_timeout = None  # Prevent auto-navigation
        self.navigate(3)
        print("[BillCoinConverter] go_to_cb_dashboard2 called - navigating index 3")

    def go_to_cb_dashboard(self, _=None):
        self.stop_countdown()
        self.on_timeout = None  # Prevent auto-navigation

        self.navigate(7)

        # Show selected amount and fee
        self.cb_dashboard_selected.setText(f"P{self.selected_amount}")
        self.cb_dashboard_tf.setText(f"P{self.selected_fee}")

        print("[BillCoinConverter] go_to_cb_dashboard - Updated dashboard values")


    def go_to_cb_insert(self, _=None):
        self.navigate(2)
        self.start_countdown(on_timeout=self.reset_to_start)

        # Fetch total due from previous page
        total_due_text = self.cb_confirm_amount.text()  # Example: "P23"
        total_due_text2 = self.cb_confirm_trans.text()  # Example: "P23"

        # Set button text with Total Due and Bold Amount
        self.cb_insert_due.setText(f'Bill to Insert: {total_due_text}')
        self.cb_insert_due_2.setText(f'Total Due: {total_due_text2}')   

        print("[BillCoinConverter] go_to_cb_insert - Insert screen prepared")

    def go_back_to_trans(self, _=None):
        self.navigate(0)
        print("[BillCoinConverter] go_back_to_trans called - navigating index 0")

    def go_to_cb_confirm(self, _=None):
        self.navigate(1)
        print("[BillCoinConverter] go_to_cb_confirm called - navigating index 1")

    def go_back_to_service(self, _=None):
        if self.navigate_main:
            self.navigate_main(2)  # Navigate main window to index 2
        print("[BillCoinConverter] go_back_to_service called - navigating main index 2")
    
    def c2b_s_transaction(self, _=None):
        self.navigate(3)
        print("[BillCoinConverter] c2b_s_transaction called - navigating index 3")

    def go_back_to_types(self, _=None):
        self.navigate(1)
        print("[BillCoinConverter] go_back_to_types called - navigating index 1")

    #TIME AND DATE
    def update_time(self):
        current_time = QTime.currentTime().toString("h:mm AP")
        current_date = QDate.currentDate().toString("dddd | dd.MM.yyyy")
        self.main_timeLabel_9.setText(current_time)
        self.main_DateLabel_9.setText(current_date)

