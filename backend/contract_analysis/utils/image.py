import base64
from io import BytesIO

from PIL import Image


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
