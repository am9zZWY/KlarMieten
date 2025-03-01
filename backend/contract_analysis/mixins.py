# mixins.py
import logging
from django.http import Http404
from django.shortcuts import get_object_or_404

logger = logging.getLogger(__name__)


class OwnershipRequiredMixin:
    """Mixin to ensure users can only access their own contracts"""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # Check if object has a user field or related contract
        if hasattr(obj, "user") and obj.user != self.request.user:
            raise Http404("Not found")

        if hasattr(obj, "contract") and obj.get_contract.user != self.request.user:
            raise Http404("Not found")

        logger.info(f"User {self.request.user} accessed object: {obj}")

        return obj
