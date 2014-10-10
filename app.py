import datetime
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5 import QtGui
import ui
import win32com.client
import traceback

class MainWindow(QMainWindow):

    minutebar_interval = 15

    def __init__(self, uiobj):
        self.ui = uiobj
        QMainWindow.__init__(self)
        uiobj.setupUi(self)

        self.minutebars = {}
        self.amount_a = 0
        self.amount_b = 0
        self.stock_code = 'CLX14'
        self.trades = []

        self.chart = win32com.client.Dispatch("CpForeDib.OvFutureChart")
        self.current = win32com.client.Dispatch("CpForeDib.OvFutCur")

        self.ui.load_box_button.clicked.connect(self.load_box)
        self.ui.apply_button.clicked.connect(self.apply_config)

        self.ui.stock_code.setText('CLY14')
        self.ui.amount_a.setText('0')
        self.ui.amount_b.setText('0')

        self.watch_current_price()
        self.watch_minutebars()

    def apply_config(self):
        self.stock_code = self.ui.stock_code.text()
        self.amount_a = int(self.ui.amount_a.text())
        self.amount_b = int(self.ui.amount_b.text())

        log('set stock code:', self.stock_code, 'amount a', self.amount_a, 'amount b', self.amount_b)

    def watch_minutebars(self):
        timer = QTimer(self)
        timer.setInterval(60000)
        timer.timeout.connect(self.load_minutebar)
        timer.start()
        log('start watching minute bar')

    def watch_current_price(self):

        class EventHandler:
            def OnReceived(this):
                self.current_price = self.current.GetHeaderValue(7)
                # price = Price.objects.create(value=self.current_price)
                self.ui.current_price.setText(str(self.current_price))
                # self.exit_if_matched()

        win32com.client.WithEvents(self.current, EventHandler)
        self.current.SetInputValue(0, self.stock_code)
        self.current.Subscribe()
        log('start watching current price')

    def load_box(self):
        today = self.today().strftime('%Y%m%d')
        now = datetime.datetime.now()
        self.chart.SetInputValue(0, self.stock_code)
        self.chart.SetInputValue(1, '2')  # 요청구분
        self.chart.SetInputValue(2, today)  # date
        self.chart.SetInputValue(4, 15)  # 요청개수
        self.chart.SetInputValue(5, [5, 4, 1, 0])  # 종가
        self.chart.SetInputValue(6, ord('m'))  # 분봉
        self.chart.SetInputValue(7, 60)
        self.chart.SetInputValue(8, '1')
        self.chart.BlockRequest()
        num = self.chart.GetHeaderValue(3)

        low_values = []
        high_values = []
        for i in range(num):
            d = self.chart.GetDataValue(0, i)
            t = self.chart.GetDataValue(1, i)

            if t > 1500.0: continue
            if t < 900.0: continue

            if str(int(d)) != today: continue

            low_values.append(self.chart.GetDataValue(3, i))
            high_values.append(self.chart.GetDataValue(2, i))

        self.box = Box(date=self.today(), high=max(*high_values), low=min(*low_values))
        self.ui.box_high.setText(str(self.box.high))
        self.ui.box_low.setText(str(self.box.low))

    def set_box(self):
    	self.box = Box(date=self.today(), high=float(self.ui.box_high.text()), low=float(self.ui.box_low.text()))

    def today(self):
        today = datetime.date.today()
        if datetime.datetime.now().hour < 9:
            today -= datetime.timedelta(days=1)

        return today

    @pyqtSlot()
    def load_minutebar(self):
        now = datetime.datetime.now()

        self.chart.SetInputValue(0, self.stock_code)
        self.chart.SetInputValue(1, '2')  # 요청구분
        self.chart.SetInputValue(2, now.strftime('%Y%m%d'))
        self.chart.SetInputValue(4, 10)  # 요청개수
        self.chart.SetInputValue(5, [0, 1, 3, 4, 5, 6])
        self.chart.SetInputValue(6, ord('m'))  # 분봉
        self.chart.SetInputValue(7, self.minutebar_interval) # 분 단위
        self.chart.SetInputValue(8, '1')
        self.chart.BlockRequest()
        num = self.chart.GetHeaderValue(3)

        now_hm = now.hour * 100 + now.minute
        if now.hour == 0:
            now_hm += 2400

        for i in range(num):
            try:
                d = int(self.chart.GetDataValue(0, i))
                t = int(self.chart.GetDataValue(1, i))

                bar = MinuteBar(
                        time = (d, t),
                        low=self.chart.GetDataValue(4, i),
                        high=self.chart.GetDataValue(3, i),
                        begin=self.chart.GetDataValue(2, i),
                        end=self.chart.GetDataValue(5, i)
                )
                self.minutebars[(d, t)] = bar

                if now_hm == t:
                    self.enter_if_matched(bar)

                self.ui.minutebars.setText('\n'.join([str(v) for k, v in sorted(self.minutebars.items(), key=lambda e: e[0][0] * 10000 + e[0][1])]))
            except:
                log(traceback.format_exc())

    def enter_if_matched(self, bar):
        box = self.box
        log('enter test', box.high, box.low, 'bar', bar.begin, bar.end)
        if bar.begin < box.high < bar.end:
            self.enter(bar, 'a-enter-buy', bar.end, self.amount_a)
            self.enter(bar, 'b-enter-buy', bar.end, self.amount_b)
        elif bar.begin > box.low > bar.end:
            self.enter(bar, 'a-enter-sell', bar.end, self.amount_a)
            self.enter(bar, 'b-enter-sell', bar.end, self.amount_b)

        self.ui.tradelogs.setText('\n'.join([str(t) for t in self.trades]))

    def enter(self, minutebar, enter_type, price, amount):
        self.trades.append(Trade(minutebar=minutebar, enter_type='a-enter-buy', price=minutebar.end, amount=self.amount_a))
        # TODO real api call

    def exit_if_matched(self, price):
        mean = sum([float(bar.end) for bar in self.minutebars[-10:]]) / float(max(len(self.minutebars), 10))
        for trade in [t for t in self.trades if t.status == 'in']:
            if trade.type == 'a-enter-buy':
                if self.current_price <= trade.minutebar.low:
                    trade.exit('loss', self.current_price)
                elif self.minutebars[-1].begin > mean > self.minutebars[1].end:
                    trade.exit('profit', self.current_price)

            elif trade.type == 'a-enter-sell':
                if self.current_price >= trade.minutebar.high:
                    trade.exit('loss', self.current_price)
                elif self.minutebars[-1].begin < mean < self.minutebars[-1].end:
                    trade.exit('profit', self.current_price)

            elif trade.type == 'b-enter-buy':
                if self.current_price <= self.box.high - 0.03:
                    trade.exit('exit', self.current_price)

            elif trade.type == 'b-enter-sell':
                if self.current_price >= box.low + 0.03:
                    trade.exit('exit', self.current_price)

