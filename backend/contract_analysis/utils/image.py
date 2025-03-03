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
