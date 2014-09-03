# coding: utf8
from datetime import datetime, date, timedelta, time
import random
from threading import Timer
import traceback
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.utils import timezone
import pytz
from trade.models import Box, MinuteBar, Trade, Configuration
from threading import Thread
import pythoncom

class MockClient(object):
    @classmethod
    def Dispatch(cls, name):
        return cls(name)

    def __init__(self, name):
        self.name = name
        self.input = {}
        self.value = 50
        self.next = 50
        self.index = 0

    def SetInputValue(self, index, value):
        self.input[index] = value

    def BlockRequest(self):
        pass

    def GetHeaderValue(self, key):
        return self.input[4]

    def GetDataValue(self, key, index):
        if self.index < index:
            self.index = index
            self.value = self.next
            self.next = self.value + (random.random() - 0.5) * 10

        unit = self.input[7]
        now = datetime.now()

        if key == 0:
            return now.strftime('%Y%m%d')
        elif key == 1:
            print index, timezone.get_current_timezone(), now.minute, now.minute % unit
            nearest_time = timezone.get_current_timezone().localize(
                datetime(year=now.year, month=now.month, day=now.day,
                         hour=now.hour, minute=now.minute - (now.minute % unit),
                         second=0))
            nearest_time -= timedelta(minutes=unit * (self.input[4] - index - 1))
            print nearest_time, nearest_time.hour * 100 + nearest_time.minute
            return nearest_time.hour * 100 + nearest_time.minute
        elif key == 2:
            return self.value
        elif key == 3:
            return self.value + random.random() * 10
        elif key == 4:
            return self.value - random.random() * 10
        elif key == 5:
            return self.next
        else:
            return self.value

    @classmethod
    def WithEvents(cls, com, trader):
        pass

    def Subscribe(self):
        pass


class NoBoxException(Exception):
    pass


class YJTrader(object):
    def __init__(self):
        try:
            import win32com.client as client
        except:
            client = MockClient

        self.client = client
        self.chart = self.client.Dispatch("CpForeDib.OvFutureChart")
        self.current_price = 0
        self.running = False

        class EventHandler(object):
            def OnReceived(this):
                print 'OnReceived'
                self.current_price = self.current.GetHeaderValue(7)
                print self.current_price


        self.current = self.client.Dispatch("CpForeDib.OvFutCur")
        self.client.WithEvents(self.current, EventHandler)
        self.current.SetInputValue(0, 'CLV14')
        self.current.Subscribe()

        print 'subscribed'

        # self.sched = BackgroundScheduler()
        # self.sched.add_job(self.load_minute_bar, CronTrigger(year="*", month="*", day="*", day_of_week="*", minute='*'))

    def load_current(self):
        pythoncom.PumpWaitingMessages()
        return self.current_price

    def today(self):
        today = date.today()
        if datetime.now().hour < 9:
            today -= timedelta(days=1)

        return today

    def box(self):
        try:
            return Box.objects.get(date=self.today())
        except:
            print self.today()
            traceback.print_exc()
            raise NoBoxException(u'Load box first.')

    def load_initial_box(self):

        try:
            return self.box()

        except NoBoxException:
            now = datetime.now()
            print 'loading box', now

            self.chart.SetInputValue(0, 'CLV14')
            self.chart.SetInputValue(1, '2')  # 요청구분
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

                if str(int(d)) != now.strftime('%Y%m%d'): continue

                low_values.append(self.chart.GetDataValue(3, i))
                high_values.append(self.chart.GetDataValue(2, i))

            return Box.objects.create(date=self.today(), high=max(*high_values), low=min(*low_values))

        except:
            traceback.print_exc()

    def start(self):
        self.box()
        self.running = True

        # if self.sched.running: return
        # self.sched.start()

    def stop(self):
        self.running = False
        # if self.sched and self.sched.running:
        #     self.sched.shutdown()

    def load_minute_bar(self):
        try:
            now = datetime.now()

            self.chart.SetInputValue(0, 'CLV14')
            self.chart.SetInputValue(1, '2')  # 요청구분
            self.chart.SetInputValue(4, 10)  # 요청개수
            self.chart.SetInputValue(5, [0, 1, 3, 4, 5, 6])
            self.chart.SetInputValue(6, ord('m'))  # 분봉
            self.chart.SetInputValue(7, 15)
            self.chart.SetInputValue(8, '1')
            self.chart.BlockRequest()
            num = self.chart.GetHeaderValue(3)

            for i in range(num):
                d = self.chart.GetDataValue(0, i)
                t = int(self.chart.GetDataValue(1, i))

                dt = timezone.get_current_timezone().localize(datetime(year=now.year, month=now.month, day=now.day,
                                                                       hour=t / 100, minute=t % 100, second=0))

                print t, dt

                if MinuteBar.objects.filter(time=dt).count() == 0:
                    bar = MinuteBar.objects.create(time=dt, period=time(minute=15),
                                                   low=self.chart.GetDataValue(4, i),
                                                   high=self.chart.GetDataValue(3, i),
                                                   begin=self.chart.GetDataValue(2, i),
                                                   end=self.chart.GetDataValue(5, i))

                    print 'loaded minute bar ', bar.time, bar.begin, bar.end

                    self.buy_if_matched(bar)

        except:
            traceback.print_exc()

    def buy_if_matched(self, bar):
        if not self.running: return

        conf = Configuration.objects.get()
        box = self.box()

        if bar.begin < box.high < bar.end:
            Trade.objects.create(minutebar=bar, type='a-enter-buy', price=bar.end, amount=conf.amount_a)
            Trade.objects.create(minutebar=bar, type='b-enter-buy', price=bar.end, amount=conf.amount_b)
        elif bar.begin > box.low > bar.end:
            Trade.objects.create(minutebar=bar, type='a-enter-sell', price=bar.end, amount=conf.amount_a)
            Trade.objects.create(minutebar=bar, type='b-enter-sell', price=bar.end, amount=conf.amount_b)

    def out_if_matched(self):
        if not self.running: return

        box = self.box()
        ten = MinuteBar.objects.order_by('-time')[:10]
        mean = sum([bar.end for bar in ten]) / 10.0

        for trade in Trade.objects.filter(type='a-enter-buy', status='in'):
            if trade.current_price <= trade.minutebar.low:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='a-exit-buy-loss', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

            elif ten[0].begin > mean > ten[0].end:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='a-exit-buy-profit', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

        for trade in Trade.objects.filter(type='a-enter-sell', status='in'):
            if trade.current_price >= trade.minutebar.low:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='a-exit-sell-loss', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

            elif ten[0].begin < mean < ten[0].end:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='a-exit-sell-profit', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

        for trade in Trade.objects.filter(type='b-enter-buy', status='in'):
            if trade.current_price >= box.high + 0.03:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='b-exit-buy', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

        for trade in Trade.objects.filter(type='b-enter-sell', status='in'):
            if trade.current_price <= box.low - 0.03:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='b-exit-sell', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()


trader = YJTrader()


