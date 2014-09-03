from django.db import models


class Box(models.Model):
    date = models.DateField(db_index=True)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)


class MinuteBar(models.Model):
    time = models.DateTimeField(db_index=True)
    period = models.TimeField()
    begin = models.DecimalField(max_digits=10, decimal_places=2)
    end = models.DecimalField(max_digits=10, decimal_places=2)
    high = models.DecimalField(max_digits=10, decimal_places=2)
    low = models.DecimalField(max_digits=10, decimal_places=2)

    def __unicode__(self):
        return '%s %s %s %s %s %s' % self.time, self.period, self.begin, self.end, self.high, self.low

class Price(models.Model):
    time = models.DateTimeField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)


class Trade(models.Model):
    minutebar = models.ForeignKey(MinuteBar, null=True)
    type = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.IntegerField()
    status = models.CharField(max_length=100, default='in')
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)


class Configuration(models.Model):
    amount_a = models.IntegerField()
    amount_b = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)