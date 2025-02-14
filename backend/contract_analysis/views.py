import io
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views import View
from pdf2image import convert_from_bytes

from darf_vermieter_das.settings import FILE_UPLOAD_MAX_MEMORY_SIZE
from .analysis import extract_details_with_gemini
from .models import Contract, ContractDetails, ContractFile
from .utils import get_nested, convert_date, validate_file_size, validate_file_type

logger = logging.getLogger(__name__)


# Create your views here.
def landing(request):
    logger.info("Rendering landing page")
    template = loader.get_template("landing.html")
    return HttpResponse(template.render(None, request))


@login_required
def home(request):
    logger.info(f"Rendering home page for user {request.user}")
    template = loader.get_template("home.html")
    user = request.user
    contracts = Contract.objects.filter(user=user)
    context = {"contracts": contracts}
    return HttpResponse(template.render(context, request))


@login_required
def contract(request):
    contract_id = request.GET.get("id")
    logger.info(f"Fetching contract {contract_id} for user {request.user}")
    template = loader.get_template("contract.html")

    # Get the contract id from the URL
    contract_id = request.GET.get("id")
    contract = Contract.objects.get(id=contract_id)

    # Get the contract details
    contract_details = ContractDetails.objects.filter(contract=contract).first()
    context = {"contract": contract, "contract_details": contract_details}

    return HttpResponse(template.render(context, request))


@login_required
def analyze_contract(request):
    contract_id = request.GET.get("contract_id")
    logger.info(f"Analyzing contract {contract_id} for user {request.user}")
    # Get the contract ID from the request
    contract_id = request.GET.get("contract_id")
    contract = Contract.objects.get(id=contract_id)

    # Update contract status to "processing"
    contract.status = "processing"
    contract.save()

    # Extract details using the Gemini extraction function
    contract_files = contract.files.all()
    # Get image paths from the contract files
    image_paths = [file.contract_file.path for file in contract_files]
    try:
        extracted_details, total_token_count = extract_details_with_gemini(image_paths)
    except Exception as e:
        logger.error(f"Error during contract analysis: {e}")
        logger.exception(e)
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
    details.additional_costs = ", ".join(
        [f"{cost['description']}: {cost['amount']}" for cost in additional_costs]
    )

    details.total_rent = get_nested(extracted_details, ["pricing", "total_rent"])
    details.heating_type = get_nested(extracted_details, ["heating_type"])

    additional_clauses = get_nested(extracted_details, ["additional_clauses"], [])
    details.additional_clauses = ", ".join(additional_clauses)

    paragraphs = get_nested(extracted_details, ["paragraphs"], [])
    details.paragraphs = "\n".join(paragraphs)

    details.save()
    logger.info(f"Contract {contract_id} analyzed and details saved")

    # Return a success response with the extracted details
    return JsonResponse({"success": True, "details": extracted_details})


class FileUploadView(View):
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    template_name = "file_upload.html"
    login_required = True

    def get(self, request):
        logger.info(f"Rendering file upload page for user {request.user}")
        context = {
            "max_file_size": FILE_UPLOAD_MAX_MEMORY_SIZE,
            "accepted_file_types": self.allowed_types,
        }
        return render(request, self.template_name, context)

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
                user=request.user,
                ai_model_version="v1",
            )
            logger.info(
                f"Created new contract {uploaded_contract.id} for user {request.user}"
            )

            unprocessed_files = list(files)

            while unprocessed_files:
                file = unprocessed_files.pop(0)

                if file.content_type == "application/pdf":
                    try:
                        images = convert_from_bytes(
                            file.read(), dpi=200, thread_count=4, fmt="png"
                        )
                        for img in images:
                            buffer = io.BytesIO()
                            img.save(buffer, format="PNG")
                            buffer.seek(0)

                            converted_file = InMemoryUploadedFile(
                                buffer,
                                None,  # Field name
                                f"{file.name.split('.')[0]}_page_{len(buffer.getvalue())}.png",
                                "image/png",
                                buffer.getbuffer().nbytes,
                                None,
                            )
                            unprocessed_files.append(converted_file)
                        continue
                    except Exception as e:
                        logger.error(f"PDF conversion error: {e}")
                        raise ValidationError("Fehler bei der PDF-Konvertierung")

                validate_file_size(file)
                validate_file_type(file)

                if file.content_type not in self.allowed_types:
                    raise ValidationError("Unzulässiger Dateityp")

                filename = default_storage.get_available_name(file.name)
                tmp_file_path = default_storage.save(f"uploads/{filename}", file)
                print(f"File saved to {tmp_file_path}")

                ContractFile.objects.create(
                    contract=uploaded_contract,
                    file_name=file.name,
                    contract_file=tmp_file_path,
                )
                logger.info(
                    f"File {file.name} uploaded and saved for contract {uploaded_contract.id}"
                )

            return JsonResponse({"success": True})

        except ValidationError as e:
            logger.error(f"Validation error during file upload: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        except Exception as e:
            logger.error(f"Unexpected error during file upload: {e}")
            logger.exception(e)
            return JsonResponse(
                {
                    "success": False,
                    "error": "Ein Fehler ist aufgetreten beim Hochladen.",
                },
                status=500,
            )
