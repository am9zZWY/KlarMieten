import logging
import os

from asgiref.sync import async_to_sync
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect

from customers.models import Entitlement
from contract_analysis.analysis import ContractProcessor
from contract_analysis.models.contract import Contract
from contract_analysis.utils.error import error_response

logger = logging.getLogger(__name__)


class ContractBaseView(LoginRequiredMixin, View):
    """Base view for contract operations with common functionality."""

    def get_contract(self, contract_id):
        """Get contract object with permission check."""
        return get_object_or_404(Contract, id=contract_id, user=self.request.user)

    @staticmethod
    def check_processing_status(contract):
        """Check if contract is already being processed."""
        if contract.status == "processing":
            return False
        return True

    @staticmethod
    def mark_processing(contract):
        """Mark contract as processing."""
        contract.status = "processing"
        contract.save(update_fields=['status'])

    @staticmethod
    def mark_analyzed(contract):
        """Mark contract as analyzed."""
        contract.status = "analyzed"
        contract.save(update_fields=['status'])

    @staticmethod
    def mark_error(contract):
        """Mark contract as having an error."""
        contract.status = "error"
        contract.save(update_fields=['status'])

    @staticmethod
    def clean_up_temp_files(temp_images):
        """Clean up temporary files."""
        for temp_path in temp_images:
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error removing temp file {temp_path}: {e}")


@method_decorator(csrf_protect, name='dispatch')
class ContractAnalysisView(ContractBaseView):
    """View for analyzing contracts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.contract_processor = ContractProcessor()

    def post(self, request, contract_id):
        """Process a POST request to analyze a contract."""
        user = request.user

        # Check if user is authenticated
        if not user.is_authenticated:
            return error_response("Unauthorized", status=401)

        logger.info(f"Analyzing contract {contract_id} for user {request.user}")

        # Check if user has permission to analyze contracts
        entitlement = Entitlement.get(user, 'analyses')
        #if not entitlement or entitlement and entitlement.value <= 0:
         #   return error_response("User does not have permission to analyze contracts. Please upgrade your plan.",
         #                         status=403)

        contract = self.get_contract(contract_id)
        temp_images = []

        try:
            # Check if already processing
            if not self.check_processing_status(contract):
                return error_response("Contract is already being analyzed", status=400)

            with transaction.atomic():
                # Update contract status to "processing"
                self.mark_processing(contract)

                async_to_sync(self.contract_processor.process_contract)(
                    contract=contract
                )

                # Update contract status to "analyzed"
                self.mark_analyzed(contract)

                # Return success response
                return JsonResponse({"success": True})

        except Exception as e:
            self.mark_error(contract)
            logger.exception(f"Error analyzing contract {contract_id}: {str(e)}")
            return error_response(str(e), status=500)
        finally:
            self.clean_up_temp_files(temp_images)


class ContractStatusView(ContractBaseView):
    """View for checking contract status."""

    def get(self, request):
        """Process a GET request to check contract status."""
        contract_id = request.GET.get("id")
        if not contract_id:
            return error_response("Contract ID is required", status=400)

        contract = self.get_contract(contract_id)
        return JsonResponse({"status": contract.status})
