import logging

from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from mietkai.faq import FAQ_pricing
from .forms import LoginForm, RegisterForm
from .models import Plan, Capability

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user:
                login(request, user)
                return redirect("home")
        return render(request, "registration/login.html", {"form": form})
    return render(request, "registration/login.html", {"form": LoginForm()})


class SignUpView(CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


# Create your views here.

def pricing(request):
    """
    Pricing page view for non-authenticated users.

    Args:
        request: HttpRequest object

    Returns:
        Rendered pricing page
    """

    plans = Plan.objects.filter(is_active=True).prefetch_related('capabilities__capability')
    capabilities = Capability.objects.all()

    # Create a list of plans for the template
    plan_list = []
    for plan in plans:
        plan_list.append({
            'id': plan.id,
            'name': plan.name,
            'price': plan.price,
            'description': plan.description,
            'billing_type': plan.billing_type,
            'capabilities': []
        })

    # For each plan, add all capabilities with their status
    for plan_data in plan_list:
        plan = Plan.objects.get(id=plan_data['id'])

        # Get all plan capabilities
        plan_capabilities = {
            pc.capability_id: pc
            for pc in plan.capabilities.all()
        }

        # Add all capabilities with their status for this plan
        for capability in capabilities:
            plan_capability = plan_capabilities.get(capability.id)

            capability_info = {
                'id': capability.id,
                'name': capability.name,
                'has_capability': bool(plan_capability),
                'display_value': None
            }

            # Add value if needed
            if plan_capability and capability.value_type != 'BOOLEAN':
                if capability.value_type == 'INTEGER':
                    capability_info['display_value'] = plan_capability.value_int
                else:  # STRING
                    capability_info['display_value'] = plan_capability.value_text

            plan_data['capabilities'].append(capability_info)

    context = {
        "faq": FAQ_pricing,
        'plans': plan_list
    }

    return render(request, "pricing.html", context)
