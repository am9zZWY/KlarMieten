import logging
import os
import tempfile
import time

from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.http.response import StreamingHttpResponse
from django.shortcuts import get_object_or_404

from contract_analysis.analysis import (
    analyze_neighborhood_with_gemini,
    extract_text_with_gemini,
    extract_details_with_gemini,
)
from contract_analysis.models import Contract, ContractDetails
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.utils import convert_date

logger = logging.getLogger(__name__)


@login_required
def analyze_contract(request, contract_id):
    # Check if the request is a POST request
    if request.method != "POST":
        return error_response("Invalid request method", status=405)

    total_token_count = 0
    logger.info(f"Analyzing contract {contract_id} for user {request.user}")

    try:
        contract = Contract.objects.get(id=contract_id)

        # Check if the status is already processing
        if contract.status == "processing":
            return error_response("Contract is already being analyzed", status=400)

        # Update contract status to "processing"
        contract.status = "processing"
        contract.save()

        # Extract structured details from the text
        images = get_contract_images(contract)
        extracted_details, detail_token_count = extract_details_with_gemini(
            contract_images=images
        )
        total_token_count += detail_token_count

        # Analyze neighborhood based on extracted address
        logger.info("Analyzing neighborhood")
        # Create full address string and geocode
        street = extracted_details["street"] if extracted_details.get("street") else ""
        postal_code = extracted_details["postal_code"] if extracted_details.get("postal_code") else ""
        city = extracted_details["city"] if extracted_details.get("city") else ""
        country = extracted_details["country"] if extracted_details.get("country") else ""
        address = f"{street} {postal_code} {city} {country}"
        neighborhood, analysis_token_count = analyze_neighborhood_with_gemini(address)
        extracted_details["neighborhood"] = neighborhood
        total_token_count += analysis_token_count

        # Update contract details with extracted information
        update_contract_details(contract, extracted_details)

        # Update contract status to "analyzed"
        contract.status = "analyzed"
        contract.save()

        # Return a success response with the extracted details
        return JsonResponse({"success": True, "details": extracted_details})

    except Exception as e:
        mark_contract_error(contract)
        return handle_exception(e)


def get_contract_images(contract):
    # Create temporary image files for analysis
    contract_files = contract.files.all()
    temp_images = []
    for file in contract_files:
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        with os.fdopen(fd, "wb") as temp_file:
            temp_file.write(file.get_file_content())
        temp_images.append(temp_path)

    return temp_images


def clean_up_temp_files(temp_images):
    for temp_path in temp_images:
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.error(f"Error removing temp file {temp_path}: {e}")


def process_contract_files(contract) -> tuple[str, int]:
    """Process contract files and extract text."""
    temp_images = []
    try:
        # Get contract images
        temp_images = get_contract_images(contract)

        # Extract text from images
        extracted_text, token_count = extract_text_with_gemini(temp_images)

        return extracted_text, token_count
    finally:
        clean_up_temp_files(temp_images)


def get_or_create_contract_details(contract):
    """Get existing contract details or create new ones."""
    details = ContractDetails.objects.filter(contract=contract).first()
    if not details:
        details = ContractDetails.objects.create(contract=contract)
    return details


def mark_contract_error(contract):
    """Mark contract as having an error."""
    contract.status = "error"
    contract.save()


def get(details, key, default):
    """Get a value from the details dictionary."""
    value = details.get(key, default)
    if value is None:
        return default
    return value


