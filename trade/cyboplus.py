from datetime import datetime

cyboplus = None


def initialize():
    global cyboplus
    if cyboplus: return

    cyboplus = CyboPlus()
    print 'initialized'

class CyboPlus(object):

    def __init__(self):
        self.chart=win32com.client.Dispatch("CpForeDib.OvFutureChart")

    def load_initial_box(self):
        now = datetime.now()

        self.chart.SetInputValue(0,'CLU14')
        self.chart.SetInputValue(1,'2')  #요청구분
        self.chart.SetInputValue(4, 15)   #요청개수
        self.chart.SetInputValue(5, [5, 4, 1, 0])    #종가
        self.chart.SetInputValue(6, ord('m')) #분봉
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

        return min(*low_values), max(*high_values)