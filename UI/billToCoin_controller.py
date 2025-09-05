from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QMessageBox, QStackedWidget
from PyQt5.QtCore import QTime, QDate, QTimer
from PyQt5.QtGui import QColor
from PyQt5 import uic
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from workers.threads import * 

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

    # Page index constants
    PAGE_transFrame = 0
    PAGE_confirmationFrame = 1
    PAGE_insertBill = 2
    PAGE_dashboardFrame = 3
    PAGE_insertCoin = 4
    PAGE_insufficient = 5
    PAGE_exclamation_notequal = 6
    PAGE_transactionFee = 7
    PAGE_summary = 8
    PAGE_successfullyDispensed = 9

    def __init__(self, parent=None, navigate=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "BillToCoin.ui")
        uic.loadUi(ui_path, self)
        self.navigate_main = navigate
        self.setCurrentIndex(self.PAGE_transFrame)

        print("[BillCoinConverter] __init__ called - UI loaded, starting at index 0")

        # Buttons
        self.s_amount_buttons = [
            self.converter_trans_b2cBtn20, self.converter_trans_b2cBtn50, self.converter_trans_b2cBtn100, self.converter_trans_b2cBtn200
        ]

        # Connect Buttons
        self.connect_buttons(self.s_amount_buttons, self.select_s_amount_button)
        self.connect_buttons([
            self.converter_select_backBtn
        ], self.go_back_to_service)

        self.connect_buttons([
            self.converter_service_proceed
        ], self.go_to_cb_confirm)
        
        self.connect_buttons([
            self.cb_confirm_backBtn
        ], self.reset_to_start)
        
        self.connect_buttons([
            self.cb_confirm_proceed
        ], self.go_to_cb_insert_bill)
        
        self.connect_buttons([
            self.cb_exclamation_insertanother
        ], self.go_to_cb_insert_bill)

        self.connect_buttons([
            self.cb_exclamation_chooseanother
        ], self.reset_to_start)

        self.connect_buttons([
            self.cb_insert_proceed
        ], self.go_to_transFee)
        
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
        ], self.go_to_cb_dispense)
        
        self.connect_buttons([
            self.another_transaction
        ], self.go_to_main_types)
        
        self.connect_buttons([
            self.cb_exit
        ], self.go_to_main)

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

        # Coin labels mapping
        self.coin_labels = {
            1: self.label_coin_1,
            5: self.label_coin_5,
            10: self.label_coin_10,
            20: self.label_coin_20
        }
        

        self.total_amount_to_dispense = 0
        self.inserted_bill_amount = 0
        self.inserted_coin_amount = 0
        self.total_money_inserted = 0
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

    # for resetting buttons after transaction
    def resetButtons(self):
        # Reset selected amount and button
        self.selected_amount = 0
        self.selected_button = None
        self.selected_fee = 0
        self.converter_service_proceed.setEnabled(False)
        # Reset button styles
        for btn in self.s_amount_buttons:
            btn.setStyleSheet(self.NORMAL_STYLE)

    #TIME AND DATE
    def update_time(self):
        current_time = QTime.currentTime().toString("h:mm AP")
        current_date = QDate.currentDate().toString("dddd | dd.MM.yyyy")
        self.main_timeLabel_9.setText(current_time)
        self.main_DateLabel_9.setText(current_date)

    # --- Timer UI ---
    # Update Progress bar
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

    # Start Timer
    def start_countdown(self, on_timeout=None):
            self.on_timeout = on_timeout  # Store the callback

            self.time_left = self.progress_steps
            self.cb_progressbar.setValue(self.progress_steps)
            self.cb_progressbar_2.setValue(self.progress_steps)
            self.cb_secondsLabel.setText(f"{self.timer_duration}s")
            self.cb_secondsLabel_2.setText(f"{self.timer_duration}s")
            self.timer.start(100)  # 100 ms for smoother progress
            print("[BillCoinConverter] start_countdown called - Timer started")

    #Progress Bar Load
    def setup_progressbar(self):
        self.timer_duration = 60  # seconds
        self.progress_steps = self.timer_duration * 10  # 10 steps per second (100ms)
        self.time_left = self.progress_steps

        self.cb_progressbar.setMaximum(self.progress_steps)
        self.cb_progressbar.setValue(self.progress_steps)
        self.cb_progressbar_2.setMaximum(self.progress_steps)
        self.cb_progressbar_2.setValue(self.progress_steps)
        self.cb_secondsLabel.setText(f"{self.timer_duration}s")
        self.cb_secondsLabel_2.setText(f"{self.timer_duration}s")

    # For stopping the timer when nagivating to another page
    def stop_countdown(self):
        if self.timer.isActive():
            self.timer.stop()
            print("[BillCoinConverter] stop_countdown called - Timer manually stopped")

    # -- Navigation Methods --

    def go_to_main(self, _=None):
        if self.navigate_main:
            self.navigate_main(0)
        print("[BillCoinConverter] go_to_main called - navigating main index 0")

    def go_to_main_types(self, _=None):
        self.resetButtons()
        if self.navigate_main:
            self.navigate_main(1)
        print("[BillCoinConverter] go_to_main_types called - navigating main index 1 and reset selection")

    def go_back_to_service(self, _=None):
        if self.navigate_main:
            self.navigate_main(2)  # Navigate main window to index 2
        print("[BillCoinConverter] go_back_to_service called - navigating main index 2")

    def reset_to_start(self, _=None):
        self.reset_transaction_state()
        self.resetLabels()
        self.navigate(self.PAGE_transFrame)
        self.resetButtons()
        print("[BillCoinConverter] reset_to_start called - reset to index 0")

    def go_to_cb_confirm(self, _=None):
        self.navigate(self.PAGE_confirmationFrame)
        print("[BillCoinConverter] go_to_cb_confirm called - navigating index 1")

    def go_to_cb_insert_bill(self, _=None):
        self.resetLabels()
        self.navigate(self.PAGE_insertBill)
        self.start_countdown(on_timeout=self.reset_to_start)

        # Fetch total due from previous page
        total_due_amount = self.cb_confirm_amount.text()  # Example: "P23"
        total_due_fee = self.cb_confirm_trans.text()  # Example: "P23"

        # Set button text with Total Due and Bold Amount
        self.cb_insert_due.setText(f'Bill to Insert: {total_due_amount}')
        self.cb_insert_due_2.setText(f'Total Due: {total_due_fee}')   

        print("[BillCoinConverter] go_to_cb_insert - Insert screen prepared")
        print(f"[BillCoinConverter] User selected bill: {self.selected_amount}")

        # --- BillHandlerWorker integration ---
        self.handle_bill_insertion()

    def go_to_cb_deduct(self, _=None):
            # Remove "P" and convert to float
            amount_text = self.cb_confirm_amount.text().replace("P", "")
            fee_text = self.cb_confirm_trans.text().replace("P", "")

            amount = int(amount_text)
            fee = int(fee_text)

            # Perform deduction
            total = amount - fee
            self.total_amount_to_dispense = total

            # Update dashboard (add "P" for consistency)
            self.cb_dashboard_selected.setText(f"P{self.selected_amount}")

            # Navigate to page 3
            self.navigate(self.PAGE_dashboardFrame)

            self.update_dashboard_checkboxes()

            print("[BillCoinConverter] go_to_cb_deduct() called - index 3")

    def go_to_cb_insertcoins(self, _=None):
        self.resetLabels()
        self.navigate(self.PAGE_insertCoin)
        self.start_countdown(on_timeout=self.go_to_transFee)
        print("[BillCoinConverter] go_to_cb_insertcoins called - navigating index 4")
        self.handle_coin_insertion()
    
    def go_to_transFee(self, _=None):
        self.stop_countdown()
        self.on_timeout = None  # Prevent auto-navigation

        self.navigate(self.PAGE_transactionFee)

        # Show selected amount and fee
        self.cb_dashboard_selected.setText(f"P{self.total_amount_to_dispense}")
        self.cb_dashboard_tf.setText(f"P{self.selected_fee}")

        print("[BillCoinConverter] go_to_transFee - Updated dashboard values")

    def go_to_cb_dashboard2(self, _=None):
        self.stop_countdown()
        self.on_timeout = None  # Prevent auto-navigation

        # update total money to be dispensed
        self.total_amount_to_dispense = self.selected_amount + self.excess_coins
        self.cb_dashboard_selected.setText(f"P{self.selected_amount}")
        self.update_dashboard_checkboxes()

        self.navigate(self.PAGE_dashboardFrame)
        print("[BillCoinConverter] go_to_cb_dashboard2 called - navigating index 3")

    def go_to_cb_summary(self, _=None):
        self.cb_summary_transactionType.setText(self.label_116.text())
        self.cb_summary_serviceType.setText(self.label_117.text())
        self.cb_summary_totalMoney.setText(str(self.total_money_inserted))
        self.cb_summary_transactionFee.setText(self.cb_dashboard_tf.text())
        self.cb_summary_moneyDispense.setText(str(self.total_amount_to_dispense))

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
        self.navigate(self.PAGE_summary)

        print(f"[BillCoinConverter] go_to_cb_summary - Denominations: {denominations}")

    def go_back_cb_db(self, _=None):
        self.navigate(self.PAGE_dashboardFrame)
        print("[BillCoinConverter] go_back_cb_db called - navigating index 3")
    
    def go_to_cb_dispense(self, _=None):
        self.navigate(self.PAGE_successfullyDispensed)
        print("[BillCoinConverter] go_to_cb_dispense called - navigating main index 9")

    def navigate(self, index):
        self.setCurrentIndex(index)

    # --- END NAVIGATION ---

    # --- Helper functions ---
    def reset_transaction_state(self):
        """Reset all money-related state variables before a new transaction."""
        self.inserted_bill_amount = 0
        self.inserted_coin_amount = 0
        self.total_money_inserted = 0
        self.excess_coins = 0
        self.total_amount_to_dispense = 0

    def resetLabels(self):
        self.bc_current_count_bill.setText("P0")
        self.bc_current_count_coins.setText("P0")
        for denom in self.coin_labels.keys():
            self.coin_labels[denom].setText("0")

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

        # Clear (uncheck) all checkboxes first
        for checkbox in checkbox_mapping.keys():
            checkbox.setChecked(False)
        
        # Enable only if amount <= what’s shown in the label
        for checkbox, amount in checkbox_mapping.items():
            state = (amount <= selected_amount)

            # Special rule: if user inserted 20 bill, disable 20 coin
            if self.inserted_bill_amount == 20 and amount == 20:
                state = False

            checkbox.setEnabled(state)

        print(f"[CoinBillConverter] update_dashboard_checkboxes - Selected amount: {selected_amount}")

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
        print(f"[BillCoinConverter] User selected bill: {amount}")

    def convert(self, _=None):
        pass  # Conversion logic

    # -- Bill handling logic --- 
    def handle_bill_insertion(self):
        if hasattr(self, 'bill_handler_worker') and self.bill_handler_worker is not None:
            self.bill_handler_worker.stop()
            self.bill_handler_worker = None

        # Start BillHandlerWorker simulation
        self.bill_handler_worker = BillHandlerWorker()
        self.bill_handler_worker.bill_inserted.connect(self.on_bill_inserted)
        self.bill_handler_worker.finished.connect(self.on_bill_worker_finished)
        self.bill_handler_worker.start()
        print("[BillCoinConverter] BillHandlerWorker started for bill verification.")
     
    def on_bill_inserted(self, bill):
        expected_bill = str(self.selected_amount)  # expected bill from earlier selection
        self.bc_current_count_bill.setText(bill)
        print(f"[BillCoinConverter] Simulated bill inserted: {bill}, expected: {expected_bill}")

        if bill == expected_bill:
            print("[BillCoinConverter] Correct bill inserted.")
            self.inserted_bill_amount = int(bill)
            self.total_money_inserted = self.inserted_bill_amount + self.inserted_coin_amount
            print(f"[BillCoinConverter] Total money inserted updated: {self.total_money_inserted}")

            # after 2 seconds, proceed to transaction fee
            QTimer.singleShot(2000, lambda: self.go_to_transFee())
        else:
            print("[BillCoinConverter] Incorrect bill inserted.")
            self.stop_countdown()
            # after 2 seconds, go to error page
            QTimer.singleShot(2000, lambda: self.navigate(self.PAGE_exclamation_notequal))

    def on_bill_worker_finished(self):
        print("[BillCoinConverter] BillHandlerWorker finished.")

    # --- Coin handling logic ---

    def handle_coin_insertion(self):
        # stop previous worker if any
        if hasattr(self, 'coin_handler_worker') and self.coin_handler_worker is not None:
            self.coin_handler_worker.stop()
            self.coin_handler_worker = None

        # expected is TOTAL VALUE in pesos
        # billToCoin_controller.py
        self.coin_handler_worker = CoinHandlerWorker(required_fee=self.selected_fee)
        self.coin_handler_worker.coinInserted.connect(self.on_single_coin_inserted)
        self.coin_handler_worker.coinsProcessed.connect(self.on_coins_processed)

        # reset UI per-denomination labels and totals
        self.coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        for d in self.coin_labels:
            self.coin_labels[d].setText("0")
        self.bc_current_count_coins.setText("P0")

        self.coin_handler_worker.start()
        print("[BillCoinConverter] CoinHandlerWorker started for coin verification.")

    def on_single_coin_inserted(self, denomination, denom_count, total_value):
        # Update the specific denom label
        self.coin_counts[denomination] = denom_count
        self.coin_labels[denomination].setText(str(denom_count))

        # Show running TOTAL VALUE in pesos
        self.bc_current_count_coins.setText(f"P{total_value}")

        # Reset/extend the countdown on each coin
        self.start_countdown(on_timeout=self.go_to_transFee)

        print(f"[BillCoinConverter] Coin inserted: {denomination}, "
            f"count for denom: {denom_count}, total: {total_value}")

    def on_coins_processed(self, success, total_value):
        if hasattr(self, 'coin_handler_worker') and self.coin_handler_worker is not None:
            self.coin_handler_worker.stop()
            self.coin_handler_worker = None

        # Final coin total
        self.bc_current_count_coins.setText(f"P{total_value}")
        self.inserted_coin_amount = total_value
        self.total_money_inserted = self.inserted_bill_amount + self.inserted_coin_amount

        # Compute excess coins (can be positive or negative)
        self.excess_coins = self.inserted_coin_amount - self.selected_fee

        # Total amount to dispense = total inserted + excess
        self.total_amount_to_dispense = self.selected_amount + self.excess_coins

        print(f"[BillCoinConverter] on_coins_processed - coins={self.inserted_coin_amount}, "
            f"bill={self.inserted_bill_amount}, total={self.total_money_inserted}, "
            f"excess_coins={self.excess_coins}, to_dispense={self.total_amount_to_dispense}")

        # Always proceed regardless of success (even if < fee)
        QTimer.singleShot(1500, lambda: self.go_to_cb_dashboard2())


    # TO Del
    def go_back_cb_insert(self, _=None):
        self.navigate(2)

    # TO Del
    def go_back_cb_confirm(self, _=None):
        self.navigate(1)

