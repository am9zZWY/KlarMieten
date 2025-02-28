import base64
import io
import logging
import os
import tempfile
import time
import uuid

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse
from django.http.response import StreamingHttpResponse
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.views import View
from pdf2image import convert_from_bytes

from .utils.utils import get_nested, validate_file_size, validate_image_type
from darf_vermieter_das import settings
from darf_vermieter_das.settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from .analysis import extract_details_with_gemini
from .models import Contract, ContractDetails, ContractFile, Paragraph

logger = logging.getLogger(__name__)


# Create your views here.
def landing(request):
    logger.info("Rendering landing page")
    return render(request, "landing.html")


@login_required
def home(request):
    logger.info(f"Rendering home page for user {request.user}")
    contracts = Contract.objects.filter(user=request.user)
    return render(request, "home.html", {"contracts": contracts})


@login_required
def contract(request, contract_id):
    # Try to get from cache first
    cache_key = f"contract_{contract_id}_{request.user.id}"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, "contract.html", cached_data)
    
    # Get from database
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    contract_details = ContractDetails.objects.filter(contract=contract).first()
    
    # Cache for 10 minutes
    context = {"contract": contract, "contract_details": contract_details}
    cache.set(cache_key, context, 60 * 10)
    
    return render(request, "contract.html", context)


@login_required
def contract_file(request, contract_id, file_id):
    """Serve encrypted file contents from database"""
    logger.info(f"Accessing contract file {file_id} for contract {contract_id}")

    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    contract_file = get_object_or_404(ContractFile, id=file_id, contract=contract)
    
    if contract_file.encrypted_content is None:
        return HttpResponse("File not found", status=404)
    
    # Decrypt the file
    try:
        file_content = contract_file.get_file_content()
        return HttpResponse(file_content, content_type=contract_file.file_type)
    except ValueError as e:
        logger.error(f"Error decrypting file: {e}")
        return HttpResponse("Error accessing file", status=500)


def edit_contract(request, contract_id):
    """
    View for editing a contract
    """
    # Get the contract and verify ownership
    logger.info(f"Editing contract {contract_id} for user {request.user}")
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    logger.info(f"Editing contract {contract_id} for user {request.user}")

    context = {
        "contract": contract,
    }

    return render(request, "edit_contract.html", context)


@login_required
def save_edited_contract(request):
    """
    AJAX endpoint to save a censored contract image
    """
    # Check if the request is a POST request
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "error": "Invalid request method"}, status=405
        )

    file_id = request.POST.get("file_id")
    censored_image = request.POST.get("censored_image")

    if not file_id or not censored_image:
        return JsonResponse(
            {"success": False, "error": "Missing required data"}, status=400
        )

    try:
        # Get the contract file and verify ownership
        contract_file = get_object_or_404(ContractFile, id=file_id)
        if contract_file.contract.user != request.user:
            return JsonResponse(
                {"success": False, "error": "Permission denied"}, status=403
            )

        # Process the data URL
        if "," in censored_image:
            header, encoded = censored_image.split(",", 1)
            binary_data = base64.b64decode(encoded)

            # Create directory for censored images if it doesn't exist
            censored_dir = os.path.join(settings.MEDIA_ROOT, "censored")
            os.makedirs(censored_dir, exist_ok=True)

            # Generate a unique filename
            filename = f"censored_{uuid.uuid4()}.png"
            file_path = os.path.join(censored_dir, filename)

            # Save the censored image
            with open(file_path, "wb") as f:
                f.write(binary_data)

            # Update the contract file with the censored image path
            relative_path = os.path.join("censored", filename)

            # If you want to keep track of the original and censored versions,
            # you could add a field to ContractFile model like 'censored_file'
            # For now, we'll update the existing file
            old_file_path = contract_file.contract_file.path
            contract_file.contract_file = relative_path
            contract_file.save()

            # Delete the old file if it exists and is different from the new one
            if os.path.exists(old_file_path) and old_file_path != file_path:
                try:
                    os.remove(old_file_path)
                except OSError:
                    # Log this error but don't fail the request
                    pass

            return JsonResponse({"success": True})
        else:
            return JsonResponse(
                {"success": False, "error": "Invalid image data"}, status=400
            )

    except Exception as e:
        # Log the error
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error saving censored image: {str(e)}")

        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def archive_contract(request, contract_id):
    logger.info(f"Deleting contract {contract_id} for user {request.user}")

    contract = get_object_or_404(Contract, id=contract_id)
    # TODO: Archive the contract instead of deleting it
    contract.delete()

    return JsonResponse({"success": True})