def update_contract_details(contract, extracted_details):
    """Update contract details with extracted information."""
    details = get_or_create_contract_details(contract)

    # Direct assignment of fields using .get() method with German defaults
    details.contract_type = get(extracted_details, "contract_type", "Mietvertrag")
    details.street = get(extracted_details, "street", None)
    details.city = get(extracted_details, "city", None)
    details.postal_code = get(extracted_details, "postal_code", None)
    details.country = get(extracted_details, "country", None)
    details.number_of_rooms = get(extracted_details, "number_of_rooms", 0)
    details.kitchen = get(extracted_details, "kitchen", False)
    details.bathroom = get(extracted_details, "bathroom", False)
    details.separate_wc = get(extracted_details, "separate_wc", False)
    details.balcony_or_terrace = get(extracted_details, "balcony_or_terrace", False)
    details.garden = get(extracted_details, "garden", False)
    details.garage_or_parking_space = get(
        extracted_details, "garage_or_parking_space", False
    )
    details.property_type = get(extracted_details, "property_type", None)
    details.floor_location = get(extracted_details, "floor_location", None)
    details.living_space = get(extracted_details, "living_space", None)
    details.year_of_construction = get(extracted_details, "year_of_construction", None)
    details.modernization = get(extracted_details, "modernization", None)
    details.floor = get(extracted_details, "floor", None)
    details.elevator = get(extracted_details, "elevator", False)
    details.energy_certificate = get(extracted_details, "energy_certificate", None)
    details.energy_consumption = get(extracted_details, "energy_consumption", None)
    details.energy_class = get(extracted_details, "energy_class", None)
    details.shared_facilities = get(extracted_details, "shared_facilities", None)
    details.keys_provided = get(extracted_details, "keys_provided", None)
    details.has_shared_garden = get(extracted_details, "has_shared_garden", False)
    details.has_shared_laundry = get(extracted_details, "has_shared_laundry", False)
    details.has_shared_drying_room = get(
        extracted_details, "has_shared_drying_room", False
    )
    details.num_apartment_keys = get(extracted_details, "num_apartment_keys", None)
    details.num_mailbox_keys = get(extracted_details, "num_mailbox_keys", None)
    details.num_building_keys = get(extracted_details, "num_building_keys", None)

    # Neighbourhood details
    details.neighborhood = get(extracted_details, "neighborhood", None)

    # Handle date fields with conversion if needed
    start_date = extracted_details.get("start_date")
    details.start_date = convert_date(start_date) if start_date else None

    end_date = extracted_details.get("end_date")
    details.end_date = convert_date(end_date) if end_date else None

    details.duration = get(extracted_details, "duration", None)
    details.is_unlimited_contract = get(
        extracted_details, "is_unlimited_contract", True
    )
    details.termination_terms = get(extracted_details, "termination_terms", None)
    details.termination_notice_period_tenant = get(
        extracted_details, "termination_notice_period_tenant", 3
    )
    details.termination_notice_period_landlord = get(
        extracted_details, "termination_notice_period_landlord", 3
    )
    details.monthly_rent = get(extracted_details, "monthly_rent", None)
    details.additional_costs = get(extracted_details, "additional_costs", None)
    details.total_rent = get(extracted_details, "total_rent", None)
    details.base_rent = get(extracted_details, "base_rent", None)
    details.utility_prepayment = get(extracted_details, "utility_prepayment", None)
    details.heating_prepayment = get(extracted_details, "heating_prepayment", None)
    details.has_inclusive_utilities = get(
        extracted_details, "has_inclusive_utilities", False
    )
    details.deposit_amount = get(extracted_details, "deposit_amount", None)
    details.deposit_payment_method = get(
        extracted_details, "deposit_payment_method", None
    )
    details.has_stepped_rent = get(extracted_details, "has_stepped_rent", False)
    details.has_indexed_rent = get(extracted_details, "has_indexed_rent", False)
    details.rent_adjustment_terms = get(
        extracted_details, "rent_adjustment_terms", None
    )
    details.heating_type = get(extracted_details, "heating_type", None)
    details.utility_billing_method = get(
        extracted_details, "utility_billing_method", None
    )
    details.cosmetic_repairs_responsibility = get(
        extracted_details, "cosmetic_repairs_responsibility", None
    )
    details.small_repairs_responsibility = get(
        extracted_details, "small_repairs_responsibility", None
    )
    details.small_repairs_cost_limit = get(
        extracted_details, "small_repairs_cost_limit", None
    )
    details.pets_allowed = get(extracted_details, "pets_allowed", False)
    details.subletting_allowed = get(extracted_details, "subletting_allowed", False)
    details.subletting_requires_permission = get(
        extracted_details, "subletting_requires_permission", True
    )
    details.additional_occupants = get(extracted_details, "additional_occupants", None)
    details.rent_due_date = get(extracted_details, "rent_due_date", 3)
    details.landlord_bank_details = get(
        extracted_details, "landlord_bank_details", None
    )
    details.quiet_hours = get(extracted_details, "quiet_hours", None)

    contract_date = extracted_details.get("contract_date")
    details.contract_date = convert_date(contract_date) if contract_date else None

    details.contract_version = get(extracted_details, "contract_version", None)

    details.save()
    logger.info(f"Contract {contract.id} analyzed and details saved")


@login_required
def analyze_contract_update(request: WSGIRequest) -> StreamingHttpResponse:
    contract_id = request.GET.get("id")
    contract = get_object_or_404(
        Contract, id=contract_id, user=request.user
    )  # Add ownership check
    last_status = contract.status  # Store initial status

    def event_stream():
        nonlocal last_status
        max_duration = 300  # 5 minutes
        start_time = time.time()

        while time.time() - start_time < max_duration:
            contract.refresh_from_db()

            # Exit conditions
            if contract.status in ["analyzed", "error"]:
                yield f"data: {contract.status}\n\n"
                yield "event: close\ndata: Connection closed\n\n"
                break

            if contract.status != last_status:
                yield f"data: {contract.status}\n\n"
                last_status = contract.status

            time.sleep(0.5)

        # Close connection after timeout
        if time.time() - start_time >= max_duration:
            yield "event: close\ndata: Timeout\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
