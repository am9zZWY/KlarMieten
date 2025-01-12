from PIL import Image
import os

import cv2

base_path = "../data/"


def get_pil_contract(contract: str, page: int) -> Image:
    """
    Load and preprocess image.
    """

    # Check if the image exists
    image_path = f"{base_path}contract{contract}_{page}.jpg"
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image {image_path} not found.")

    im = Image.open(image_path)

    if im.mode != "L":
        im = im.convert("L")

    return im


def get_cv2_contract(contract: str, page: int):
    """
    Load and preprocess image.
    """

    # Check if the image exists
    image_path = f"{base_path}contract{contract}_{page}.jpg"
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image {image_path} not found.")

    return cv2.imread(image_path)


def to_data_path(path: str) -> str:
    """
    Convert contract and page to a data path.
    """

    return f"{base_path}{path}"


def split_into_rows(im: Image, num_rows: int):
    """
    Split the image into multiple regions.
    Thanks to https://stackoverflow.com/a/58477722 for providing the code
    """

    # Split the image in multiple regions
    y = 0
    row_height = im.height / num_rows
    while y < im.height:
        top_left = (0, y)
        bottom_right = (im.width, min(y + row_height, im.height))
        yield im.crop((*top_left, *bottom_right))

        y += row_height
