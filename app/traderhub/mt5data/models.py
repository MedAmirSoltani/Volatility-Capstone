from django.db import models

class MT5Candle(models.Model):
    symbol = models.CharField(max_length=10)
    time = models.DateTimeField(unique=True)
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    tick_volume = models.BigIntegerField()

    def __str__(self):
        return f"{self.symbol} - {self.time}"


# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
class CustomUser(AbstractUser):
    birth_date = models.DateField(null=True, blank=True)
    preferences = models.OneToOneField('Preferences', on_delete=models.CASCADE, null=True, blank=True)


class Preferences(models.Model):
    RISK_TOLERANCE_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]

    INVESTMENT_HORIZON_CHOICES = [
        ('short_term', 'Short Term'),
        ('medium_term', 'Medium Term'),
        ('long_term', 'Long Term')
    ]


    INVESTMENT_OBJECTIVE_CHOICES = [
        ('capital_preservation', 'Capital Preservation'),
        ('income_generation', 'Income Generation'),
        ('wealth_accumulation', 'Wealth Accumulation')
    ]

    KNOWLEDGE_EXPERIENCE_CHOICES = [
        ('novice', 'Novice'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ]
    SECTORS_CHOICES = [
        ('all', 'All (highly recommended)'),
        ('assurance', 'Assurance'),
        ('other', 'industrial'),
        ('leasing', 'Leasing (not recommended)'),
        ('bank', 'Bank (not recommended)')
 
    
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_preferences')
    risk_tolerance = models.CharField(max_length=10, choices=RISK_TOLERANCE_CHOICES)
    investment_horizon = models.CharField(max_length=20, choices=INVESTMENT_HORIZON_CHOICES)
    investment_objective = models.CharField(max_length=20, choices=INVESTMENT_OBJECTIVE_CHOICES)
    knowledge_experience = models.CharField(max_length=20, choices=KNOWLEDGE_EXPERIENCE_CHOICES)
    sectors = models.CharField(max_length=20, choices=SECTORS_CHOICES)
    available_funds = models.DecimalField(max_digits=12, decimal_places=2)
from django.db import models

class ForumTopic(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    topic = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class ForumComment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)