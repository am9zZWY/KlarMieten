import base64
import json
from io import BytesIO
from typing import Any

import google.generativeai as genai
from PIL import Image

# Configure the Gemini API
genai.configure(api_key="")


def image_to_base64(image: Image.Image) -> str:
    """
    Converts a PIL Image to a base64 encoded string.
    """
    buffered = BytesIO()
    image.save(buffered, format="JPEG")  # Or PNG, depending on your needs
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return img_str


json_scheme_contract_detail_extraction = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Housing Contract",
    "type": "object",
    "properties": {
        "contract_type": {
            "type": "string",
            "description": "The type of contract (e.g., Wohnraummietvertrag, lease agreement)."
        },
        "property_details": {
            "type": "object",
            "description": "Details about the rented property.",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The address of the rented property."
                },
                "rooms": {
                    "type": "object",
                    "description": "Details about the rooms included in the rental.",
                    "properties": {
                        "number_of_rooms": { "type": "integer" },
                        "kitchen": { "type": "boolean" },
                        "bathroom": { "type": "boolean" },
                        "separate_wc": { "type": "boolean" },
                        "balcony_or_terrace": { "type": "boolean" },
                        "garden": { "type": "boolean" },
                        "garage_or_parking_space": { "type": "boolean" }
                    }
                },
                "shared_facilities": {
                    "type": "array",
                    "description": "List of shared facilities available to the tenant.",
                    "items": { "type": "string" }
                },
                "keys_provided": {
                    "type": "array",
                    "description": "List of keys provided to the tenant.",
                    "items": { "type": "string" }
                }
            }
        },
        "rental_terms": {
            "type": "object",
            "description": "Details about the rental terms.",
            "properties": {
                "start_date": {
                    "type": "string",
                    "format": "date",
                    "description": "The start date of the rental agreement."
                },
                "end_date": {
                    "type": ["string", "null"],
                    "format": "date",
                    "description": "The end date of the rental agreement, or null if indefinite."
                },
                "duration": {
                    "type": "string",
                    "description": "The duration of the rental agreement (e.g., 'indefinite')."
                },
                "termination_terms": {
                    "type": "string",
                    "description": "Conditions and procedures for terminating the rental agreement."
                }
            }
        },
        "pricing": {
            "type": "object",
            "description": "Details about the pricing and costs.",
            "properties": {
                "monthly_rent": {
                    "type": "number",
                    "description": "The monthly rent amount."
                },
                "additional_costs": {
                    "type": "array",
                    "description": "List of additional costs (e.g., utilities, maintenance).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": { "type": "string" },
                            "amount": { "type": "number" }
                        }
                    }
                },
                "total_rent": {
                    "type": "number",
                    "description": "The total rent amount including additional costs."
                }
            }
        },
        "heating_type": {
            "type": "string",
            "description": "The type of heating in the property (e.g., Einzelofen, Etagenheizung, Zentralheizung)."
        },
        "additional_clauses": {
            "type": "array",
            "description": "Any additional clauses or notes in the contract.",
            "items": { "type": "string" }
        },
        "paragraphs": {
            "type": "array",
            "description": "All paragraphs from the contract text.",
            "items": { "type": "string" }
        }
    },
    "required": ["contract_type", "property_details", "rental_terms", "pricing", "paragraphs"]
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
    try:
        # Attempt to load the JSON string directly
        data = json.loads(json_string)
        return data  # If it loads without error, it's already valid.

    except json.JSONDecodeError as e:
        print(f"Initial JSONDecodeError: {e}")

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
            print(f"Cleaning failed. Second JSONDecodeError: {e2}")
            print(f"Problematic JSON String: {cleaned_string}")  # Print the string for debugging
            return None


def extract_details_with_gemini(image_path: str) -> dict:
    def upload_to_gemini(path, mime_type=None):
        """Uploads the given file to Gemini.

        See https://ai.google.dev/gemini-api/docs/prompting_with_media
        """
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file

    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-preview-02-05",
        generation_config=generation_config,
    )

    # TODO Make these files available on the local file system
    # You may need to update the file paths
    files = [
        upload_to_gemini(image_path, mime_type="image/jpeg"),
    ]

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    files[0],
                ],
            },
        ]
    )

    response = chat_session.send_message(
        """
You are a contract analysis expert. Your task is to extract key information from a contract provided as plain text and output it as a JSON object. The JSON object must conform to the following JSON Schema:
""" + str(json_scheme_contract_detail_extraction) + """
Here are the requirements:
1.  **No Personal Information:** Do not include any personal or contact information such as names, phone numbers, email addresses, or signatures. Include the address of the property, including the city and postal code.
2.  **Pricing Information:** Extract all pricing information (e.g., fees, rates, costs, payments, discounts, taxes) and include it under the "price" key. Each price should have a description.
3.  **Paragraphs:** Extract all paragraphs of the contract and include them in a list under the "paragraphs" key.
4.  **Key Sections:** Identify and extract information related to the following key sections (if present):
    *   "contract_type": The type of contract (e.g., lease agreement, service agreement, sales agreement).
    *   "effective_date": The date the contract becomes effective.
    *   "term": The duration or term of the contract (start and end dates, or length of time).
    *   "renewal_terms": Information about contract renewal options and conditions.
    *   "termination_terms": Conditions and procedures for contract termination.
    *   "payment_terms": Details about payment schedules, methods, and any late payment penalties.
    *   "obligations": A summary of the key obligations of each party involved.
    *   "liabilities": A summary of the liabilities of each party involved.
    *   "governing_law": The jurisdiction whose laws govern the contract.
    *   "dispute_resolution": How disputes will be resolved (e.g., arbitration, mediation, litigation).
5.  **Additional Keys:** Feel free to add more keys as you deem necessary to capture relevant information from the contract.
6.  **JSON Output:** The output must be a valid JSON object. Ensure proper formatting, including quotation marks around keys and string values, and commas between key-value.

Output the extracted information as a JSON object
        """
    )
    print("Response:", response.text)

    response_text = response.text
    response_json = clean_gemini_json(response_text)
    if response_json is None:
        return {}

    return response_json


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
