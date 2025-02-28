# tasks.py
@shared_task
def process_contract_file(contract_file_id):
    contract_file = ContractFile.objects.get(id=contract_file_id)
    
    # Process file (convert PDF, resize image, etc.)
    processed_file_path = process_file(contract_file.original_file.path)
    
    # Update the model with processed file
    contract_file.processed_file = processed_file_path
    contract_file.save()
    
    return processed_file_path

# views.py
def upload_file(request):
    # Save original file
    contract_file = ContractFile.objects.create(
        contract=contract,
        original_file=file
    )
    
    # Queue processing task
    process_contract_file.delay(contract_file.id)
    
    return JsonResponse({"success": True})