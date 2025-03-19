import asyncio
import base64
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Optional

from PIL import Image
from asgiref.sync import sync_to_async
from google import genai
from google.cloud import vision
from google.genai import types as genai_types
from mistralai import Mistral

from contract_analysis.models.contract import ContractDetails, Contract
from contract_analysis.utils.json import clean_json, model_to_schema
from contract_analysis.utils.map import get_neighborhood_map

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# API keys and clients
GEMINI_API_KEY = os.getenv("GENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GCP_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Model constants
MISTRAL_OCR_MODEL = "mistral-ocr-latest"
MISTRAL_SMALL_MODEL = "mistral-small"
GEMINI_FLASH_MODEL = "gemini-2.0-flash"
GEMINI_FLASH_EXP_MODEL = "gemini-2.0-flash-exp"

# Initialize clients
MISTRAL_CLIENT = Mistral(api_key=MISTRAL_API_KEY)
GEMINI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
VISION_CLIENT = vision.ImageAnnotatorClient()

# In-memory cache
OCR_CACHE = {}

# Prompts
SIMPLIFICATION_PROMPT = """
Es liegt ein Mietvertrag vor. Dieser enthält Paragraphen, die mit § oder einer entsprechenden Überschrift gekennzeichnet sind. Nur diese Paragraphen sollen vereinfacht werden. Teile des Textes ohne Paragraphen-Bezug werden ignoriert. 

Sämtliche persönlichen Daten wie Namen, Adressen, IBAN, Telefonnummern oder E-Mail-Adressen sind zu entfernen. 

Die Zusammenfassung erfolgt ausschließlich in deutscher Sprache. Rechtsbegriffe sollen in kurzen Sätzen und ohne komplizierten Fachjargon erklärt werden. Dabei bleiben die rechtlich relevanten Informationen erhalten. 

Es finden keine wörtlichen Zitate aus dem Originalvertrag statt. Diese Zusammenfassung ist nur eine verständliche Darstellung und keine Rechtsberatung. 

Die Ausgabe erfolgt als JSON-Array. Jeder Eintrag enthält:
[
  {
    "title": "Kurze Überschrift zu §1 oder ähnlichem",
    "simplified": "Kurze Erläuterung zum Inhalt dieses Paragraphen"
  },
  {
    "title": "Kurze Überschrift zu §2 oder ähnlichem",
    "simplified": "Kurze Erläuterung zum Inhalt dieses Paragraphen"
  }
]

"title" ist eine Ein- oder Zwei-Wort-Beschreibung des Absatzes oder Paragraphen. 
"simplified" ist die vereinfachte Fassung des jeweiligen Paragraphen-Textes. 
"""

NEIGHBORHOOD_ANALYSIS_PROMPT_TEMPLATE = """
Sie sind ein Immobilienexperte und analysieren die Umgebung einer Immobilie.
Ihre Aufgabe ist es, eine kurze Analyse der Umgebung basierend auf dem bereitgestellten Kartenbild zu liefern.

Wenn Sie spezifische Merkmale oder Wahrzeichen in der Umgebung sehen, beschreiben Sie diese bitte im Detail.
Zum Beispiel, wenn es eine große Straße gibt, könnten Sie erwähnen, dass es sich um eine belebte Gegend handeln könnte und daher laut sein könnte.
Wenn es einen nahegelegenen Park gibt, könnten Sie erwähnen, dass dieser eine grüne Oase für die Bewohner bietet, um sich zu entspannen.

**Anforderungen:**

1. Beschreiben Sie die Umgebung basierend auf dem bereitgestellten Kartenbild.
2. Erwähnen Sie spezifische Merkmale oder Wahrzeichen, die Sie sehen.
3. Bieten Sie eine kurze Analyse darüber, wie diese Merkmale die Immobilie oder ihre Bewohner beeinflussen könnten.
4. Geben Sie keine persönlichen Meinungen oder Vorurteile ab.
5. Geben Sie keine rechtlichen Ratschläge oder Analysen.
6. Antworten Sie in vollständigen Sätzen und verwenden Sie korrekte Grammatik und Interpunktion.
7. Antworten Sie nur auf Deutsch.

**Zusätzliche Informationen:**

- Das Kartenbild zeigt die Umgebung der Immobilie, die sich befindet an: {address}
- Das Bild ist eine Draufsicht auf das Gebiet und zeigt Straßen, Gebäude, Parks und andere Merkmale.
"""

DETAIL_EXTRACTION_PROMPT_TEMPLATE = """
Sie sind ein Vertragsanalyse-Experte. Ihre Aufgabe ist es, den Vertrag zu analysieren und wichtige Informationen zu extrahieren, die in einem JSON-Objekt organisiert werden, das *strikt* dem folgenden Schema entspricht:

{schema}

**Anforderungen:**

1. Geben Sie keine persönlichen Kontaktinformationen (Namen, Telefonnummern, E-Mails, Unterschriften) an. Geben Sie die Adresse der Immobilie (Stadt, Postleitzahl) an.
2. Extrahieren Sie alle Preisdetails mit Beschreibungen und Beträgen.
3. Wenn ein Abschnitt nicht vorhanden oder nicht extrahierbar ist, lassen Sie ihn als null oder eine leere Zeichenfolge.
4. Geben Sie keine rechtlichen Ratschläge oder Interpretationen.
5. Seien Sie bei der Extraktion so genau wie möglich.

**Zusätzliche Informationen:**
* Der Vertrag kann Informationen über die Immobilie, Mietbedingungen, Kosten und andere Details enthalten.
* Der Vertrag kann auf Deutsch sein.
* Der Vertrag kann Tabellen, Listen oder andere strukturierte Daten enthalten.
* Der Vertrag kann handschriftliche Anmerkungen oder Text enthalten, die nicht ignoriert werden sollten, da sie Teil des Vertrags sind!
"""


class ContractProcessor:
    def __init__(self):
        self.vision_client = VISION_CLIENT
        self.gemini_client = GEMINI_CLIENT
        self.mistral_client = MISTRAL_CLIENT
        self.executor = ThreadPoolExecutor(max_workers=5)

    def encode_image(self, image_path: str) -> Optional[str]:
        """Encode an image file to base64 string."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image {image_path}: {e}")
            return None

    async def process_contract(self, contract: Contract):
        """Main entry point for contract processing."""
        start_time = datetime.now()
        logger.info("Starting contract processing")

        updated_contract_details = dict()
        contract_images = await sync_to_async(contract.get_images)()
        contract_details = await sync_to_async(contract.get_details)()

        # Step 1: Extract text using Google Cloud Vision (more efficient for OCR)
        if not contract_images:
            logger.error("No contract images found")
            return {"error": "No contract images found"}

        if not contract_details.full_contract_text:
            full_contract_text = await self.extract_text_with_vision(contract_images)
        else:
            logger.info("Using existing full contract text")
            full_contract_text = contract_details.full_contract_text

        if not full_contract_text:
            logger.error("Text extraction failed")
            return {"error": "Text extraction failed"}

        logger.info(f"Text extraction completed in {(datetime.now() - start_time).total_seconds()} seconds")
        updated_contract_details["full_contract_text"] = full_contract_text

        # Step 2: Run parallel tasks for full contract details and simplified paragraphs
        step2_tasks = [
            self.extract_full_contract_details(full_contract_text, contract_images),
            self.simplify_paragraphs(full_contract_text)
        ]
        step2_results = await asyncio.gather(*step2_tasks, return_exceptions=True)

        # Handle step 2 results
        if len(step2_results) > 0 and isinstance(step2_results[0], dict):
            updated_contract_details.update(step2_results[0])  # Use update to merge dictionaries

        if len(step2_results) > 1 and isinstance(step2_results[1], list):
            updated_contract_details["simplified_paragraphs"] = step2_results[1]

        # Step 3: Analyze neighborhood based on address
        address = self.get_address_from_details(updated_contract_details)
        if address:
            try:
                neighborhood_analysis = await self.analyze_neighborhood(address)
                if isinstance(neighborhood_analysis, str):
                    updated_contract_details["neighborhood_analysis"] = neighborhood_analysis
            except Exception as e:
                logger.error(f"Error analyzing neighborhood: {str(e)}")

        # Process results
        result_dict = {
            "full_contract_text": full_contract_text,
            "processing_time": (datetime.now() - start_time).total_seconds()
        }

        logger.info(f"Contract processing completed in {result_dict['processing_time']} seconds")

        # Update contract details - make sure this is properly awaited if it's an async operation
        await sync_to_async(contract_details.update)(updated_contract_details)

        return result_dict

    def get_address_from_details(self, details: Dict) -> str:
        """Extract address from contract details."""
        if not details:
            return ""

        """Build an address string from details."""
        components = [
            details.get("street", ""),
            details.get("postal_code", ""),
            details.get("city", ""),
            details.get("country", "")
        ]
        # Filter out empty components and join the rest with a space
        return ' '.join(filter(None, components))

    async def extract_text_with_vision(self, image_paths: List[str]) -> str:
        """Extract text from images using Google Cloud Vision API."""
        logger.info(f"Extracting text from {len(image_paths)} images using Cloud Vision")

        # Check cache first
        cache_key = ','.join(sorted(image_paths))
        if cache_key in OCR_CACHE:
            logger.info("Using cached OCR results")
            return OCR_CACHE[cache_key]

        all_text = []
        batch_requests = []

        # Prepare batch request
        for image_path in image_paths:
            try:
                with open(image_path, 'rb') as image_file:
                    content = image_file.read()

                image = vision.Image(content=content)
                # Request text detection and document text detection
                # Document text detection is optimized for dense text
                batch_requests.append({
                    'image': image,
                    'features': [
                        {'type_': vision.Feature.Type.DOCUMENT_TEXT_DETECTION}
                    ]
                })

            except Exception as e:
                logger.error(f"Error preparing image {image_path}: {e}")

        if not batch_requests:
            return ""

        try:
            # Process images in batch
            response = self.vision_client.batch_annotate_images(requests=batch_requests)

            for annotation in response.responses:
                if annotation.full_text_annotation:
                    all_text.append(annotation.full_text_annotation.text)
                elif annotation.text_annotations:
                    all_text.append(annotation.text_annotations[0].description)

            result = "\n\n".join(all_text)

            # Cache the result
            OCR_CACHE[cache_key] = result

            logger.info(f"Successfully extracted {len(result)} characters of text")
            return result

        except Exception as e:
            logger.error(f"Error in Cloud Vision text extraction: {e}")
            return ""

    async def extract_full_contract_details(self, text: str, images: List[str] = None) -> Dict:
        """Extract full contract details using Gemini."""
        logger.info("Extracting full contract details")

        try:
            # Get the full schema for contract details
            contract_details_schema = model_to_schema(ContractDetails)

            prompt = DETAIL_EXTRACTION_PROMPT_TEMPLATE.format(
                schema=json.dumps(contract_details_schema, indent=2)
            )

            contents = [prompt, text]

            # Process in a separate thread to not block
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._extract_details_with_gemini(contents, images)
            )

            return result

        except Exception as e:
            logger.error(f"Error in extract_full_contract_details: {e}")
            return {}

    def _extract_details_with_gemini(self, contents, images=None) -> Dict:
        """Helper method to run in thread pool for Gemini API calls."""
        try:
            # Add images if provided
            if images:
                for image_path in images:
                    if os.path.exists(image_path):
                        img = Image.open(image_path)
                        contents.append(img)

            # Generate content with the model
            response = self.gemini_client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                    top_p=0.9,
                    top_k=32,
                    max_output_tokens=4096
                ),
            )

            response_text = response.text

            try:
                response_json = clean_json(response_text)
                logger.info("Successfully extracted details with Gemini")
                return response_json
            except Exception as e:
                logger.error(f"Failed to clean Gemini JSON: {e}")
                return {}

        except Exception as e:
            logger.error(f"Error in _extract_details_with_gemini: {e}")
            return {}

    async def simplify_paragraphs(self, text: str) -> List[Dict]:
        """Simplify contract paragraphs using Mistral."""
        logger.info("Simplifying contract paragraphs")

        if not text:
            return []

        try:
            # Process in a separate thread to not block
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._simplify_with_mistral(text)
            )

            return result

        except Exception as e:
            logger.error(f"Error in simplify_paragraphs: {e}")
            return []

    @staticmethod
    def _merge_paragraphs(all_results: List[Dict]) -> List:
        """Merge paragraphs into chunks of 4k characters."""
        merged_results = {}
        for item in all_results:
            title = item.get("title")
            simplified = item.get("simplified")

            if title and simplified:
                if title not in merged_results:
                    merged_results[title] = simplified
                else:
                    merged_results[title] += " " + simplified
        return [{"title": title, "simplified": simplified} for title, simplified in merged_results.items()]

    def _simplify_with_mistral(self, text: str) -> List[Dict]:
        """Helper method to run in thread pool for Mistral API calls."""
        try:
            # Split text into manageable chunks if needed (for token limits)
            chunks = ContractProcessor._chunk_text(text, max_chars=4000)
            all_results = []

            for chunk in chunks:
                response = self.mistral_client.chat.complete(
                    model=MISTRAL_SMALL_MODEL,
                    messages=[
                        {"role": "system", "content": SIMPLIFICATION_PROMPT},
                        {"role": "user", "content": chunk}
                    ],
                    max_tokens=4096,
                    response_format={
                        "type": "json_object",
                    }
                )

                if response and response.choices and response.choices[0].message.content:
                    try:
                        result = json.loads(response.choices[0].message.content)
                        if isinstance(result, list):
                            all_results.extend(result)
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode JSON from Mistral response")

            # Merge paragraphs if needed
            all_results = ContractProcessor._merge_paragraphs(all_results)

            return all_results

        except Exception as e:
            logger.error(f"Error in _simplify_with_mistral: {e}")
            return []

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 4000) -> List[str]:
        """Split text into chunks of roughly equal size."""
        if not text or len(text) <= max_chars:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by paragraphs
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_chars:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def analyze_neighborhood(self, address: str) -> str:
        """Analyze neighborhood based on address."""
        logger.info(f"Analyzing neighborhood for address: {address}")

        if not address:
            return ""

        try:
            # Get map image in a separate thread
            loop = asyncio.get_event_loop()
            map_image = await loop.run_in_executor(
                self.executor,
                lambda: get_neighborhood_map(address)
            )

            if not map_image:
                logger.error("Failed to get neighborhood map")
                return ""

            # Analyze in a separate thread
            result = await loop.run_in_executor(
                self.executor,
                lambda: self._analyze_neighborhood_with_gemini(address, map_image)
            )

            return result

        except Exception as e:
            logger.error(f"Error in analyze_neighborhood: {e}")
            return ""

    def _analyze_neighborhood_with_gemini(self, address: str, map_image) -> str:
        """Helper method to run in thread pool for Gemini API calls."""
        try:
            prompt = NEIGHBORHOOD_ANALYSIS_PROMPT_TEMPLATE.format(address=address)

            # Generate content with the model
            response = self.gemini_client.models.generate_content(
                model=GEMINI_FLASH_MODEL,
                contents=[prompt, map_image],
                config=genai_types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.9,
                    top_k=32,
                    max_output_tokens=2048
                ),
            )

            return response.text or ""

        except Exception as e:
            logger.error(f"Error in _analyze_neighborhood_with_gemini: {e}")
            return ""
