from django.shortcuts import render

from darf_vermieter_das.faq import FAQ_landing


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
