from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.http import JsonResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt

from .analysis import extract_details_with_gemini
from .models import Contract, ContractDetails
from .utils import get_nested


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
    extracted_details = extract_details_with_gemini(contract.contract_file.path)
    print(extracted_details)

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

    details.start_date = get_nested(extracted_details, ["rental_terms", "start_date"])
    details.end_date = get_nested(extracted_details, ["rental_terms", "end_date"])
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


@csrf_exempt
@login_required
def upload_files(request):
    if request.method == "POST":
        files = request.FILES.getlist("files")
        for file in files:
            if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
                return JsonResponse({"success": False, "error": "Ungültiger Dateityp."})
            if file.size > 10 * 1024 * 1024:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Die Datei darf nicht größer als 10MB sein.",
                    }
                )
            path = default_storage.save(
                f"uploads/{file.name}", ContentFile(file.read())
            )
            Contract.objects.create(
                user=request.user,
                contract_file=path,
                ai_model_version="v1",
                file_name=file.name,
            )
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Ungültige Anfrage."})
