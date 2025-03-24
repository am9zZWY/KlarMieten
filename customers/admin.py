from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Product, Plan, Capability, PlanCapability
from .models import User

admin.site.register(User, UserAdmin)
admin.site.register(Product)
admin.site.register(Plan)
admin.site.register(Capability)
admin.site.register(PlanCapability)
