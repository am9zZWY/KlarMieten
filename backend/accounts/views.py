from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import RegisterForm


# Create your views here.

class SignUpView(CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"
