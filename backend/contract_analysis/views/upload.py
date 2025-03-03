import io
import logging

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from pdf2image import convert_from_bytes

from contract_analysis.models import Contract, ContractFile
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.utils import validate_image_type, validate_file_size

logger = logging.getLogger(__name__)

allowed_types = ["application/pdf", "image/jpeg", "image/png"]


def convert_pdf_to_images(file, uploaded_contract):
    try:
        images = convert_from_bytes(file.read(), dpi=200, thread_count=4, fmt="png")
        for i, img in enumerate(images):
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            # Create new in-memory file
            page_filename = f"{file.name.split('.')[0]}_page_{i+1}.png"

            # Create and save contract file with encrypted content
            contract_file = ContractFile.objects.create(
                contract=uploaded_contract,
                file_name=page_filename,
                file_type="image/png",
            )

            # Encrypt and save the image content
            contract_file.set_file_content(buffer.getvalue())
            contract_file.save()

            logger.info(f"PDF page {i+1} saved for contract {uploaded_contract.id}")
    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        raise ValidationError("Fehler bei der PDF-Konvertierung")


def upload_contract(request):
    if request.method != "POST":
        return error_response("Invalid request method", 405)

    logger.info(f"Uploading files for user {request.user}")
    try:
        files = request.FILES.getlist("files")
        if not files:
            return error_response("Keine Dateien hochgeladen", 400)

        # Actually use the allowed_types for validation
        for file in files:
            if file.content_type not in allowed_types:
                return error_response(f"Unerlaubter Dateityp: {file.content_type}", 400)

        uploaded_contract = Contract.objects.create(user=request.user)
        logger.info(f"Created new contract {uploaded_contract.id}")

        unprocessed_files = list(files)

        while unprocessed_files:
            file = unprocessed_files.pop(0)

            # Handle PDF conversion
            if file.content_type == "application/pdf":
                convert_pdf_to_images(file, uploaded_contract)
                continue

            # Process image file
            validate_image_type(file)
            validate_file_size(file)

            # Read the file content
            file_content = file.read()

            # Create and save contract file with encrypted content
            contract_file = ContractFile.objects.create(
                contract=uploaded_contract,
                file_name=file.name,
                file_type=file.content_type,
            )

            # Encrypt and save the content
            contract_file.set_file_content(file_content)
            contract_file.save()

            logger.info(f"File {file.name} saved for contract {uploaded_contract.id}")

        return JsonResponse({"success": True, "contract_id": str(uploaded_contract.id)})

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return error_response(str(e))
    except Exception as e:
        return handle_exception(e)
