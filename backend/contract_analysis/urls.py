from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("home", views.home, name="home"),
    path("contract", views.contract, name="contract"),
    path("analyze_contract", views.analyze_contract, name="analyze_contract"),
    path("upload", views.upload_files, name="upload_files"),
]
