# coding: utf8
from datetime import datetime, date, timedelta
import random
import traceback
from django.db.models.aggregates import Max, Min

from django.utils import timezone

from trade.models import Box, MinuteBar, Trade, Configuration, Price

minute_bar_interval = 15

class MockClient(object):
    initial_price = 50

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
        if key == 7:
            return self.current

        return self.input[4]

    def GetDataValue(self, key, index):
        unit = self.input[7]
        now = datetime.now()
        nearest_time = timezone.get_current_timezone().localize(
            datetime(year=now.year, month=now.month, day=now.day,
                     hour=now.hour, minute=now.minute - (now.minute % unit),
                     second=0)) - timedelta(minutes=unit * (self.input[4] - index - 1))

        print now, self.input[4], index, nearest_time
        prices = Price.objects.filter(created__gte=nearest_time - timedelta(minutes=unit),
                                      created__lt=nearest_time).order_by('created')

        if key == 0:
            return now.strftime('%Y%m%d')
        elif key == 1:
            return nearest_time.hour * 100 + nearest_time.minute
        elif key == 2:
            return prices[0].value
        elif key == 3:
            return prices.aggregate(Max('value'))['value__max']
        elif key == 4:
            return prices.aggregate(Min('value'))['value__min']
        elif key == 5:
            return prices[prices.count() - 1].value
        else:
            return self.value

    @classmethod
    def WithEvents(cls, com, trader):
        cls.handler = trader()

    def Subscribe(self):
        pass

    @classmethod
    def PumpWaitingMessages(cls):
        if Price.objects.count() == 0:
            Price.objects.create(value=cls.initial_price)

        cls.current = float(Price.objects.order_by('-created')[0].value)

        if random.random() > 0.5:
            cls.current = round(cls.current + (random.random() - 0.5) * 2, 2)
            cls.handler.OnReceived()


try:
    import win32com.client as client
    import pythoncom
except:
    client = MockClient
    pythoncom = MockClient


class NoBoxException(Exception):
    pass


class YJTrader(object):
    def __init__(self):

        self.chart = client.Dispatch("CpForeDib.OvFutureChart")
        self.current_price = 0
        self.running = False

        class EventHandler(object):
            def OnReceived(this):
                self.current_price = self.current.GetHeaderValue(7)
                price = Price.objects.create(value=self.current_price)
                print 'current', price.created, price.value
                self.exit_if_matched()



        self.current = client.Dispatch("CpForeDib.OvFutCur")
        client.WithEvents(self.current, EventHandler)
        self.current.SetInputValue(0, 'CLX14')
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
            try:
                now = datetime.now()
                print 'loading box', now

                self.chart.SetInputValue(0, 'CLX14')
                self.chart.SetInputValue(1, '2')  # 요청구분
                self.chart.SetInputValue(4, 15)  # 요청개수
                self.chart.SetInputValue(5, [5, 4, 1, 0])  # 종가
                self.chart.SetInputValue(6, ord('m'))  # 분봉
                self.chart.SetInputValue(7, 60) # 분 단위
                self.chart.SetInputValue(8, '1')
                self.chart.BlockRequest()
                num = self.chart.GetHeaderValue(3)

                low_values = []
                high_values = []
                for i in range(num):
                    d = self.chart.GetDataValue(0, i)
                    t = self.chart.GetDataValue(1, i)

                    print d, t, self.chart.GetDataValue(3, i)
                    if t > 1500.0: continue
                    if t < 900.0: continue

                    if str(int(d)) != now.strftime('%Y%m%d'): continue

                    low_values.append(self.chart.GetDataValue(3, i))
                    high_values.append(self.chart.GetDataValue(2, i))

                return Box.objects.create(date=self.today(), high=max(*high_values), low=min(*low_values))
            except:
                traceback.print_exc()

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

    def load_minute_bar(self, time=None, force_enter=False):
        try:
            if not time:
                time = datetime.now()

            self.chart.SetInputValue(0, 'CLV14')
            self.chart.SetInputValue(1, '2')  # 요청구분
            self.chart.SetInputValue(4, 10)  # 요청개수
            self.chart.SetInputValue(5, [0, 1, 3, 4, 5, 6])
            self.chart.SetInputValue(6, ord('m'))  # 분봉
            self.chart.SetInputValue(7, minute_bar_interval) # 분 단위
            self.chart.SetInputValue(8, '1')
            self.chart.BlockRequest()
            num = self.chart.GetHeaderValue(3)

            for i in range(num):
                try:
                    d = self.chart.GetDataValue(0, i)
                    t = int(self.chart.GetDataValue(1, i))

                    dt = timezone.get_current_timezone().localize(datetime(year=time.year, month=time.month, day=time.day,
                                                                           hour=t / 100, minute=t % 100, second=0))

                    print t, dt

                    bar, created = MinuteBar.objects.get_or_create(time=dt, defaults=dict(
                        period=time(minute=minute_bar_interval),
                        low=self.chart.GetDataValue(4, i),
                        high=self.chart.GetDataValue(3, i),
                        begin=self.chart.GetDataValue(2, i),
                        end=self.chart.GetDataValue(5, i)
                    ))

                    if created:
                        print 'loaded minute bar ', bar.time, bar.begin, bar.end

                    if created or force_enter:
                        self.enter_if_matched(bar)
                except:
                    traceback.print_exc()

        except:
            traceback.print_exc()

    def enter_if_matched(self, bar):
        if not self.running: return

        conf = Configuration.objects.get()
        box = self.box()
        if bar.begin < box.high < bar.end:
            print 'enter-buy', bar
            Trade.objects.create(minutebar=bar, type='a-enter-buy', price=bar.end, amount=conf.amount_a)
            Trade.objects.create(minutebar=bar, type='b-enter-buy', price=bar.end, amount=conf.amount_b)
        elif bar.begin > box.low > bar.end:
            print 'enter-sell', bar
            Trade.objects.create(minutebar=bar, type='a-enter-sell', price=bar.end, amount=conf.amount_a)
            Trade.objects.create(minutebar=bar, type='b-enter-sell', price=bar.end, amount=conf.amount_b)

    def exit_if_matched(self):
        if not self.running: return

        box = self.box()
        ten = MinuteBar.objects.order_by('-time')[:10]
        mean = sum([float(bar.end) for bar in ten]) / 10.0

        for trade in Trade.objects.filter(type='a-enter-buy', status='in'):
            if self.current_price <= trade.minutebar.low:
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
            if self.current_price >= trade.minutebar.high:
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
            if self.current_price <= box.high - 0.03:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='b-exit-buy', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()

        for trade in Trade.objects.filter(type='b-enter-sell', status='in'):
            if self.current_price >= box.low + 0.03:
                Trade.objects.create(minutebar=trade.minutebar, 
                                     type='b-exit-sell', 
                                     price=trade.current_price,
                                     amount=trade.amount,
                                     status='out')
                trade.status = 'out'
                trade.save()


trader = YJTrader()


