from django.urls import path

from .views import LoginInView, SignUpView



urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginInView.as_view(), name="login"),
]