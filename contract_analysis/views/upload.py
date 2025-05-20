import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from contract_analysis.models.contract import Contract
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.image import convert_pdf_to_images
from contract_analysis.utils.utils import validate_type, validate_file_size
from customers.models import Entitlement

logger = logging.getLogger(__name__)

allowed_types = ["application/pdf", "image/jpeg", "image/png"]


@login_required
@require_http_methods(["POST"])
def upload_contract(request):
    user = request.user

    # Check if user has permission to upload contracts
    uploads_available = Entitlement.get(user, 'uploads')
    logger.info(f"User {user} has {uploads_available} uploads available")
    #if uploads_available is None or uploads_available <= 0:
    #    return error_response("No uploads available", 403)

    logger.info(f"Uploading files for user {user}")
    try:
        files = request.FILES.getlist("files")
        if not files:
            return error_response("Keine Dateien hochgeladen", 400)

        with transaction.atomic():
            # Create a new contract
            uploaded_contract = Contract.objects.create(user=user)
            logger.info(f"Created new contract {uploaded_contract.id}")

            for file in files:
                validate_file_size(file)
                validate_type(file)

                if file.content_type == "application/pdf":
                    convert_pdf_to_images(file, uploaded_contract)
                else:
                    # Process image files
                    uploaded_contract.add_file(file.name, file.read(), file.content_type, )

        return JsonResponse({"success": True, "contract_id": str(uploaded_contract.id)})

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return error_response(str(e))
    except Exception as e:
        return handle_exception(e)
