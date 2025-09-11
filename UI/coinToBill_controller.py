from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QMessageBox, QStackedWidget
from PyQt5.QtCore import QTime, QDate, QTimer
from PyQt5.QtGui import QColor
from PyQt5 import uic
import os

class CoinBillConverter(QStackedWidget):
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
    # Page Indexes
    PAGE_transFrame = 0
    PAGE_confirmationFrame = 1
    PAGE_insertFrame = 2
    PAGE_dashboardFrame = 3
    PAGE_cb_summary = 4
    PAGE_insufficient = 5
    PAGE_successfullyDispensed = 6
    PAGE_exclamation_notequal = 7

    def __init__(self, parent=None, navigate=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "CoinToBill.ui")
        uic.loadUi(ui_path, self)
        self.navigate_main = navigate
        self.setCurrentIndex(0)

        print("[CoinBillConverter] __init__ called - UI loaded, starting at index 0")

        # Buttons
        self.s_amount_buttons = [
            self.converter_trans_b2bBtn20, self.converter_trans_b2bBtn40,
            self.converter_trans_b2bBtn50, self.converter_trans_b2bBtn60,
            self.converter_trans_b2bBtn70, self.converter_trans_b2bBtn80,
            self.converter_trans_b2bBtn90, self.converter_trans_b2bBtn100,
            self.converter_trans_b2bBtn110, self.converter_trans_b2bBtn120,
            self.converter_trans_b2bBtn150, self.converter_trans_b2bBtn160,
            self.converter_trans_b2bBtn170, self.converter_trans_b2bBtn200
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
            self.cb_dashboard_proceed
        ], self.go_to_cb_summary)
        
        self.connect_buttons([
            self.cb_summary_back
        ], self.go_back_cb_dashboard)
        
        self.connect_buttons([
            self.cb_summary_proceed
        ], self.go_to_cb_dispense)
        
        self.connect_buttons([
            self.cb_insertCoins_proceed_2
        ], self.go_to_main_types)
        
        self.connect_buttons([
            self.cb_exit
        ], self.go_to_main)

        self.connect_buttons([
            self.cb_confirm_proceed_2
        ], self.c2b_s_transaction)

        self.amount_fee_mapping = {
            20: 3, 40: 3,
            50: 5, 60: 5, 70: 5,
            80: 8, 90: 8, 100: 8,
            110: 10, 120: 10, 150: 10,
            160: 15, 170: 15, 200: 15
        }

        self.button_amount_mapping = {
        self.converter_trans_b2bBtn20: 20,
        self.converter_trans_b2bBtn40: 40,
        self.converter_trans_b2bBtn50: 50,
        self.converter_trans_b2bBtn60: 60,
        self.converter_trans_b2bBtn70: 70,
        self.converter_trans_b2bBtn80: 80,
        self.converter_trans_b2bBtn90: 90,
        self.converter_trans_b2bBtn100: 100,
        self.converter_trans_b2bBtn110: 110,
        self.converter_trans_b2bBtn120: 120,
        self.converter_trans_b2bBtn150: 150,
        self.converter_trans_b2bBtn160: 160,
        self.converter_trans_b2bBtn170: 170,
        self.converter_trans_b2bBtn200: 200
        }

        # Coin labels mapping
        self.coin_labels = {
            1: self.label_coin_1,
            5: self.label_coin_5,
            10: self.label_coin_10,
            20: self.label_coin_20
        }

        self.total_amount_to_dispense = 0
        self.inserted_coin_amount = 0
        self.excess_coins = 0
        self.selected_amount = 0
        
        #CB Transaction / Proceed Button
        self.resetButtons()

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

        #to Del
        self.connect_buttons([
            self.converter_select_backBtn_11
        ], self.go_back_cb_insert)
        #to Del
        self.connect_buttons([
            self.converter_select_backBtn_10
        ], self.go_back_cb_confirm)

    # For connecting buttons to functions
    def connect_buttons(self, buttons, slot_function):
        for btn in buttons:
            btn.clicked.connect(lambda checked=False, b=btn: slot_function(b))

    def resetButtons(self):
        #CB Transaction / Proceed Button
        self.selected_button = None
        self.converter_service_proceed.setEnabled(False)

    #TIME AND DATE
    def update_time(self):
        current_time = QTime.currentTime().toString("h:mm AP")
        current_date = QDate.currentDate().toString("dddd | dd.MM.yyyy")
        self.main_timeLabel_9.setText(current_time)
        self.main_DateLabel_9.setText(current_date)
    
    # --- Timer UI ---
    #CB Update Progress bar
    def update_timer_ui(self):
        seconds_left = int(self.time_left / 10) if self.time_left > 0 else 0

        if self.time_left > 0:
            self.time_left -= 1
            self.cb_progressbar.setValue(self.time_left)

            # Calculate seconds remaining from progress steps
            self.cb_secondsLabel.setText(f"{seconds_left}s")
        else:
            self.timer.stop()
            self.cb_secondsLabel.setText("Time's up!")
            # Execute the callback if provided
            if self.on_timeout:
                self.on_timeout()

    #CB Start Timer
    def start_countdown(self, on_timeout=None):
            self.on_timeout = on_timeout

            self.time_left = self.progress_steps
            self.cb_progressbar.setValue(self.progress_steps)
            self.cb_secondsLabel.setText(f"{self.timer_duration}s")
            self.timer.start(100)  # 100 ms for smoother progress
            print("[CoinBillConverter] start_countdown - Countdown started")

    #CB Progress Bar Load
    def setup_progressbar(self):
        self.timer_duration = 10  # seconds
        self.progress_steps = self.timer_duration * 10  # 10 steps per second (100ms)
        self.time_left = self.progress_steps

        self.cb_progressbar.setMaximum(self.progress_steps)
        self.cb_progressbar.setValue(self.progress_steps)
        self.cb_secondsLabel.setText(f"{self.timer_duration}s")

    # for stopping the timer when nagivating to another page
    def stop_countdown(self):
        if self.timer.isActive():
            self.timer.stop()
            print("[CoinBillConverter] stop_countdown called - Timer manually stopped")

    # -- Navigation Methods --
    def navigate(self, index):
        self.setCurrentIndex(index)

    def go_to_main(self, _=None):
        if self.navigate_main:
            self.navigate_main(0)
        print("[CoinBillConverter] go_to_main - Navigated to Main index 0")

    def go_to_main_types(self, _=None):
        if self.navigate_main:
            self.navigate_main(1)
        print("[CoinBillConverter] go_to_main_types - Navigated to Main index 1")

    def go_back_to_service(self, _=None):
        if self.navigate_main:
            self.navigate_main(2)  # Navigate main window to index 2
            print("[CoinBillConverter] go_back_to_service - Navigated to Main index 2")

    def reset_to_start(self):
        self.reset_transaction_state()
        self.resetLabels()
        self.navigate(self.PAGE_transFrame)
        self.resetButtons()
        print("[CoinBillConverter] reset_to_start - Reset to index 0")

    def go_to_cb_confirm(self, _=None):
        self.navigate(self.PAGE_confirmationFrame)
        print("[CoinBillConverter] go_to_cb_confirm - Navigated to index 1")

    def go_to_cb_insert(self, _=None):
        self.navigate(self.PAGE_insertFrame)
        self.start_countdown(on_timeout=self.reset_to_start)
        print("[CoinBillConverter] go_to_cb_insert - Navigated to index 2 and started countdown")
    
    def go_to_cb_dashboard(self, _=None):
        self.stop_countdown()
        self.on_timeout = None  # Prevent auto-navigation
        self.navigate(self.PAGE_dashboardFrame)

        # Show selected amount and fee
        self.cb_dashboard_selected.setText(f"P{self.selected_amount}")
        self.cb_dashboard_tf.setText(f"P{self.selected_fee}")

        self.update_dashboard_checkboxes()
        print("[CoinBillConverter] go_to_cb_dashboard - Updated dashboard values")

        # Fetch total due from previous page
        total_due_text = self.cb_confirm_due.text()  # Example: "P23"

        # Set button text with Total Due and Bold Amount
        self.cb_insert_due.setText(f'Total Due: {total_due_text}')  
        print("[CoinBillConverter] go_to_cb_insert - Insert screen prepared")
    
    def go_to_cb_summary(self, _=None):
        self.cb_summary_transactionType.setText(self.label_140.text())
        self.cb_summary_serviceType.setText(self.label_141.text())
        self.cb_summary_totalMoney.setText(self.cb_dashboard_selected.text())
        self.cb_summary_transactionFee.setText(self.cb_dashboard_tf.text())
        self.cb_summary_moneyDispense.setText(self.cb_dashboard_selected.text())

        # Denomination = collect all checked checkboxes
        denominations = []
        checkbox_mapping = {
            self.cb_dashboard_20: "20",
            self.cb_dashboard_50: "50",
            self.cb_dashboard_100: "100",
            self.cb_dashboard_200: "200"
        }
        for checkbox, label in checkbox_mapping.items():
            if checkbox.isChecked():
                denominations.append(label)

        # Display as comma-separated (or customize formatting)
        self.cb_summary_denomination.setText(", ".join(denominations) if denominations else "None")

        # Finally, navigate to summary tab
        self.navigate(self.PAGE_cb_summary)

        print(f"[CoinBillConverter] go_to_cb_summary - Denominations: {denominations}")
    
    def go_to_cb_dispense(self, _=None):
        self.navigate(self.PAGE_successfullyDispensed)
        print("[CoinBillConverter] go_to_cb_dispense - Navigated to index 6")

    def go_back_cb_dashboard(self, _=None):
        self.navigate(self.PAGE_dashboardFrame)
        print("[CoinBillConverter] go_back_cb_dashboard - Navigated to index 3")
    
    def go_back_to_trans(self, _=None):
        self.navigate(self.PAGE_transFrame)
        print("[CoinBillConverter] go_back_to_trans - Navigated to index 0")
    
    def c2b_s_transaction(self, _=None):
        self.navigate(self.PAGE_transFrame)
        print("[CoinBillConverter] c2b_s_transaction - Navigated to Main index 3")

    def go_back_to_types(self, _=None):
        self.navigate(1)
        print("[CoinBillConverter] go_back_to_types - Navigated to Main index 1")
    # --- END NAVIGATION ---

    # --- Helper functions ---
    # C2B Specific_Amount_Transaction / Styles
    def reset_transaction_state(self):
        self.selected_button = None
        self.selected_amount = 0
        self.selected_fee = 0
        self.converter_service_proceed.setEnabled(False)
        for btn in self.s_amount_buttons:
            btn.setStyleSheet(self.NORMAL_STYLE)
        print("[CoinBillConverter] reset_transaction_state - Transaction state reset")
    
    def resetLabels(self):
        self.cb_current_count.setText("P0")
        for denom in self.coin_labels.keys():
            self.coin_labels[denom].setText("0")

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
        self.cb_confirm_due.setText(f"P{total_due}")

        print(f"[CoinBillConverter] select_s_amount_button - Amount: {amount}, Fee: {fee}, Total: {total_due}")

    def convert(self, _=None):
        pass  # Conversion logic
    
    #CB Dashboard Checkboxes
    def update_dashboard_checkboxes(self):
        # Get displayed selected amount (remove "P" prefix)
        selected_text = self.cb_dashboard_selected.text().replace("P", "")
        try:
            selected_amount = int(selected_text)
        except ValueError:
            selected_amount = 0  # Default to 0 if invalid display

        # Map your checkboxes to their respective amounts
        checkbox_mapping = {
            self.cb_dashboard_20: 20,
            self.cb_dashboard_50: 50,
            self.cb_dashboard_100: 100,
            self.cb_dashboard_200: 200
        }

        # Loop through and disable or enable checkboxes
        for checkbox, amount in checkbox_mapping.items():
            if amount > selected_amount:
                checkbox.setEnabled(False)
            else:
                checkbox.setEnabled(True)
        
        print(f"[CoinBillConverter] update_dashboard_checkboxes - Selected amount: {selected_amount}")

    
    #T0 Del
    def go_back_cb_insert(self, _=None):
        self.navigate(2)
        print("[CoinBillConverter] go_back_cb_insert - Navigated to index 2")

    #T0 Del
    def go_back_cb_confirm(self, _=None):
        self.navigate(1)
        print("[CoinBillConverter] go_back_cb_confirm - Navigated to index 1")

