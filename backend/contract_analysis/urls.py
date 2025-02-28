from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("home", views.home, name="home"),
    path("contracts/upload", views.FileUploadView.as_view(), name="upload_contract"),
    path("contracts/<uuid:contract_id>/", views.contract, name="contract"),
    path("contracts/<uuid:contract_id>/file/<str:file_name>", views.contract_file, name="contract_file"),
    path("contracts/<uuid:contract_id>/archive", views.archive_contract, name="archive_contract"),
    path("contracts/<uuid:contract_id>/edit", views.edit_contract, name="edit_contract"),
    path("contracts/<uuid:contract_id>/save/", views.save_edited_contract, name="save_edited_contract"),
    path("contracts/<uuid:contract_id>/analyze", views.analyze_contract, name="analyze_contract"),
    path(
        "contracts/analyze/update",
        views.analyze_contract_update,
        name="contract_status_update",
    ),
    path("price", TemplateView.as_view(template_name="pricing.html"), name="price"),
]
