from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View

from .analysis import extract_details_with_gemini
from .models import Contract, ContractDetails
from .utils import get_nested, convert_date


# Create your views here.
def landing(request):
    template = loader.get_template("landing.html")
    return HttpResponse(template.render(None, request))


@login_required
def home(request):
    template = loader.get_template("home.html")
    user = request.user
    contracts = Contract.objects.filter(user=user)
    context = {"contracts": contracts}
    return HttpResponse(template.render(context, request))


@login_required
def contract(request):
    template = loader.get_template("contract.html")

    # Get the contract id from the URL
    contract_id = request.GET.get("id")
    contract = Contract.objects.get(id=contract_id)

    # Get the contract details
    contract_details = ContractDetails.objects.filter(contract=contract).first()
    context = {"contract": contract, "contract_details": contract_details}

    return HttpResponse(template.render(context, request))


@csrf_exempt
@login_required
def analyze_contract(request):
    # Get the contract ID from the request
    contract_id = request.GET.get("contract_id")
    contract = Contract.objects.get(id=contract_id)

    # Update contract status to "processing"
    contract.status = "processing"
    contract.save()

    # Extract details using the Gemini extraction function
    extracted_details, total_token_count = extract_details_with_gemini(contract.contract_file.path)

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
    details.city = get_nested(extracted_details, ["property_details", "city"])
    details.postal_code = get_nested(extracted_details, ["property_details", "postal_code"])
    details.country = get_nested(extracted_details, ["property_details", "country"])
    details.number_of_rooms = get_nested(extracted_details, ["property_details", "rooms", "number_of_rooms"])
    details.kitchen = get_nested(extracted_details, ["property_details", "rooms", "kitchen"], False)
    details.bathroom = get_nested(extracted_details, ["property_details", "rooms", "bathroom"], False)
    details.separate_wc = get_nested(extracted_details, ["property_details", "rooms", "separate_wc"], False)
    details.balcony_or_terrace = get_nested(extracted_details, ["property_details", "rooms", "balcony_or_terrace"],
                                            False)
    details.garden = get_nested(extracted_details, ["property_details", "rooms", "garden"], False)
    details.garage_or_parking_space = get_nested(extracted_details,
                                                 ["property_details", "rooms", "garage_or_parking_space"], False)

    shared_facilities = get_nested(extracted_details, ["property_details", "shared_facilities"], [])
    details.shared_facilities = ", ".join(shared_facilities)

    keys_provided = get_nested(extracted_details, ["property_details", "keys_provided"], [])
    details.keys_provided = ", ".join(keys_provided)

    details.start_date = convert_date(get_nested(extracted_details, ["rental_terms", "start_date"]))
    details.end_date = convert_date(get_nested(extracted_details, ["rental_terms", "end_date"]))
    details.duration = get_nested(extracted_details, ["rental_terms", "duration"])
    details.termination_terms = get_nested(extracted_details, ["rental_terms", "termination_terms"])
    details.monthly_rent = get_nested(extracted_details, ["pricing", "monthly_rent"])

    additional_costs = get_nested(extracted_details, ["pricing", "additional_costs"], [])
    details.additional_costs = ", ".join([f"{cost['description']}: {cost['amount']}" for cost in additional_costs])

    details.total_rent = get_nested(extracted_details, ["pricing", "total_rent"])
    details.heating_type = get_nested(extracted_details, ["heating_type"])

    additional_clauses = get_nested(extracted_details, ["additional_clauses"], [])
    details.additional_clauses = ", ".join(additional_clauses)

    paragraphs = get_nested(extracted_details, ["paragraphs"], [])
    details.paragraphs = "\n".join(paragraphs)

    details.save()

    # Return a success response with the extracted details
    return JsonResponse({"success": True, "details": extracted_details})


class FileUploadView(View):
    max_file_size = 10 * 1024 * 1024  # 10MB
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
    template_name = 'file_upload.html'

    def get(self, request):
        context = {
            'max_file_size': self.max_file_size,
            'accepted_file_types': self.allowed_types,
        }
        return render(request, 'file_upload.html', context)

    def post(self, request):
        try:
            files = request.FILES.getlist('files')

            if not files:
                raise ValidationError('Keine Dateien ausgewählt.')

            uploaded_files = []
            for file in files:
                # Validate file type
                if file.content_type not in self.allowed_types:
                    raise ValidationError('Ungültiger Dateityp.')

                # Validate file size
                if file.size > self.max_file_size:
                    raise ValidationError('Datei ist zu groß.')

                # Generate unique filename
                filename = default_storage.get_available_name(file.name)

                # Save file
                path = default_storage.save(f'uploads/{filename}', file)
                uploaded_files.append(path)

                # Create a new contract object
                Contract.objects.create(
                    user=request.user,
                    contract_file=path,
                    ai_model_version="v1",
                    file_name=file.name,
                )

            return JsonResponse({
                'success': True,
                'files': uploaded_files
            })

        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Ein Fehler ist aufgetreten beim Hochladen.'
            }, status=500)
