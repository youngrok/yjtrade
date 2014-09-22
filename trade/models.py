from django.db import models
from django.forms.models import model_to_dict


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

    def as_dict(self):
        data = model_to_dict(self)
        data['begin'] = float(self.begin)
        data['end'] = float(self.end)
        data['high'] = float(self.high)
        data['low'] = float(self.low)
        return data

    def __unicode__(self):
        return '%s %s %s %s %s %s' % (self.time, self.period, self.begin, self.end, self.high, self.low)

class Price(models.Model):
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    value = models.DecimalField(max_digits=10, decimal_places=2)


class Trade(models.Model):
    minutebar = models.ForeignKey(MinuteBar, null=True)
    type = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.IntegerField()
    status = models.CharField(max_length=100, default='in')
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)

    def as_dict(self):
        data = model_to_dict(self)
        data['minutebar'] = model_to_dict(self.minutebar)
        data['created'] = self.created
        data['updated'] = self.updated
        return data

class Configuration(models.Model):
    amount_a = models.IntegerField()
    amount_b = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)