@login_required
def analyze_contract(request, contract_id):
    logger.info(f"Analyzing contract {contract_id} for user {request.user}")
    contract = Contract.objects.get(id=contract_id)

    # Check if the status is already processing
    if contract.status == "processing":
        return JsonResponse(
            {"success": False, "error": "Fehler bei der Verarbeitung des Vertrags"},
            status=500,
        )

    # Update contract status to "processing"
    contract.status = "processing"
    contract.save()

    # Extract details using the Gemini extraction function
    contract_files = contract.files.all()
    
    # Create temporary image files for analysis
    temp_images = []
    try:
        for file in contract_files:
            # Create temp file with decrypted content
            fd, temp_path = tempfile.mkstemp(suffix='.png')
            with os.fdopen(fd, 'wb') as temp_file:
                temp_file.write(file.get_file_content())
            temp_images.append(temp_path)
            
        extracted_details, total_token_count = extract_details_with_gemini(temp_images)
        
        for temp_path in temp_images:
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Error removing temp file {temp_path}: {e}")
    except Exception as e:
        # Clean up temp files on error
        for temp_path in temp_images:
            try:
                os.unlink(temp_path)
            except:
                pass
                
        logger.error(f"Error during contract analysis: {e}")
        contract.status = "error"
        contract.save()
        return JsonResponse(
            {"success": False, "error": "Fehler bei der Verarbeitung des Vertrags"},
            status=500,
        )

    logger.info(f"Total token count for contract {contract_id}: {total_token_count}")

    # TODO: Update the token count in the user's profile
    print(f"Total token count: {total_token_count}")

    # Update contract status to "analyzed"
    contract.status = "analyzed"
    contract.save()

    # Create and populate ContractDetails
    # Check if ContractDetails already exists
    details = ContractDetails.objects.filter(contract=contract).first()
    if not details:
        details = ContractDetails.objects.create(contract=contract)

    # Use the get_nested function to safely access nested values
    details.contract_type = get_nested(extracted_details, ["contract_type"])
    details.address = get_nested(extracted_details, ["property_details", "address"])
    details.number_of_rooms = get_nested(
        extracted_details, ["property_details", "rooms", "number_of_rooms"]
    )
    details.kitchen = get_nested(
        extracted_details, ["property_details", "rooms", "kitchen"], False
    )
    details.bathroom = get_nested(
        extracted_details, ["property_details", "rooms", "bathroom"], False
    )
    details.separate_wc = get_nested(
        extracted_details, ["property_details", "rooms", "separate_wc"], False
    )
    details.balcony_or_terrace = get_nested(
        extracted_details, ["property_details", "rooms", "balcony_or_terrace"], False
    )
    details.garden = get_nested(
        extracted_details, ["property_details", "rooms", "garden"], False
    )
    details.garage_or_parking_space = get_nested(
        extracted_details,
        ["property_details", "rooms", "garage_or_parking_space"],
        False,
    )

    shared_facilities = get_nested(
        extracted_details, ["property_details", "shared_facilities"], []
    )
    details.shared_facilities = ", ".join(shared_facilities)

    keys_provided = get_nested(
        extracted_details, ["property_details", "keys_provided"], []
    )
    details.keys_provided = ", ".join(keys_provided)

    details.start_date = convert_date(
        get_nested(extracted_details, ["rental_terms", "start_date"])
    )
    details.end_date = convert_date(
        get_nested(extracted_details, ["rental_terms", "end_date"])
    )
    details.duration = get_nested(extracted_details, ["rental_terms", "duration"])
    details.termination_terms = get_nested(
        extracted_details, ["rental_terms", "termination_terms"]
    )
    details.monthly_rent = get_nested(extracted_details, ["pricing", "monthly_rent"])

    additional_costs = get_nested(
        extracted_details, ["pricing", "additional_costs"], []
    )
    # TODO: Save additional costs in the database
    # details.additional_costs = ", ".join(
    #    [f"{cost['description']}: {cost['amount']}" for cost in additional_costs]
    # )

    details.total_rent = get_nested(extracted_details, ["pricing", "total_rent"])
    details.heating_type = get_nested(extracted_details, ["heating_type"])

    additional_clauses = get_nested(extracted_details, ["additional_clauses"], [])
    details.additional_clauses = ", ".join(additional_clauses)

    paragraphs = get_nested(extracted_details, ["paragraphs"], [])
    # Create paragraphs in the database
    for paragraph in paragraphs:
        logger.info(f"Creating paragraph: {paragraph}")
        Paragraph.objects.create(
            contract_details=details,
            title=paragraph["title"],
            content=paragraph["content"],
        )

    details.save()
    logger.info(f"Contract {contract_id} analyzed and details saved")

    # Return a success response with the extracted details
    return JsonResponse({"success": True, "details": extracted_details})


def analyze_contract_update(request: WSGIRequest) -> StreamingHttpResponse:
    contract_id = request.GET.get("id")
    contract = Contract.objects.get(id=contract_id)
    last_status = contract.status  # Store initial status

    def event_stream():
        nonlocal last_status  # Access last_status from outer scope
        while True:
            contract.refresh_from_db()

            if contract.status != last_status:  # Check if status changed
                yield f"data: {contract.status}\n\n"
                last_status = contract.status

            time.sleep(0.5)

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


class FileUploadView(View):
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    template_name = "file_upload.html"
    login_required = True

    def post(self, request):
        logger.info(f"Uploading files for user {request.user}")
        try:
            files = request.FILES.getlist("files")
            if not files:
                return JsonResponse(
                    {"success": False, "error": "Keine Dateien hochgeladen"},
                    status=400,
                )

            uploaded_contract = Contract.objects.create(
                user=request.user
            )
            logger.info(f"Created new contract {uploaded_contract.id}")

            unprocessed_files = list(files)
            
            while unprocessed_files:
                file = unprocessed_files.pop(0)
                
                # Handle PDF conversion
                if file.content_type == "application/pdf":
                    try:
                        images = convert_from_bytes(
                            file.read(), dpi=200, thread_count=4, fmt="png"
                        )
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
            return JsonResponse({"success": False, "error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"success": False, "error": "Ein Fehler ist aufgetreten"}, status=500)