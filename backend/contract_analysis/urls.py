from django.urls import path
from django.views.generic import TemplateView

from .views.analysis import analyze_contract, analyze_contract_update
from .views.contract import (
    archive_contract,
    get_contract_file,
    home,
    landing,
    save_edited_contract,
    get_contract,
    edit_contract,
)
from .views.upload import upload_contract

urlpatterns = [
    path("", landing, name="landing"),
    path("home", home, name="home"),
    path("contracts/upload", upload_contract, name="upload_contract"),
    path("contracts/<uuid:contract_id>/", get_contract, name="contract"),
    path(
        "contracts/<uuid:contract_id>/file/<str:file_id>",
        get_contract_file,
        name="contract_file",
    ),
    path(
        "contracts/<uuid:contract_id>/archive",
        archive_contract,
        name="archive_contract",
    ),
    path("contracts/<uuid:contract_id>/edit", edit_contract, name="edit_contract"),
    path(
        "contracts/<uuid:contract_id>/save/",
        save_edited_contract,
        name="save_edited_contract",
    ),
    path(
        "contracts/<uuid:contract_id>/analyze",
        analyze_contract,
        name="analyze_contract",
    ),
    path(
        "contracts/analyze/update",
        analyze_contract_update,
        name="contract_status_update",
    ),
    path("price", TemplateView.as_view(template_name="pricing.html"), name="pricing"),
]
