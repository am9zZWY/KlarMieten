import base64
import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404

from contract_analysis.models import Contract, ContractDetails, ContractFile
from contract_analysis.utils.error import handle_exception, error_response

logger = logging.getLogger(__name__)


# Create your views here.
def landing(request):
    logger.info("Rendering landing page")
    return render(request, "landing.html")


@login_required
def home(request):
    logger.info(f"Rendering home page for user {request.user}")
    contracts = Contract.objects.filter(user=request.user, archived=False)
    return render(request, "contract/home.html", {"contracts": contracts})


@login_required
def get_contract(request, contract_id):
    # Try to get from cache first
    cache_key = f"contract_{contract_id}_{request.user.id}"
    cached_data = cache.get(cache_key)

    # if cached_data:
    #    return render(request, "contract/contract.html", cached_data)

    # Get from database
    contract = get_object_or_404(
        Contract, id=contract_id, user=request.user, archived=False
    )
    contract_details = ContractDetails.objects.filter(contract=contract).first()

    # Cache for 10 minutes
    context = {"contract": contract, "contract_details": contract_details}
    cache.set(cache_key, context, 60 * 10)

    return render(request, "contract/contract.html", context)


@login_required
def get_contract_file(request, contract_id, file_id):
    """Serve encrypted file contents from database"""
    logger.info(f"Accessing contract file {file_id} for contract {contract_id}")

    contract = get_object_or_404(Contract, id=contract_id, user=request.user)
    contract_file = get_object_or_404(ContractFile, id=file_id, contract=contract)

    if contract_file.encrypted_content is None:
        return error_response("File not found", status=404)

    # Decrypt the file
    try:
        file_content = contract_file.get_file_content()
        return HttpResponse(file_content, content_type=contract_file.file_type)
    except ValueError as e:
        return error_response("Error accessing file", status=500)


@login_required
def edit_contract(request, contract_id):
    """
    View for editing a contract
    """
    # Remove duplicate logging statement
    logger.info(f"Editing contract {contract_id} for user {request.user}")
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)

    context = {
        "contract": contract,
    }

    return render(request, "contract/edit.html", context)


@login_required
def save_edited_contract(request, contract_id):
    """
    AJAX endpoint to save a censored contract image
    """

    # Check if the request is a POST request
    if request.method != "POST":
        return error_response("Invalid request method", status=405)

    file_id = request.POST.get("file_id")
    censored_image = request.POST.get("censored_image")

    if not file_id or not censored_image:
        return error_response("Missing required data", status=400)

    try:
        # Get the contract file and verify ownership
        contract = get_object_or_404(Contract, id=contract_id, user=request.user)
        contract_file = get_object_or_404(ContractFile, id=file_id)
        if (
            contract_file.contract.user != request.user
            or contract_file.contract.id != contract.id
        ):
            return error_response("Invalid contract file", status=403)

        # Process the data URL
        if "," in censored_image:
            file_content = base64.b64decode(censored_image.split(",")[1])
            contract_file.set_file_content(file_content)
            contract_file.save()
            return JsonResponse({"success": True})
        else:
            return error_response("Invalid data URL format", status=400)

    except Exception as e:
        return handle_exception(e)


@login_required
def archive_contract(request, contract_id):
    from django.utils import timezone

    # Check if the request is a POST request
    if request.method != "POST":
        return error_response("Invalid request method", status=405)

    logger.info(f"Archiving contract {contract_id} for user {request.user}")

    # Get the contract and verify ownership
    contract = get_object_or_404(Contract, id=contract_id, user=request.user)

    # Archive instead of delete
    contract.archived = True
    contract.archived_date = timezone.now()
    contract.save()

    return JsonResponse({"success": True})
