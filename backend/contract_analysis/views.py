from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


# Create your views here.
def contract_analysis(request):
    template = loader.get_template("index.html")
    return HttpResponse(template.render(None, request))


@csrf_exempt
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
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": "Ungültige Anfrage."})
