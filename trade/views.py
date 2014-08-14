import json
from django.http.response import HttpResponse
from djangox.mako.shortcuts import render_to_response
from trade.cyboplus import cyboplus

cyboplus.initialize()

def index(request):
    return render_to_response('index.html', locals())


def initial_box(request):
    high, low = cyboplus.load_initial_box()

    return HttpResponse(json.dumps({
        'high': high,
        'low': low
    }))