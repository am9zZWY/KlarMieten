import json
import logging
import os
from typing import Any

from PIL import Image
from google import genai
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
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=2.0, top_p=0.9, top_k=64, max_output_tokens=8192
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
    
    1.  Do not include personal contact information (names, phone numbers, emails, signatures). Include the property address (city, postal code).
    2.  Extract all pricing details with descriptions and format them correctly in the "price" array.
    3.  Extract all paragraphs and include them in the "paragraphs" array.
    4.  Identify and extract information for the key sections listed above.
    5.  Do not recite any training data or model information.
    6.  If a section is not present or not extractable, leave it as null or an empty string.
    7.  Do not include any legal advice or interpretation.
    8.  Do not include any links or references to external resources.
    
    
    Here are a few examples:
    
    **Contract Snippet:**

    "Wohnraummietvertrag
    zwischen Vermieter AG und Mieter Herr Mustermann
    Mietbeginn: 01.01.2025
    Addresse: Derendinger Straße. 62 Whg. Nr. 13, 72072 Tübingen
    3 Zimmer, Küche, Bad
    Miete: 1000 EUR pro Monat
    Keine Haustiere erlaubt"
    
    **JSON Output:**
    
    ```json
    {{
        "contract_type": "Wohnraummietvertrag",
        "address": "Derendinger Straße. 62, 72072 Tübingen",
        "city": "Tübingen",
        "postal_code": "72072",
        "country": "Germany",
        "number_of_rooms": "3",
        "kitchen": "true",
        "bathroom": "true",
        "separate_wc": "false",
        "balcony_or_terrace": "false",
        "garden": "false",
        "property_type": "Wohnung",
        "floor": "",
        "start_date": "01.01.2025",
        "total_rent": "1000",
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
            temperature=1.0, top_p=0.9, top_k=64, max_output_tokens=8192
        ),
    )

    usage_metadata = response.usage_metadata
    total_token_count = usage_metadata.total_token_count

    response_text = response.text
    try:
        response_json = clean_json(response_text)
    except Exception as e:
        logger.error(f"Failed to clean Gemini JSON: {e}")
        response_json = None

    if response_json is None:
        logger.warning("Failed to extract details with Gemini")
        logger.warning(f"Gemini response: {response}")
        return {}, total_token_count

    logger.info("Successfully extracted details with Gemini")
    return response_json, total_token_count


prompt = (
    "AUFGABE:\n"
    "Du bist ein freundlicher Erklärer für Mietverträge.\n"
    "Erkläre Mietvertragstexte so, als würdest du sie einem Freund erklären.\n"
    "WICHTIG:\n"
    "- Erst Grundregel, dann Details\n"
    "- 'Du'-Form verwenden\n"
    "- Ein Gedanke pro Absatz\n"
    "- Alltagssprache\n"
    "- Kurze Sätze\n"
    "- Keine nummerierten Aufzählungen\n"
    "VERBOTEN:\n"
    "- Keine Formatierung\n"
    "- Keine Rechtsberatung\n"
    "- Keine Fragen beantworten\n"
    "- Nur Mietvertragsthemen\n"
    "Bei Nicht-Mietvertragstext: 'Nicht verarbeitbar'\n"
    f"Legal text: {"test"}\n\nSimplify this text in plain German:"
)
