from django.db import models


class PriceBar(models.Model):
    time = models.DateTimeField()
    period = models.TimeField()
    start = models.IntegerField()
    end = models.IntegerField()
    low = models.IntegerField()
    high = models.IntegerField()


class Trade(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=100)
    price = models.IntegerField()
    amount = models.IntegerField()

