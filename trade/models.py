from django.db import models


class Box(models.Model):
    date = models.DateField(db_index=True)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)


class MinuteBar(models.Model):
    time = models.DateTimeField(db_index=True)
    period = models.TimeField()
    start = models.DecimalField(max_digits=10, decimal_places=2)
    end = models.DecimalField(max_digits=10, decimal_places=2)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)


class Price(models.Model):
    time = models.DateTimeField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Trade(models.Model):
    datetime = models.DateTimeField(auto_now_add=True, db_index=True)
    type = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.IntegerField()


class Configuration(models.Model):
    amount_a = models.IntegerField()
    amount_b = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)