class Box:
    def __init__(self, date, high, low):
        self.date = date
        self.high = high
        self.low = low

class MinuteBar:
    def __init__(self, time, low, high, begin, end):
        self.time = time
        self.low = low
        self.high = high
        self.begin = begin
        self.end = end

    def __str__(self):
        return '%s  %.2f  %.2f' % (self.time, self.begin, self.end)


class Trade:

    def __init__(self, minutebar, enter_type, price, amount):
        self.minutebar = minutebar
        self.enter_type = enter_type
        self.enter_price = price
        self.entered = datetime.datetime.now()

        self.exit_price = 0.0
        self.exit_type = None
        self.exited = None

        self.amount = amount
        self.status = 'in'

        log('enter', self)
        
    def exit(self, exit_type, price):
        self.exit_price = price
        self.exit_type = exit_type
        self.exited = datetime.datetime.now()
        self.status = 'out'

        log('exit', self)

    def __str__(self):
        return '%s  %s  %.2f  %d  %s  %s  %.2f  %s' % (self.minutebar.time, self.enter_type, self.enter_price, self.amount, self.entered, 
                                                       self.exit_type, self.exit_price, self.exited)

def log(*messages):
    print(*messages)
    ui_main.logs.setText(ui_main.logs.toPlainText() + "\n" + ' '.join(map(str, messages)))
    ui_main.logs.moveCursor(QtGui.QTextCursor.End)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui_main = ui.Ui_MainWindow()
    window = MainWindow(ui_main)
    window.show()
    sys.exit(app.exec_())
