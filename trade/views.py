import json
import traceback
from datetime import datetime, timedelta
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.http.response import HttpResponse, HttpResponseRedirect
from django.template.context import RequestContext
from djangox.mako.shortcuts import render_to_response
from trade import trader
from trade.models import Configuration, Box, MinuteBar, Price, Trade


def index(request):
    return render_to_response('index.html', locals(), RequestContext(request))


def initial_box(request):
    box = trader.trader.load_initial_box()
    print 'loaded', box

    return JSONResponse({
        'high': box.high,
        'low': box.low
    })


def set_box(request):
    try:
        box = Box.objects.get(date=trader.trader.today())
        box.high = request.POST['high']
        box.low = request.POST['low']
        box.save()

    except:
        box = Box.objects.create(date=trader.trader.today(),
                                 high=request.POST['high'],
                                 low=request.POST['low'])

    return HttpResponseRedirect('/')

def start(request):
    try:
        trader.trader.start()
        return HttpResponse(json.dumps({
            'running': trader.trader.running,
        }))
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({'error': unicode(e)})


def stop(request):
    trader.trader.stop()
    return HttpResponse(json.dumps({
        'running': trader.trader.running,
    }))


def status(request):
    now = datetime.now()
    try:
        conf = Configuration.objects.get()
    except:
        conf = Configuration.objects.create(amount_a=0, amount_b=0)

    try:
        box = trader.trader.box()
        if (now.minute in range(0, 59, 1) and now.second in [1, 2]) or request.GET.get('force', 'false') == 'true':
            trader.trader.load_minute_bar()

        data = {
            'current_price': trader.trader.load_current(),
            'running': trader.trader.running,
            'configuration': model_to_dict(conf)
        }

        nine_am = datetime(year=now.year, month=now.month, day=now.day, hour=9)
        if now.hour < 9: nine_am - timedelta(days=1)

        data['box'] = {'low': float(box.low), 'high': float(box.high)}
        data['minute_bars'] = [t.as_dict() for t in MinuteBar.objects.filter(time__gte=nine_am).order_by('-time')]
        data['trades'] = [t.as_dict() for t in Trade.objects.all().select_related().order_by('-updated')[0:15]]
    except:
        traceback.print_exc()


    return JSONResponse(data)


class JSONResponse(HttpResponse):

    def __init__(self, data, *args, **kwargs):
        super(HttpResponse, self).__init__(*args, **kwargs)
        self.content = json.dumps(data, cls=DjangoJSONEncoder)
        self.content_type="application/json"
