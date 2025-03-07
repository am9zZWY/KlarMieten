import json
import logging
import os
from typing import Any

from PIL import Image
from google import genai
from contract_analysis.utils.map import get_neighborhood_map
from google.genai import types

from contract_analysis.models import ContractDetails
from contract_analysis.utils.json import model_to_json_schema, clean_json

logger = logging.getLogger(__name__)

# Load dotenv file
from dotenv import load_dotenv

load_dotenv()

text_extraction_prompt = """
    You are an expert system for extracting raw text from images.
    Your task is to extract all text present in the image, including any visible characters, numbers, symbols, and punctuation.
    
    **Requirements:**
    
    1.  Extract ALL alphanumeric characters, symbols, and punctuation marks visible in the image, preserving their original order and spacing as accurately as possible.
    2.  Do NOT add any text that is not directly visible in the image.
    3.  Do NOT interpret, summarize, or paraphrase the text.
    4.  Do NOT provide any legal advice or analysis.
    5.  Do NOT attempt to understand the meaning of the text.
    6.  Do NOT translate the text.
    7.  Do NOT stop generating text unless the image is completely processed.
    8.  Output the extracted text as a single, continuous string.
    """


def extract_text_with_gemini(image_paths: list[str]) -> tuple[str, Any]:
    # Create the model
    logger.info("Creating Gemini client")
    logger.info(f"Image paths: {image_paths}")
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

    images = [Image.open(image_path) for image_path in image_paths]
    contents = [text_extraction_prompt]
    contents.extend(images)

    # Generate content with the model
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.9, top_p=0.9, top_k=64, max_output_tokens=8192
        ),
    )

    usage_metadata = response.usage_metadata
    total_token_count = usage_metadata.total_token_count

    response_text = response.text
    if response_text is None:
        logger.warning("Failed to extract text with Gemini")
        logger.warning(f"Gemini response: {response}")
        return {}, total_token_count

    logger.info("Successfully extracted text with Gemini")
    return response_text, total_token_count


json_scheme = model_to_json_schema(ContractDetails)


def extract_details_with_gemini(
    contract_text: str = None, contract_images: list[str] = None
) -> tuple[dict, int]:
    detail_extraction_prompt = (
        """
    You are a contract analysis expert.
    Your task is to analyze the contract and extract key information, organizing it into a JSON object that *strictly* conforms to the following schema description:
    """
        + json.dumps(json_scheme, indent=2)
        + """
    The JSON object should have the following keys:
    
    **Requirements:**
    
    1. Do not include personal contact information (names, phone numbers, emails, signatures). Include the property address (city, postal code).
    2. Extract all pricing details with descriptions and format them correctly in the "price" array.
    3. Extract all paragraphs and include them in the "paragraphs" array.
    4. Identify and extract information for the key sections listed above.
    5. Do not recite any training data or model information.
    6. If a section is not present or not extractable, leave it as null or an empty string.
    7. Do not include any legal advice or interpretation.
    8. Do not include any links or references to external resources.
    9. Try to be as accurate as possible in your extraction.
    
    
    Here are a few examples:
    
    **Contract Snippet:**

    "Wohnraummietvertrag
    zwischen Vermieter AG und Mieter Herr Mustermann
    Mietbeginn: 01.01.2025
    Addresse: Derendingerstr. 62 Whg.Nr. 13, 72072 Tübingen
    3 Zimmer, Küche, Bad
    Gartenanteil
    Miete: 1000 EUR pro Monat
    Betriebskosten: Werden direkt mit dem Lieferanten abgerechnet
    Keine Haustiere erlaubt"
    
    **JSON Output:**
    
    ```json
    {{
        "contract_type": "Wohnraummietvertrag",
        "address": "Derendingerstr. 62",
        "city": "Tübingen",
        "postal_code": "72072",
        "country": "Germany",
        "number_of_rooms": "3",
        "kitchen": "true",
        "bathroom": "true",
        "separate_wc": "false",
        "balcony_or_terrace": "false",
        "garden": "true",
        "property_type": "Wohnung",
        "floor": "",
        "start_date": "01.01.2025",
        "monthly_rent": "1000",
        "additional_costs": "Betriebskosten werden direkt mit dem Lieferanten abgerechnet",
        "pets_allowed": "false",
    }}
    ```
    """
    )

    # Create the model
    logger.info("Creating Gemini client")
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

    contents = [detail_extraction_prompt]
    if contract_images:
        images = [Image.open(image_path) for image_path in contract_images]
        contents.extend(images)
    if contract_text:
        contents.extend([contract_text])

    # Generate content with the model
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=1.5, top_p=0.9, top_k=64, max_output_tokens=8192, 
        ),
    )

    usage_metadata = response.usage_metadata
    total_token_count = usage_metadata.total_token_count

    response_text = response.text
    try:
        response_json = clean_json(response_text)
        logger.info(f"Cleaned Gemini JSON: {response_json}")
    except Exception as e:
        logger.error(f"Failed to clean Gemini JSON: {e}")
        response_json = None

    if response_json is None:
        logger.warning("Failed to extract details with Gemini")
        logger.warning(f"Gemini response: {response}")
        return {}, total_token_count

    logger.info("Successfully extracted details with Gemini")
    return response_json, total_token_count


neighborhood_analysis_prompt = """
    You are a real estate expert analyzing the neighborhood of a property.
    Your task is to provide a short analysis of the neighborhood based on the map image provided.

    If you see any specific features or landmarks in the neighborhood, please describe them in detail.
    For example, if there is a large street, you could mention that it might be a busy area and thus could be noisy.
    If there is a park nearby, you could mention that it provides a green space for residents to relax.
    If there is a police station or hospital nearby, you could mention that it provides safety and convenience for residents but might also lead to more noise due to sirens.

    **Requirements:**

    1. Describe the neighborhood based on the map image provided.
    2. Mention any specific features or landmarks that you see.
    3. Provide a brief analysis of how these features might impact the property or its residents.
    4. Do not provide any personal opinions or biases.
    5. Do not provide any legal advice or analysis.
    6. Do not provide any information about the property itself, only the neighborhood.
    7. Do not provide any information about the property owner or residents.
    8. Answer in complete sentences and use proper grammar and punctuation.
    9. Answer only in German.
"""

def analyze_neighborhood_with_gemini(address: str) -> tuple[str, int]:
    """Analyze the neighborhood of a given address"""
    image =  get_neighborhood_map(address)

    if image is None:
        logger.error("Failed to fetch neighborhood map")
        return None, 0
    
    # Create the model
    logger.info("Creating Gemini client")
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

    contents = [neighborhood_analysis_prompt, image]

    # Generate content with the model
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.5, top_p=0.9, top_k=64, max_output_tokens=8192, 
        ),
    )

    usage_metadata = response.usage_metadata
    total_token_count = usage_metadata.total_token_count

    response_text = response.text

    logger.info("Successfully analyzed neighborhood with Gemini")
    return response_text, total_token_count
