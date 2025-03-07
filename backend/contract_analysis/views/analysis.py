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
from contract_analysis.models.contract import Contract, ContractDetails
from contract_analysis.utils.error import handle_exception, error_response

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
        logger.info(f"Token count after details extraction: {total_token_count}")

        # Analyze neighborhood based on extracted address
        logger.info("Analyzing neighborhood")
        # Create full address string and geocode
        street = extracted_details["street"] if extracted_details.get("street") else ""
        postal_code = (
            extracted_details["postal_code"]
            if extracted_details.get("postal_code")
            else ""
        )
        city = extracted_details["city"] if extracted_details.get("city") else ""
        country = (
            extracted_details["country"] if extracted_details.get("country") else ""
        )
        address = f"{street} {postal_code} {city} {country}"
        neighborhood, analysis_token_count = analyze_neighborhood_with_gemini(address)
        extracted_details["neighborhood_description"] = neighborhood
        total_token_count += analysis_token_count
        logger.info(f"Token count after neighborhood analysis: {total_token_count}")

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

    # Get existing contract details or create new ones
    created = False
    details = ContractDetails.objects.filter(contract=contract).first()
    if not details:
        details = ContractDetails.objects.create(contract=contract)
        created = True

    # Update fields with extracted information
    valid_fields = [f.name for f in ContractDetails._meta.fields]

    for key, value in extracted_details.items():
        if key in valid_fields:
            setattr(details, key, value)

    details.save()  # Only one database write
    logger.info(
        f"Contract {contract.id} analyzed and details saved (created: {created})"
    )


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
