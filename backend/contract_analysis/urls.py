from django.urls import path
from . import views

urlpatterns = [
    path("", views.contract_analysis, name="home"),
    path("upload/", views.upload_files, name="upload_files"),
]
