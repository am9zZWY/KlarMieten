from django.contrib import admin

from .models import Contract, PaymentHistory, Subscription, User

admin.site.register(User)
admin.site.register(Contract)
admin.site.register(Subscription)
admin.site.register(PaymentHistory)
