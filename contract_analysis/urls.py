from django.urls import path

from .views.analysis import ContractAnalysisView, ContractStatusView
from .views.contract import (
    archive_contract,
    get_contract_file,
    home,
    save_edited_contract,
    get_contract,
    edit_contract, pricing,
)
from .views.upload import upload_contract

urlpatterns = [
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
        ContractAnalysisView.as_view(),
        name="analyze_contract",
    ),
    path(
        "contracts/<uuid:contract_id>/analyze/update",
        ContractStatusView.as_view(),
        name="analyze_contract_update",
    ),
    path("price", pricing, name="pricing"),
]
