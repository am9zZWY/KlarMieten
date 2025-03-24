import base64
import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from contract_analysis.models.contract import Contract, ContractDetails, ContractFile
from contract_analysis.utils.error import handle_exception, error_response
from contract_analysis.utils.map import geocode_address
from mietkai.faq import FAQ_pricing

logger = logging.getLogger(__name__)


def pricing(request):
    """
    Pricing page view for non-authenticated users.

    Args:
        request: HttpRequest object

    Returns:
        Rendered pricing page
    """
    context = {
        "faq": FAQ_pricing
    }
    return render(request, "pricing.html", context)


@login_required
def home_view(request):
    """
    Home page view displaying active contracts for the authenticated user.

    Args:
        request: HttpRequest object

    Returns:
        Rendered home page with user's active contracts
    """
    contracts = Contract.objects.filter(user=request.user, archived=False)
    return render(request, "contract/home.html", {"contracts": contracts})


@login_required
def get_contracts(request):
    """
    AJAX endpoint to get all contracts for the authenticated user.

    Args:
        request: HttpRequest object

    Returns:
        JsonResponse with list of contracts
    """
    contracts = Contract.objects.filter(user=request.user, archived=False)
    return JsonResponse({"contracts": contracts})


@login_required
def contract_view(request, contract_id):
    """
    View for displaying contract details with location information.
    Uses caching to improve performance for frequently accessed contracts.

    Args:
        request: HttpRequest object
        contract_id: ID of the requested contract

    Returns:
        Rendered contract detail view or 404 if not found
    """
    # Try to get from cache first
    cache_key = f"contract_{contract_id}_{request.user.id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return render(request, "contract/contract.html", cached_data)

    # Get from the database
    contract = get_object_or_404(
        Contract, id=contract_id, user=request.user, archived=False
    )
    contract_details = ContractDetails.objects.filter(contract=contract).first()
    if not contract_details:
        return HttpResponseNotFound("Contract details not found")

    # Create full address string and geocode
    address_parts = [
        contract_details.street or "",
        contract_details.postal_code or "",
        contract_details.city or "",
        "Germany"  # Default country
    ]
    address = " ".join(filter(None, address_parts))
    location = geocode_address(address)

    # Cache for 10 minutes
    context = {
        "contract": contract,
        "contract_details": contract_details,
        "location": location,
    }
    cache.set(cache_key, context, 60 * 10)

    return render(request, "contract/contract.html", context)


@login_required
def get_contract_file(request, contract_id, file_id):
    """
    Serve encrypted file contents from database.

    Args:
        request: HttpRequest object
        contract_id: ID of the contract
        file_id: ID of the file to retrieve

    Returns:
        HttpResponse with file content or error response
    """
    logger.info(f"Accessing contract file {file_id} for contract {contract_id}")

    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    contract_file = get_object_or_404(ContractFile, id=file_id, contract=contract)

    if contract_file.encrypted_content is None:
        return error_response("File not found", status=404)

    try:
        file_content = contract_file.get_file_content()
        return HttpResponse(file_content, content_type=contract_file.file_type)
    except ValueError:
        return error_response("Error accessing file", status=500)


@login_required
def edit_contract(request, contract_id):
    """
    View for editing a contract.

    Args:
        request: HttpRequest object
        contract_id: ID of the contract to edit

    Returns:
        Rendered contract edit page
    """
    logger.info(f"Editing contract {contract_id} for user {request.user}")
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)

    return render(request, "contract/edit.html", {"contract": contract})


@login_required
@require_http_methods(["POST"])
def save_edited_contract(request, contract_id):
    """
    AJAX endpoint to save a censored contract image.

    Args:
        request: HttpRequest object
        contract_id: ID of the contract being edited

    Returns:
        JsonResponse with success status or error response
    """
    file_id = request.POST.get("file_id")
    censored_image = request.POST.get("censored_image")

    if not file_id or not censored_image:
        return error_response("Missing required data", status=400)

    try:
        # Get the contract file and verify ownership
        contract = get_object_or_404(Contract, id=contract_id, user=request.user)
        contract_file = get_object_or_404(ContractFile, id=file_id, contract=contract)

        # Process the data URL
        if "," in censored_image:
            file_content = base64.b64decode(censored_image.split(",")[1])
            contract_file.set_file_content(file_content)
            contract_file.save()

            # Invalidate any cached versions of this contract
            cache_key = f"contract_{contract_id}_{request.user.id}"
            cache.delete(cache_key)

            return JsonResponse({"success": True})
        else:
            return error_response("Invalid data URL format", status=400)

    except Exception as e:
        return handle_exception(e)


@login_required
@require_http_methods(["POST"])
def archive_contract(request, contract_id):
    """
    Archive a contract instead of deleting it.

    Args:
        request: HttpRequest object
        contract_id: ID of the contract to archive

    Returns:
        JsonResponse with success status
    """
    logger.info(f"Archiving contract {contract_id} for user {request.user}")

    # Get the contract and verify ownership
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)

    # Archive instead of delete
    contract.archived = True
    contract.archived_date = timezone.now()
    contract.save()

    # Invalidate any cached versions of this contract
    cache_key = f"contract_{contract_id}_{request.user.id}"
    cache.delete(cache_key)

    return JsonResponse({"success": True})
