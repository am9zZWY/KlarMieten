from django.contrib.auth.decorators import login_required
from django.http.response import JsonResponse

from contract_analysis.models.chat import ChatMessage


@login_required
def chat(request):
    # Check if POST request
    if request.method == "POST":
        # Get the message from the POST request
        message = request.POST.get("message", "")
        # Get the user from the request
        user = request.user

        if not user.is_authenticated:
            return JsonResponse({"error": "User is not authenticated."}, status=403)

        # Check if user is authenticated and has permission to chat
        has_chat_permission = user.has('unlimited_chat')
        if not has_chat_permission:
            return JsonResponse({"error": "User does not have permission to chat. Please upgrade your plan."}, status=403)

        # Create and save the chat message
        ChatMessage.objects.create(user=user, message=message)

        # TODO: Make API call to chatbot and get response

        response = "Chatbot response"

        # Return the response
        return JsonResponse({"message": response})
