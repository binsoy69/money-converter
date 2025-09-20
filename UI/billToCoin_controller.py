from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QMessageBox, QStackedWidget
from PyQt5.QtCore import QTime, QDate, QTimer
from PyQt5.QtGui import QColor
from PyQt5 import uic
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from workers.threads import *
from demo.bill_to_coin_converter import *



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
    PAGE_dispensing = 10

    def __init__(self, parent=None, navigate=None, bill_handler=None, coin_handler=None):
        super().__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "BillToCoin.ui")
        uic.loadUi(ui_path, self)
        self.navigate_main = navigate
        self.setCurrentIndex(self.PAGE_transFrame)
        self.bill_handler = bill_handler
        self.coin_handler = coin_handler

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
        ], self.on_proceed_coin_pressed)
        
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

        self.connect_buttons([
            self.cb_confirm_proceed_2
        ], self.go_to_main)

        self.amount_fee_mapping = {
            20: 2,
            50: 3,
            100: 5,
            200: 7
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

        # Map checkboxes to denominations
        self.checkbox_mapping = {
            self.cb_dashboard_1: "1",
            self.cb_dashboard_5: "5",
            self.cb_dashboard_10: "10",
            self.cb_dashboard_20: "20"
        }

        
        self.total_amount_to_dispense = 0
        self.inserted_bill_amount = 0
        self.inserted_coin_amount = 0
        self.total_money_inserted = 0
        self.excess_coins = 0
        self.selected_amount = 0
        self.breakdown = {}

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
    def navigate(self, index):
        self.setCurrentIndex(index)
        
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
        total_due_amount = self.selected_amount
        total_due_fee = self.selected_fee

        # Set button text with Total Due and Bold Amount
        self.cb_insert_due.setText(f'Bill to Insert: {total_due_amount}')
        self.cb_insert_due_2.setText(f'Total Due: {total_due_fee}')   

        print("[BillCoinConverter] go_to_cb_insert - Insert screen prepared")
        print(f"[BillCoinConverter] User selected bill: {self.selected_amount}")

        # --- BillHandlerWorker integration ---
        self.handle_bill_insertion()

    def go_to_cb_deduct(self, _=None):
            # Perform deduction
            self.total_amount_to_dispense = self.selected_amount - self.selected_fee + self.excess_coins

            # Update dashboard (add "P" for consistency)
            self.cb_dashboard_selected.setText(f"P{self.selected_amount}")

            # Navigate to page 3
            self.update_dashboard_checkboxes()
            self.navigate(self.PAGE_dashboardFrame)
            print("[BillCoinConverter] go_to_cb_deduct() called - index 3")

    def go_to_cb_insertcoins(self, _=None):
        self.resetLabels()
        self.navigate(self.PAGE_insertCoin)
        print("[BillCoinConverter] go_to_cb_insertcoins called - navigating index 4")
        self.start_coin_insertion()
    
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
       
        for checkbox, label in self.checkbox_mapping.items():
            if checkbox.isChecked():
                denominations.append(label)

        # Display as comma-separated (or customize formatting)
        self.cb_summary_denomination.setText(", ".join(denominations) if denominations else "AUTO")

        # Finally, navigate to summary tab
        self.navigate(self.PAGE_summary)

        print(f"[BillCoinConverter] go_to_cb_summary - Denominations: {denominations}")

    def go_back_cb_db(self, _=None):
        self.navigate(self.PAGE_dashboardFrame)
        print("[BillCoinConverter] go_back_cb_db called - navigating index 3")
    
    def go_to_cb_dispense(self, _=None):
        if self.convert_bill_to_coin():
            self.navigate(self.PAGE_dispensing)

            # Create and start dispense worker
            self.dispense_worker = CoinDispenserWorker(handler=self.coin_handler, breakdown=self.breakdown)
            self.dispense_worker.dispenseAck.connect(self.on_dispense_ack)
            self.dispense_worker.dispenseDone.connect(self.on_dispense_done)
            self.dispense_worker.dispenseError.connect(self.on_dispense_error)
            self.dispense_worker.finished.connect(self.on_dispense_finished)
            self.dispense_worker.start()

            print("[BillCoinConverter] go_to_cb_dispense started dispense worker")
        else:
            print("[BillCoinConverter] Conversion failed")
            self.navigate(self.PAGE_insufficient)


    # --- END NAVIGATION ---

    #  --- HELPER FUNCTIONS --- 

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

    def reset_transaction_state(self):
        """Reset all money-related state variables before a new transaction."""
        self.inserted_bill_amount = 0
        self.inserted_coin_amount = 0
        self.total_money_inserted = 0
        self.excess_coins = 0
        self.total_amount_to_dispense = 0
        self._coins_finalized = False
        self.breakdown.clear()
        self.cb_insert_proceed_3.setEnabled(True)

        for cb in self.checkbox_mapping.keys():
            cb.setChecked(False)   # uncheck
            cb.setEnabled(True)    # re-enable

    def resetLabels(self):
        self.bc_current_count_bill.setText("P0")
        self.bc_current_count_coins.setText("P0")
        for denom in self.coin_labels.keys():
            self.coin_labels[denom].setText("0")

    def update_dashboard_checkboxes(self):
        # get selected amount
        selected_amount = self.selected_amount

        # Get latest storage state
        current_storage = self.coin_handler.storage.get_storage()

        for checkbox, amount in self.checkbox_mapping.items():
            # Rule 1: Enable only if denom <= selected amount
            amount = int(amount)
            allowed_by_amount = amount <= selected_amount

            # Rule 2: Enable only if storage >= 5
            allowed_by_storage = current_storage.get(amount, 0) >= 5

            if allowed_by_amount and allowed_by_storage:
                checkbox.setEnabled(True)
            else:
                checkbox.setEnabled(False)
                checkbox.setChecked(False)  # uncheck if disabled

        # Additional rule: If selected amount is exactly 20, disable 20-peso checkbox
        if selected_amount == 20:
            self.cb_dashboard_20.setEnabled(False)
            self.cb_dashboard_20.setChecked(False)
            print("[UI] Disabled 20-peso checkbox (selected amount = 20).")

        print(f"[BillCoinConverter] update_dashboard_checkboxes - "
              f"Selected amount: {selected_amount}, Storage: {current_storage}")

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

    def get_selected_denoms(self):
        checkbox_mapping = {
            self.cb_dashboard_1: 1,
            self.cb_dashboard_5: 5,
            self.cb_dashboard_10: 10,
            self.cb_dashboard_20: 20
        }
        return [amount for checkbox, amount in checkbox_mapping.items() if checkbox.isChecked()]
    
    def convert_bill_to_coin(self, _=None):
        """
        Wrapper that calls the coin_converter module.
        Uses self.total_amount_to_dispense and user-selected checkboxes.
        """
        amount = self.total_amount_to_dispense
        if amount <= 0:
            print("[Convert] Nothing to dispense.")
            return False

        # Get selected denominations from checkboxes
        selected_denoms = self.get_selected_denoms()
        if not selected_denoms:
            selected_denoms = [20, 10, 5, 1]  # auto mode

        # Use global coin_storage (already in your class)
        storage = self.coin_handler.storage.get_storage()

        # --- Simulation ---
        self.breakdown = convert_bill_to_coin(amount, selected_denoms, storage)

        if not self.breakdown:
            print("[Convert] ERROR: Cannot dispense with available coins.")
            return False

        return True

    # -- Bill handling logic --- 
    def handle_bill_insertion(self):
        self.bill_acceptor_worker = BillAcceptorWorker(
            self.selected_amount,
            handler=self.bill_handler
        )
        self.bill_acceptor_worker.bill_result.connect(self.on_bill_result)
        self.bill_acceptor_worker.finished.connect(self.on_bill_finished)
        self.bill_acceptor_worker.start()


    def on_bill_result(self, success, denomination):
        self.bc_current_count_bill.setText(f"P{denomination}")
        if success:
            self.inserted_bill_amount = int(denomination)
            self.total_money_inserted += self.inserted_bill_amount
            print(f"[BillCoinConverter] Bill accepted: {denomination}, "
                f"total_money_inserted={self.total_money_inserted}")
            QTimer.singleShot(2000, lambda: self.go_to_transFee())
        else:
            print("[BillCoinConverter] Bill rejected")
            self.stop_countdown()
            QTimer.singleShot(2000, lambda: self.navigate(self.PAGE_exclamation_notequal))

    def on_bill_finished(self):
        print("[BillCoinConverter] Bill handler finished")

    # --- Coin handling logic ---
    # -------------------------
    # Call this to begin coin insertion page
    # -------------------------
    def start_coin_insertion(self):
        """
        Start the coin insertion flow.
        """
        self.coin_counts = {1: 0, 5: 0, 10: 0, 20: 0}
        self.total_amount_to_dispense = self.inserted_bill_amount  # bill only for now  

        # ensure previous worker is stopped
        if hasattr(self, "coin_handler_worker") and self.coin_handler_worker is not None:
            try:
                if self.coin_handler_worker.isRunning():
                    self.coin_handler_worker.stop()
            except Exception:
                pass
            self.coin_handler_worker = None

        # start new worker
        self.coin_handler_worker = CoinAcceptorWorker(handler=self.coin_handler, required_amount=self.selected_fee)
        self.coin_handler_worker.coinInserted.connect(self.on_single_coin_inserted)
        self.coin_handler_worker.coinsProcessed.connect(self.on_coins_finalized)
        self.coin_handler_worker.start()

        # start UI countdown (existing helper). When timeout occurs, it will call self.on_coin_timeout()
        self.start_countdown(on_timeout=self.on_coin_timeout)

        print(f"[BillCoinConverter] Coin insertion started (required_fee=P{self.selected_fee}")

        
    # Live coin update (called on every coinInserted signal)
    # -------------------------
    def on_single_coin_inserted(self, denomination, denom_count, total_value):
        """
        denomination: int coin value (1/5/10/20)
        denom_count: count of that denom
        total_value: running total in pesos
        """
        # update per-denom UI
        self.coin_counts[denomination] = denom_count
        if hasattr(self, "coin_labels") and denomination in self.coin_labels:
            self.coin_labels[denomination].setText(str(denom_count))

        # update running totals
        self.inserted_coin_amount = total_value
        self.total_money_inserted = self.inserted_bill_amount + self.inserted_coin_amount
        # excess_coins defined as inserted_coins - fee (can be negative)
        self.excess_coins = self.inserted_coin_amount - self.selected_fee
        self.total_amount_to_dispense = self.selected_amount + self.excess_coins

        # update UI
        self.bc_current_count_coins.setText(f"P{total_value}")

        # restart/extend countdown on each coin insertion
        self.start_countdown(on_timeout=self.on_coin_timeout)

        print(f"[BillCoinConverter] on_single_coin_inserted: denom={denomination}, "
            f"denom_count={denom_count}, running_total=P{total_value}, "
            f"excess_coins={self.excess_coins}, to_dispense={self.total_amount_to_dispense}")


    # -------------------------
    # Finalization when worker finishes naturally (reached >= fee or user typed done)
    # -------------------------
    def on_coins_finalized(self, total_value):
        """
        Called when CoinHandlerWorker finishes (natural completion).
        total_value is final total inserted coins.
        """
        self.stop_countdown()
        self.on_timeout = None  # prevent auto-navigation
        # ensure we stop and clear worker
        if hasattr(self, "coin_handler_worker") and self.coin_handler_worker is not None:
            try:
                if self.coin_handler_worker.isRunning():
                    self.coin_handler_worker.stop()
            except Exception:
                pass
            self.coin_handler_worker = None

        # update final totals (this also covers cases when total_value == 0)
        self.inserted_coin_amount = total_value
        self.total_money_inserted = self.inserted_bill_amount + self.inserted_coin_amount
        self.excess_coins = self.inserted_coin_amount - self.selected_fee
        self.total_amount_to_dispense = self.selected_amount + self.excess_coins

        # UI
        self.bc_current_count_coins.setText(f"P{total_value}")

        print(f"[BillCoinConverter] on_coins_finalized - total_value=P{total_value}, "
            f"excess_coins={self.excess_coins}, to_dispense={self.total_amount_to_dispense}")

        # If user reached or exceeded fee, automatically proceed
        if self.inserted_coin_amount >= self.selected_fee:
            # proceed to next page (auto)
            QTimer.singleShot(1500, lambda: self.go_to_cb_dashboard2())
        else:
            # still less than fee but worker done (user typed 'done' or similar):
            # allow user to proceed explicitly; we do NOT auto-fail
            # you can also navigate automatically to choice page if you prefer
            print("[BillCoinConverter] Coins less than fee but worker finished - waiting for user action")


    # -------------------------
    # User pressed PROCEED while on coin-insert page
    # -------------------------
    def on_proceed_coin_pressed(self, _=None):
        """User pressed Proceed while on coin insertion page."""
        # 1) stop countdown and disable further timeout
        self.stop_countdown()
        self.on_timeout = None

        # 2) prevent double-processing
        if getattr(self, "_coins_finalized", False):
            print("[Proceed] Coins already finalized; ignoring duplicate proceed.")
            return
        self._coins_finalized = True

        # 3) stop worker if running (cooperative)
        if hasattr(self, "coin_handler_worker") and self.coin_handler_worker is not None:
            try:
                if self.coin_handler_worker.isRunning():
                    print("[Proceed] Stopping coin handler worker...")
                    # request stop; don't block
                    self.coin_handler_worker.stop()
            except Exception as e:
                print("[Proceed] Error stopping worker:", e)
            finally:
                # remove reference (worker may still be winding down but we won't wait)
                self.coin_handler_worker = None

        # 4) compute final coin total from the controller's coin_counts (authoritative)
        total_value = sum(int(denom) * int(count) for denom, count in self.coin_counts.items())
        self.inserted_coin_amount = total_value

        # 5) core accounting (correct formulas)
        self.total_money_inserted = int(self.inserted_bill_amount) + int(self.inserted_coin_amount)
        self.excess_coins = int(self.inserted_coin_amount) - int(self.selected_fee)    # may be negative
        self.total_amount_to_dispense = self.selected_amount - int(self.selected_fee)

        # 6) update UI
        self.bc_current_count_coins.setText(f"P{total_value}")
        # optionally disable proceed button to prevent re-click
        try:
            self.cb_insert_proceed_3.setEnabled(False)
        except Exception:
            pass

        print(f"[Proceed] Finalized coins=P{total_value}, "
            f"bill=P{self.inserted_bill_amount}, fee=P{self.selected_fee}, "
            f"excess_coins={self.excess_coins}, to_dispense=P{self.total_amount_to_dispense}")

        # 7) navigate to the next page/flow (deduct or dashboard)
        # choose whichever is your flow; commonly:
        QTimer.singleShot(500, lambda: self.go_to_cb_dashboard2())

    # -------------------------
    # Timer timeout handling
    # -------------------------
    def on_coin_timeout(self):
        """
        Called when countdown ends while on coin insertion page.
        If coins < required fee: automatically deduct from bill and record coins as excess.
        If coins >= required fee: proceed normally.
        """
        print("[BillCoinConverter] Coin insertion timer expired - evaluating...")

        # Stop the worker gracefully
        if hasattr(self, "coin_handler_worker") and self.coin_handler_worker is not None:
            try:
                if self.coin_handler_worker.isRunning():
                    self.coin_handler_worker.stop()
            except Exception:
                pass
            self.coin_handler_worker = None

        # Compute totals from inserted coins
        total_value = sum(denom * count for denom, count in self.coin_counts.items())
        self.inserted_coin_amount = total_value
        self.total_money_inserted = self.inserted_bill_amount + self.inserted_coin_amount
        self.excess_coins = self.inserted_coin_amount - self.selected_fee
        self.total_amount_to_dispense = self.selected_amount + self.excess_coins

        # Update UI
        self.bc_current_count_coins.setText(f"P{total_value}")

        if self.inserted_coin_amount < self.selected_fee:
            # Not enough coins → auto deduct fee from bill
            print("[BillCoinConverter] Timeout with insufficient coins - auto deducting fee from bill")

            # Deduct flow: bill - fee, but coins are preserved as excess
            self.excess_coins = self.inserted_coin_amount   # keep inserted coins as excess
            self.total_amount_to_dispense = self.selected_amount - self.selected_fee + self.excess_coins

            # Navigate to dashboard (same as deduct flow)
            self.cb_dashboard_selected.setText(f"P{self.selected_amount}")
            self.update_dashboard_checkboxes()
            QTimer.singleShot(1000, lambda: self.navigate(self.PAGE_dashboardFrame))
        else:
            # Enough coins → proceed as if finalized
            print("[BillCoinConverter] Timeout but fee covered - proceeding to dashboard")
            QTimer.singleShot(1000, lambda: self.go_to_cb_dashboard2())

        print(f"[BillCoinConverter] Timeout final state: "
            f"coins=P{self.inserted_coin_amount}, "
            f"bill=P{self.inserted_bill_amount}, "
            f"fee=P{self.selected_fee}, "
            f"excess_coins={self.excess_coins}, "
            f"to_dispense=P{self.total_amount_to_dispense}")

    # For coin dispensing
    def on_dispense_ack(self, denom, qty):
        print(f"[ACK] Dispensing ₱{denom} x{qty}")

    def on_dispense_done(self, denom, qty):
        print(f"[DONE] Dispensed ₱{denom} x{qty}")
        # You could also update a progress bar here

    def on_dispense_error(self, msg):
        print("[ERROR] Dispense failed:", msg)
        self.navigate(self.PAGE_insufficient)

    def on_dispense_finished(self):
        print("[BillCoinConverter] Dispensing finished")
        self.navigate(self.PAGE_successfullyDispensed)

    # TO Del
    def go_back_cb_insert(self, _=None):
        self.navigate(2)

    # TO Del
    def go_back_cb_confirm(self, _=None):
        self.navigate(1)

