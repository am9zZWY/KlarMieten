import logging
from datetime import datetime

import magic
from PIL import Image
from django.core.exceptions import ValidationError

from darf_vermieter_das.settings import FILE_UPLOAD_MAX_MEMORY_SIZE

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


def validate_image_type(file):
    """
    Validates that the uploaded file is a PDF document or an image.
    """

    # magic checks the first 1024 bytes of the file to determine the file type
    file_mime = magic.from_buffer(file.read(1024), mime=True)
    print(f"Filetype of contract file: {file_mime}")
    if file_mime != "application/pdf" and not file_mime.startswith("image/"):
        raise ValidationError("Die Datei muss ein PDF-Dokument oder ein Bild sein.")
    # Reset the file pointer to the beginning
    file.seek(0)


def compress_image(image_path, output_path, quality=75, max_size=None):
    """
    Compresses an image file to reduce its size while maintaining reasonable quality.

    Args:
        image_path: Path to the input image file.
        output_path: Path to save the compressed image.
        quality: Compression quality (0-100, higher is better quality). [[2]] [[8]]
        max_size: Tuple (width, height) for maximum image dimensions.  Resizes if larger. [[6]] [[10]]
    """
    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return

    if max_size:
        img = img.thumbnail(max_size, Image.Resampling.LANCZOS)[[10]]

    try:
        img.save(output_path, optimize=True, quality=quality)
    except Exception as e:
        print(f"Error saving image: {e}")


def validate_file_size(file):
    """
    Validates that the uploaded file is not larger than 10MB.
    """
    # Check if the file size is greater than 10MB
    if file.size > FILE_UPLOAD_MAX_MEMORY_SIZE:
        raise ValidationError("Die Datei darf nicht größer als 10MB sein.")
