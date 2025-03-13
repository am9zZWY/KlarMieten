import logging
import requests
from PIL import Image
from io import BytesIO
import math
import time

USER_AGENT = "Darf Vermieter Das/1.0 (josef.mueller@student.uni-tuebingen.de) This is for testing purposes only. I want to provide AI-based contract analysis."

logger = logging.getLogger(__name__)


def geocode_address(address):
    """Geocode address on the server side"""
    encoded_address = address.replace(" ", "+")
    nominatim_url = f"https://nominatim.openstreetmap.org/search.php?q={encoded_address}&format=jsonv2"

    headers = {"User-Agent": USER_AGENT}

    try:
        # Include headers in the request
        response = requests.get(nominatim_url, headers=headers)
        data = response.json()

        if data and len(data) > 0:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
            }
    except Exception as e:
        print(f"Error geocoding address: {e}")

    return None


def get_neighborhood_map(
    address: str, zoom: int = 16, width_px: int = 800, height_px: int = 600
) -> Image.Image:
    """Fetch OSM map image for an address with proper API etiquette."""
    location = geocode_address(address)
    if location is None:
        logger.error(f"Failed to geocode address {address}")
        return None

    # Convert lat/lon to tile coordinates
    lat, lon = location["lat"], location["lon"]

    # Calculate tile coordinates
    n = 2**zoom
    x_tile = int((lon + 180) / 360 * n)
    y_tile = int(
        (
            1
            - math.log(math.tan(math.radians(lat)) +
                       1 / math.cos(math.radians(lat)))
            / math.pi
        )
        / 2
        * n
    )

    # Calculate pixels within the tile
    x_pixel = int(((lon + 180) / 360 * n - x_tile) * 256)
    y_pixel = int(
        (
            (
                1
                - math.log(
                    math.tan(math.radians(lat)) + 1 /
                    math.cos(math.radians(lat))
                )
                / math.pi
            )
            / 2
            * n
            - y_tile
        )
        * 256
    )

    # Determine tiles needed for the requested image size
    tiles_x = int(math.ceil(width_px / 256)) + 1
    tiles_y = int(math.ceil(height_px / 256)) + 1

    # Calculate the starting tile
    start_x = x_tile - int(tiles_x / 2)
    start_y = y_tile - int(tiles_y / 2)

    # Create a blank image for the result
    result_img = Image.new("RGB", (tiles_x * 256, tiles_y * 256))

    headers = {
        "User-Agent": USER_AGENT,
    }

    # Fetch tiles and combine them
    for x in range(tiles_x):
        for y in range(tiles_y):
            tile_x = start_x + x
            tile_y = start_y + y

            # Ensure tile coordinates are valid
            if tile_x < 0 or tile_y < 0 or tile_x >= n or tile_y >= n:
                continue

            tile_url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"

            try:
                # Respect OSM usage policy with a small delay between requests
                time.sleep(0.1)
                response = requests.get(tile_url, headers=headers, timeout=5)
                response.raise_for_status()
                tile_img = Image.open(BytesIO(response.content))
                result_img.paste(tile_img, (x * 256, y * 256))
            except Exception as e:
                logger.error(f"Error fetching map tile {tile_url}: {e}")

    # Crop the result to requested size, centered on the target location
    center_x = (tiles_x * 256) // 2
    center_y = (tiles_y * 256) // 2
    left = center_x - (width_px // 2)
    top = center_y - (height_px // 2)
    cropped_img = result_img.crop(
        (left, top, left + width_px, top + height_px))

    return cropped_img
