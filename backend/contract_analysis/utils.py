import logging

from darf_vermieter_das.settings import FILE_UPLOAD_MAX_MEMORY_SIZE
import magic
from datetime import datetime
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

def get_nested(data, keys, default=None):
    """
    Safely retrieves a nested value from a dictionary using a list of keys.
    Returns the default value if any key is not found.
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def convert_date(date_str):
    """
    Converts a date string in the format "YYYY-MM-DD" to a datetime object.
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def validate_file_type(file):
    """
    Validates that the uploaded file is a PDF document or an image.
    """
    
    # magic checks the first 1024 bytes of the file to determine the file type
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    print(f"Filetype of contract file: {file_mime}")
    if file_mime != 'application/pdf' and not file_mime.startswith('image/'):
        raise ValidationError('Die Datei muss ein PDF-Dokument oder ein Bild sein.')
    # Reset the file pointer to the beginning
    file.seek(0)

def validate_file_size(file):
    """
    Validates that the uploaded file is not larger than 10MB.
    """
    # Check if the file size is greater than 10MB
    if file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
        raise ValidationError('Die Datei darf nicht größer als 10MB sein.')
