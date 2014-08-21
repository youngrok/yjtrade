from django.contrib import admin
from trade.models import MinuteBar, Trade, Configuration, Price, Box

admin.site.register(Box)
admin.site.register(MinuteBar)
admin.site.register(Configuration)
admin.site.register(Price)
admin.site.register(Trade)