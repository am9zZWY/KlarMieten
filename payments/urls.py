from django.urls import path

from . import views

urlpatterns = [
    path('get-checkout-session/', views.get_checkout_session, name='get-checkout-session'),
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('customer-portal/', views.customer_portal, name='customer-portal'),
    path('webhook/', views.webhook_received, name='webhook'),
]
