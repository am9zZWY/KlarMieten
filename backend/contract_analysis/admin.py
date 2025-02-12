from django.contrib import admin

from .models import Contract, PaymentHistory, Subscription

admin.site.register(Contract)
admin.site.register(Subscription)
admin.site.register(PaymentHistory)
