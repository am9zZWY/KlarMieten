from django.shortcuts import render

from klarmieten.faq import FAQ_landing, FAQ_pricing


def main(request):
    """
    Landing page view for non-authenticated users.

    Args:
        request: HttpRequest object

    Returns:
        Rendered landing page with FAQ content
    """
    context = {
        "faq": FAQ_landing
    }
    return render(request, "main.html", context)
