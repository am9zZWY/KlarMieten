import base64
import json
import logging
import os
from io import BytesIO
from typing import Any

from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Load dotenv file
from dotenv import load_dotenv

load_dotenv()


def image_to_base64(image: Image.Image) -> str:
    """
    Converts a PIL Image to a base64 encoded string.
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")  # Or PNG, depending on your needs
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


json_scheme_contract_detail_extraction = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Housing Contract",
    "type": "object",
    "properties": {
        "contract_type": {
            "type": "string",
            "description": "The type of contract (e.g., Wohnraummietvertrag, lease agreement).",
        },
        "property_details": {
            "type": "object",
            "description": "Details about the rented property.",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The address of the rented property.",
                },
                "rooms": {
                    "type": "object",
                    "description": "Details about the rooms included in the rental.",
                    "properties": {
                        "number_of_rooms": {"type": "integer"},
                        "kitchen": {"type": "boolean"},
                        "bathroom": {"type": "boolean"},
                        "separate_wc": {"type": "boolean"},
                        "balcony_or_terrace": {"type": "boolean"},
                        "garden": {"type": "boolean"},
                        "garage_or_parking_space": {"type": "boolean"},
                    },
                },
                "shared_facilities": {
                    "type": "array",
                    "description": "List of shared facilities available to the tenant.",
                    "items": {"type": "string"},
                },
                "keys_provided": {
                    "type": "array",
                    "description": "List of keys provided to the tenant.",
                    "items": {"type": "string"},
                },
            },
        },
        "rental_terms": {
            "type": "object",
            "description": "Details about the rental terms.",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "The start date of the rental agreement.",
                },
                "end_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "The end date of the rental agreement, or null if indefinite.",
                },
                "duration": {
                    "type": "string",
                    "description": "The duration of the rental agreement (e.g., 'indefinite').",
                },
                "termination_terms": {
                    "type": "string",
                    "description": "Conditions and procedures for terminating the rental agreement.",
                },
            },
        },
        "pricing": {
            "type": "object",
            "description": "Details about the pricing and costs.",
            "properties": {
                "monthly_rent": {
                    "type": "number",
                    "description": "The monthly rent amount.",
                },
                "additional_costs": {
                    "type": "array",
                    "description": "List of additional costs (e.g., utilities, maintenance).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "amount": {"type": "number"},
                        },
                    },
                },
                "total_rent": {
                    "type": "number",
                    "description": "The total rent amount including additional costs.",
                },
            },
        },
        "heating_type": {
            "type": "string",
            "description": "The type of heating in the property (e.g., Einzelofen, Etagenheizung, Zentralheizung).",
        },
        "additional_clauses": {
            "type": "array",
            "description": "Any additional clauses or notes in the contract.",
            "items": {"type": "string"},
        },
        "paragraphs": {
            "type": "array",
            "description": "All paragraphs from the contract text.",
            "items": {"type": "string"},
        },
    },
    "required": [
        "contract_type",
        "property_details",
        "rental_terms",
        "pricing",
        "paragraphs",
    ],
}


def clean_gemini_json(json_string: str) -> Any | None:
    """
    Cleans a JSON string received from Gemini, ensuring it's valid JSON,
    and returns it as a Python dictionary.  Handles common issues like
    trailing commas, unescaped characters, and incorrect data types.

    Args:
        json_string: The JSON string to clean.

    Returns:
        A Python dictionary representing the cleaned JSON, or None if cleaning failed.
    """
    if not json_string:
        return None

    try:
        # Attempt to load the JSON string directly
        data = json.loads(json_string)
        return data  # If it loads without error, it's already valid.

    except json.JSONDecodeError as e:
        logger.error(f"Initial JSONDecodeError: {e}")

        # Attempt cleaning strategies:
        cleaned_string = json_string
        cleaned_string = cleaned_string.replace(",\n}", "\n}")
        cleaned_string = cleaned_string.replace(",\n]", "\n]")
        cleaned_string = cleaned_string.replace("'", '"')
        cleaned_string = cleaned_string.replace("```json", "")
        cleaned_string = cleaned_string.replace("```", "")
        cleaned_string = cleaned_string.replace("True", "true")
        cleaned_string = cleaned_string.replace("False", "false")
        cleaned_string = cleaned_string.replace("Null", "null")

        # 4. Try loading the cleaned string again
        try:
            data = json.loads(cleaned_string)
            return data
        except json.JSONDecodeError as e2:
            logger.error(f"Failed to clean JSON: {e2}")
            return None


def extract_details_with_gemini(image_paths: list[str]) -> tuple[dict[Any, Any], Any]:
    detail_extraction_prompt = (
        """
    You are a contract analysis expert.
    Your task is to analyze contract images and extract key information, organizing it into a JSON object that *strictly* conforms to the following schema description:
    """
        + json.dumps(json_scheme_contract_detail_extraction, indent=2)
        + """
    The JSON object should have the following keys:
    
    - **contract_type**: (String) The type of contract (e.g., lease agreement, service agreement).
    - **effective_date**: (String, ISO 8601 format) The date the contract becomes effective.
    - **term**: (String) The duration of the contract (start and end dates).
    - **renewal_terms**: (String) Information about renewal options.
    - **termination_terms**: (String) Conditions for termination.
        - **payment_terms**: (String) Payment schedules and penalties.
    - **obligations**: (String) Key obligations of each party.
    - **liabilities**: (String) Liabilities of each party.
    - **governing_law**: (String) The governing jurisdiction.
    - **dispute_resolution**: (String) How disputes will be resolved.
    - **price**: (Array of Objects) All pricing information (fees, rates, etc.) with descriptions. Each object in the array should have a "description" (String) and an "amount" (Number).
    - **paragraphs**: (Array of Strings) A list of all contract paragraphs.
    
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

    "Mietvertrag für Wohnraum
    zwischen Vermieter AG und Mieter Herr Mustermann
    Mietbeginn: 01.01.2025"
    
    **JSON Output:**
    
    ```json
    {{
      "contract_type": "Wohnraummietvertrag",
      "property_details": {{
        "address": null,
        "rooms": {{
          "number_of_rooms": 0,
          "kitchen": false,
          "bathroom": false,
          "separate_wc": false,
          "balcony_or_terrace": false,
          "garden": false,
          "garage_or_parking_space": false
        }},
        "shared_facilities": [],
        "keys_provided": []
      }},
      "rental_terms": {{
        "start_date": "2025-01-01",
        "end_date": null,
        "duration": null,
        "termination_terms": null
      }},
      "pricing": {{
        "monthly_rent": 0,
        "additional_costs": [],
        "total_rent": 0
      }},
      "heating_type": null,
      "additional_clauses": [],
      "paragraphs": []
    }}
    ```
    """
    )

    # Create the model
    logger.info("Creating Gemini client")
    logger.info(f"Image paths: {image_paths}")
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

    images = [Image.open(image_path) for image_path in image_paths]
    contents = [detail_extraction_prompt]
    contents.extend(images)

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
        response_json = clean_gemini_json(response_text)
    except Exception as e:
        logger.error(f"Failed to clean Gemini JSON: {e}")
        response_json = None

    if response_json is None:
        logger.warning("Failed to extract details with Gemini")
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
