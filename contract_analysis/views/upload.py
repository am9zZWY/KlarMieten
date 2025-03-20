import io
import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from pdf2image import convert_from_bytes

from contract_analysis.models.contract import ContractFile, Contract
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.image import reduce_image_size
from contract_analysis.utils.utils import validate_type, validate_file_size

logger = logging.getLogger(__name__)

allowed_types = ["application/pdf", "image/jpeg", "image/png"]


def save_contract_file(contract, filename, content_type, content):
    """Helper function to create and save a contract file with encrypted content."""
    contract_file = ContractFile.objects.create(
        contract=contract,
        file_name=filename,
        file_type=content_type,
    )
    contract_file.set_file_content(content)
    contract_file.save()
    logger.info(f"File {filename} saved for contract {contract.id}")
    return contract_file


def convert_pdf_to_images(file, contract):
    """Convert PDF to images and save them as contract files."""
    try:
        images = convert_from_bytes(file.read(), dpi=200, thread_count=4, fmt="png")
        base_name = file.name.split(".")[0]

        for i, img in enumerate(images):
            # Reduce image size and save to buffer
            resized_img = reduce_image_size(img, percent=35)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="PNG")
            buffer.seek(0)

            page_filename = f"{base_name}_page_{i + 1}.png"
            save_contract_file(contract, page_filename, "image/png", buffer.getvalue())

    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        raise ValidationError("Fehler bei der PDF-Konvertierung")


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
                save_contract_file(
                    uploaded_contract, file.name, file.content_type, file.read()
                )

        return JsonResponse({"success": True, "contract_id": str(uploaded_contract.id)})

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return error_response(str(e))
    except Exception as e:
        return handle_exception(e)
