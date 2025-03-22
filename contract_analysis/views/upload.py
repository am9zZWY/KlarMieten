import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse

from contract_analysis.models.contract import Contract
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.image import convert_pdf_to_images
from contract_analysis.utils.utils import validate_type, validate_file_size

logger = logging.getLogger(__name__)

allowed_types = ["application/pdf", "image/jpeg", "image/png"]


def upload_contract(request):
    if request.method != "POST":
        return error_response("Invalid request method", 405)

    user = request.user

    # Check if user is authenticated
    if not user.is_authenticated:
        return error_response("Unauthorized", 401)

    # Check if user has permission to upload contracts
    # TODO: has_upload_permission = user.has_active_capability('contract_upload')

    logger.info(f"Uploading files for user {user}")
    try:
        files = request.FILES.getlist("files")
        if not files:
            return error_response("Keine Dateien hochgeladen", 400)

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
                uploaded_contract.add_file(file.name, file.content_type, file.read())

        return JsonResponse({"success": True, "contract_id": str(uploaded_contract.id)})

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return error_response(str(e))
    except Exception as e:
        return handle_exception(e)
