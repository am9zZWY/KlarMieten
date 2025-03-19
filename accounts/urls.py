from django.contrib.auth.views import LoginView
from django.urls import path

from .views import SignUpView

urlpatterns = [
    path(
        "login",
        LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("signup", SignUpView.as_view(), name="signup"),
]
