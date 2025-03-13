from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
