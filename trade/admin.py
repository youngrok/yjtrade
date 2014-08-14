from django.contrib import admin
from trade.models import PriceBar, Trade

admin.site.register(PriceBar)
admin.site.register(Trade)