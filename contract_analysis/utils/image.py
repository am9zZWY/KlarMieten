import base64
import io
import logging
from io import BytesIO

from PIL import Image
from django.core.exceptions import ValidationError
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)


def convert_pdf_to_images(file, contract):
    """Convert PDF to images and save them as contract files."""
    try:
        images = convert_from_bytes(file.read(), dpi=200, thread_count=4, fmt="png")
        base_name = file.name.split(".")[0]

        for i, img in enumerate(images):
            # Reduce image size and save to buffer
            resized_img = reduce_image_size(img, percent=35)
            buffer = io.BytesIO()
            resized_img.save(buffer, format="PNG")
            buffer.seek(0)

            page_filename = f"{base_name}_page_{i + 1}.png"
            contract.add_file(page_filename, buffer.getvalue(), "image/png")

    except Exception as e:
        logger.error(f"PDF conversion error: {e}")
        raise ValidationError("Fehler bei der PDF-Konvertierung")


def image_to_base64(image: Image.Image) -> str:
    """
    Converts a PIL Image to a base64 encoded string.
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")  # Or PNG, depending on your needs
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def reduce_image_size(image: Image.Image, percent: int = 50) -> Image.Image:
    """
    Reduces image dimensions by specified percentage while maintaining an aspect ratio.
    Example: 1000x2000 image at 20% will become 200x400.
    """
    new_size = (int(image.width * percent / 100), int(image.height * percent / 100))
    return image.resize(new_size, Image.Resampling.LANCZOS)
