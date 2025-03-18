import logging
import os
import tempfile
from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from asgiref.sync import async_to_sync

from contract_analysis.analysis import ContractProcessor
from contract_analysis.models.contract import Contract, ContractDetails
from contract_analysis.utils.error import error_response

logger = logging.getLogger(__name__)


class ContractBaseView(LoginRequiredMixin, View):
    """Base view for contract operations with common functionality."""

    def get_contract(self, contract_id):
        """Get contract object with permission check."""
        return get_object_or_404(Contract, id=contract_id, user=self.request.user)

    def check_processing_status(self, contract):
        """Check if contract is already being processed."""
        if contract.status == "processing":
            return False
        return True

    def mark_processing(self, contract):
        """Mark contract as processing."""
        contract.status = "processing"
        contract.save(update_fields=['status'])

    def mark_analyzed(self, contract):
        """Mark contract as analyzed."""
        contract.status = "analyzed"
        contract.save(update_fields=['status'])

    def mark_error(self, contract):
        """Mark contract as having an error."""
        contract.status = "error"
        contract.save(update_fields=['status'])

    def get_contract_images(self, contract) -> List[str]:
        """Create temporary image files from contract files."""
        contract_files = contract.files.all()
        temp_images = []

        for file in contract_files:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_file.write(file.get_file_content())
                temp_images.append(temp_file.name)

        return temp_images

    def clean_up_temp_files(self, temp_images):
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
        logger.info(f"Analyzing contract {contract_id} for user {request.user}")
        contract = self.get_contract(contract_id)
        temp_images = []

        try:
            # Check if already processing
            if not self.check_processing_status(contract):
                return error_response("Contract is already being analyzed", status=400)

            with transaction.atomic():
                # Update contract status to "processing"
                self.mark_processing(contract)

                # Extract structured details from the text
                temp_images = self.get_contract_images(contract)

                # Use async_to_sync to call the asynchronous process_contract method
                contract_details = async_to_sync(self.contract_processor.process_contract)(
                    contract_images=temp_images
                )

                ContractDetails.update_contract_details(contract, contract_details)

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
