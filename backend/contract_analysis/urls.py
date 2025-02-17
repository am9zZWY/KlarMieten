from django.urls import path
from django.views.generic import TemplateView

from . import views
from .views import analyze_contract_update

urlpatterns = [
    path("", views.landing, name="landing"),
    path("home", views.home, name="home"),
    path("upload_contract", views.FileUploadView.as_view(), name="upload_contract"),
    path("archive_contract", views.archive_contract, name="archive_contract"),
    path("contract", views.contract, name="contract"),
    path("analyze_contract", views.analyze_contract, name="analyze_contract"),
    path(
        "analyze_contract_update",
        views.analyze_contract_update,
        name="analyze_contract_update",
    ),
    path("price", TemplateView.as_view(template_name="pricing.html"), name="price"),
]
