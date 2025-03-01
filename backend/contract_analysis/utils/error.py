import logging

from django.core.exceptions import ValidationError
from django.http.response import JsonResponse

logger = logging.getLogger(__name__)


def error_response(message, status=400):
    """Standardized error response for views"""
    logger.error(f"Error: {message}")
    return JsonResponse({"success": False, "error": message}, status=status)


def handle_exception(e, default_message="Ein Fehler ist aufgetreten"):
    """Standardized exception handler for views"""
    if isinstance(e, ValidationError):
        logger.warning(f"Validation error: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    else:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "error": default_message}, status=500)
