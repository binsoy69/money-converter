#python -m PyQt5.uic.pyuic -x CoinToBill.ui -o coin_to_bill_ui.py

from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QTimer, QTime, QDate, Qt
from PyQt5 import uic
from coinToBill_controller import CoinBillConverter
from billToCoin_controller import BillCoinConverter
from billToBill_controller import BillBillConverter
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bill_handler.python.pi_bill_handler import *
from coin_handler.python.coin_handler_serial import *

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        ui_path = os.path.join(os.path.dirname(__file__), "MainDesign.ui")
        uic.loadUi(ui_path, self)

        # --- Shared handlers created once ---
        self.bill_handler = PiBillHandler()
        self.coin_handler = CoinHandlerSerial()


        self.current_index = 0
        self.update_button_styles(self.current_index)

        # Load CoinToBill.ui as a page in main_stackedWidget
        self.coin_bill_widget = CoinBillConverter(parent=self, navigate=self.navigate, bill_handler=self.bill_handler, coin_handler=self.coin_handler)
        self.main_stackedWidget.addWidget(self.coin_bill_widget)
        self.coin_bill_index = self.main_stackedWidget.indexOf(self.coin_bill_widget)

        # Load BillToCoin.ui as a page in main_stackedWidget
        self.bill_coin_widget = BillCoinConverter(parent=self, navigate=self.navigate, bill_handler=self.bill_handler, coin_handler=self.coin_handler)
        self.main_stackedWidget.addWidget(self.bill_coin_widget)
        self.bill_coin_index = self.main_stackedWidget.indexOf(self.bill_coin_widget)

        self.bill_bill_widget = BillBillConverter(parent=self, navigate=self.navigate, bill_handler=self.bill_handler, coin_handler=self.coin_handler)
        self.main_stackedWidget.addWidget(self.bill_bill_widget)
        self.bill_bill_index = self.main_stackedWidget.indexOf(self.bill_bill_widget)

        # Navigation buttons
        self.connect_buttons({
            self.type_backBtn: lambda: self.navigate(0),
            self.service_backBtn: lambda: self.navigate(1),
            self.type_currencyBtn: lambda: self.navigate(2),
            self.main_startBtn: lambda: self.navigate(1),
            self.service_c2bBtn: lambda: self.go_to_coinbill(),
            self.service_b2cBtn: lambda: self.go_to_billcoin(),
            self.service_b2bBtn: lambda: self.go_to_billbill(),

            
        })

        # Page indicators
        page_buttons = [self.main_page1Btn, self.main_page2Btn, self.main_page3Btn]
        for idx, btn in enumerate(page_buttons):
            btn.clicked.connect(lambda checked, i=idx: self.switch_carousel(i))

        # Shadow buttons
        self.apply_shadow([
            self.type_foreignBtn, self.type_currencyBtn, self.type_ewalletBtn,
            self.service_c2bBtn, self.service_b2cBtn, self.service_b2bBtn
        ])

        # Time updates
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
    
    def go_to_billbill(self):
        self.bill_bill_widget.reset_to_start()
        self.navigate(self.bill_bill_index)

    def go_to_billcoin(self):
        self.bill_coin_widget.reset_to_start()
        self.navigate(self.bill_coin_index)

    def go_to_coinbill(self):
        self.coin_bill_widget.reset_to_start()
        self.navigate(self.coin_bill_index)


    def connect_buttons(self, button_action_dict):
        for btn, func in button_action_dict.items():
            btn.clicked.connect(func)

    def apply_shadow(self, buttons):
        for btn in buttons:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 160))
            btn.setGraphicsEffect(shadow)

    def navigate(self, index):
        self.main_stackedWidget.setCurrentIndex(index)

    def update_time(self):
        current_time = QTime.currentTime().toString("h:mm AP")
        current_date = QDate.currentDate().toString("dddd | dd.MM.yyyy")

        self.main_timeLabel.setText(current_time)
        self.main_timeLabel_2.setText(current_time)
        self.main_DateLabel.setText(current_date)
        self.main_DateLabel_2.setText(current_date)
        self.main_DateLabel_3.setText(current_date)
        self.main_timeLabel_3.setText(current_time)

    def update_button_styles(self, active_index):
        buttons = [self.main_page1Btn, self.main_page2Btn, self.main_page3Btn]
        for i, btn in enumerate(buttons):
            btn.setFixedSize(21, 21)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {"white" if i == active_index else "transparent"};
                    color: {"black" if i == active_index else "white"};
                    border: {"none" if i == active_index else "1px solid white"};
                    border-radius: 10px;
                }}
            """)

    def switch_carousel(self, new_index):
        if new_index == self.current_index:
            return

        direction = 1 if new_index > self.current_index else -1
        width = self.main_carousel.frameGeometry().width()

        current_widget = self.main_carousel.currentWidget()
        next_widget = self.main_carousel.widget(new_index)

        current_widget.setGeometry(0, 0, width, self.height())
        next_widget.setGeometry(direction * width, 0, width, self.height())

        anim_old = QPropertyAnimation(current_widget, b"pos", self)
        anim_old.setDuration(600)
        anim_old.setStartValue(current_widget.pos())
        anim_old.setEndValue(QPoint(-direction * width, 0))
        anim_old.setEasingCurve(QEasingCurve.InOutQuad)

        anim_new = QPropertyAnimation(next_widget, b"pos", self)
        anim_new.setDuration(600)
        anim_new.setStartValue(next_widget.pos())
        anim_new.setEndValue(QPoint(0, 0))
        anim_new.setEasingCurve(QEasingCurve.InOutQuad)

        self.main_carousel.setCurrentIndex(new_index)
        anim_old.start()
        anim_new.start()

        self.update_button_styles(new_index)
        self.current_index = new_index


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
