from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("home", views.home, name="home"),
    path("contract", views.contract, name="contract"),
    path("analyze_contract", views.analyze_contract, name="analyze_contract"),
    path("upload_contract", views.FileUploadView.as_view(), name="upload_contract"),
    path("price", TemplateView.as_view(template_name="pricing.html"), name="price"),
]
