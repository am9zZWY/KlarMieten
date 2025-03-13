import json
import logging
import os
from typing import Any

from PIL import Image
from google import genai
from google.genai import types

from contract_analysis.models.contract import ContractDetails
from contract_analysis.utils.json import clean_json, model_to_schema
from contract_analysis.utils.map import get_neighborhood_map

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
    if total_token_count is None:
        total_token_count = 0

    response_text = response.text
    if response_text is None:
        logger.warning("Failed to extract text with Gemini")
        logger.warning(f"Gemini response: {response}")
        return {}, total_token_count

    logger.info("Successfully extracted text with Gemini")
    return response_text, total_token_count


contract_details_json_scheme = model_to_schema(ContractDetails)


def extract_details_with_gemini(
    contract_text: str = None, contract_images: list[str] = None
) -> tuple[dict, int]:
    detail_extraction_prompt = (
        """
            Sie sind ein Vertragsanalyse-Experte. Ihre Aufgabe ist es, den Vertrag zu analysieren und wichtige Informationen zu extrahieren, die in einem JSON-Objekt organisiert werden, das *strikt* dem folgenden Schema entspricht:
            """
        + json.dumps(contract_details_json_scheme, indent=2)
        + """
    Das JSON-Objekt sollte die folgenden Schlüssel enthalten:

    **Anforderungen:**

    1. Geben Sie keine persönlichen Kontaktinformationen (Namen, Telefonnummern, E-Mails, Unterschriften) an. Geben Sie die Adresse der Immobilie (Stadt, Postleitzahl) an.
    2. Extrahieren Sie alle Preisdetails mit Beschreibungen und Beträgen.
    3. Wenn ein Abschnitt nicht vorhanden oder nicht extrahierbar ist, lassen Sie ihn als null oder eine leere Zeichenfolge.
    4. Geben Sie keine rechtlichen Ratschläge oder Interpretationen.
    5. Geben Sie keine Links oder Verweise auf externe Ressourcen an.
    6. Seien Sie bei der Extraktion so genau wie möglich.

    **Zusätzliche Informationen:**
    * Der Vertrag kann Informationen über die Immobilie, Mietbedingungen, Kosten und andere Details enthalten.
    * Der Vertrag kann auf Deutsch sein.
    * Der Vertrag kann im Format eines gescannten Bildes vorliegen.
    * Der Vertrag kann Tabellen, Listen oder andere strukturierte Daten enthalten.
    * Der Vertrag kann mehrere Seiten umfassen.
    * Der Vertrag kann handschriftliche Anmerkungen oder Text enthalten, die nicht ignoriert werden sollten, da sie Teil des Vertrags sind!
    * Der Vertrag kann Teile enthalten, die schwer zu lesen oder zu verstehen sind, die Grammatikfehler enthalten oder durcheinander sind. Geben Sie Ihr Bestes, um die Informationen genau zu extrahieren.

    Hier sind einige Beispiele:

    **Vertragsschnipsel für einen Mietvertrag mit verrauschten Daten:**

    "Wohnraummietvertrag Zwischen Sibylle Reisecista, Serbergst. 15, 78074 Tübingen als Verm Vor- und Zuname) Adam Reisecsita Serbergst. 15, 78074 Tabingen(Straße Nr., PLZ, Ort) 07011-00000 adameinecib@gmail com als Vermieter/in
    und Josef Maier X 28.01.1995
    (Geburtsdatum)
    (Straße Nr., PLZ, Ort) Schützenstraße Straße. 31, 39123 Sorgenhausen
    (Vor- und Zuname) (Geburtsdatum)
    (Straße Nr., PLZ, Ort)
    0176 0000000 x max.mustermann@protonmail.com als Mieter/in
    DE 39 0000 0000 0000 0000 00
    (Bankverbindung: IBAN)
    wird folgender Mietvertrag geschlossen:
    § 1 Mietsache
    1. Vermietet werden im EG Geschoss links-mitte rechts des Hauses Hotzenplotzige Straße. 538 Whg.Nr.10, rechts, 3. Stock, 78921 Festburg zu Wohnzwecken und alleiniger Nutzung:
    4 Zimmer 2 Keller/Nr.
    Sonstiges/Wohnungszubehör (z.B. Einbauküche) 1
    Küche 1
    Bad/Dusche 1
    Abstellraum/Nr.
    Gartenanteil 1
    separates WC
    Balkon/Terrasse 1
    Stellplatz/Nr. 13
    Garage/Nr. Es handelt sich um eine Eigentumswohnung
    2. Beheizung Einzelofen X Etagenheizung Zentralheizung Sonstiges:
    3. Gemeinschaftlich X Waschküche • Trockenraum < Garten Sonstiges:
    4. Ausgehändigte Schlüssel Schließanlage 1 Wohnung 1 Haustür Zimmer Briefkasten
    Keller Garage Handsender Zugangskarte
    Sonstiges:
    Das Mietverhältnis beginnt am 01.07.2023 und wird auf unbestimmte Zeit geschlossen.
    Die Miete beträgt monatlich für
    a) Wohnung
    b) Garage/Stellplatz
    c) Einbauküche/Möblierung
    dem Eregiewusarge errechner
    d) Betriebskosten-Vorauszahlung (siehe folg. Ziffer 2), 1400,00 € Betriebskosten werden direkt mit dem Energieversorger abgerechnet.
    Untervermietung an folgende Personen genehmigt: Jürgen Maier, Petra Schmitt, Max Mustermann

    **JSON Output:**

    ```json
    {
        "contract_type": "Unbefristeter Mietvertrag",
        "start_date": "2023-07-01",
        "address": "Hotzenplotzige Straße 538",
        "city": "Festburg",
        "postal_code": "78921",
        "property_type": "Wohnung",
        "number_of_rooms": 4,
        "kitchen": true,
        "bathroom": true,
        "separate_wc": true,
        "balcony_or_terrace": true,
        "garden": true,
        "garage_or_parking": true,
        "elevator": false,
        "basic_rent": 1400,
        "operation_costs": 0,
        "heating_costs": 0,
        "garage_costs": 0,
        "deposit_amount": null,
        "pets_allowed": false,
        "subletting_allowed": true
    }
    ```

    Ein weiteres Beispiel:

    **Vertragsschnipsel:**

    *Untermietvertrag*
    *zwischen*
    *Herrn Max Mustermann*
    *und*
    *Frau Maria Musterfrau*
    Der Untermietvertrag beginnt am 18.04.2024
    Die Mietdauer bestimmt sich nach der Dauer des Hauptmietvertrages. Endet der Hauptmietvertrag,
    gleich auch welchen Gründen, endet damit ohne Ausnahme auch der Untermietvertrag.
    *Addresse: Musterstr. 12, 12345 Musterstadt*
    Die Wohnung befindet sich in der EG Etage auf der linken Seite rechten Seite. Folgende Räume werden vermietet: .1. Zimmer, 1 Küche/Kochnische,1 Bad/Dusche/WC, 1 Bodenräume / Speicher
    Nr........., 2 Kellerräume Nr. 1. Garage / Stellplatz,.1. Garten,/ gewerblich genutzte Räume
    Die Wohnfläche beträgt ..11. qm.
    Dem Untermieter werden vom Hauptmieter für die Dauer der Untermietzeit folgende Schlüssel ausgehändigt: 1 Haustürschlüssel, 1 Wohnungsschlüssel, 1. Briefkasten -, 1 Kellerabteilt und 1 Dachgeschossschlüssel werden gemeinsam genutzt
    Die Nettomiete beträgt monatlich EUR. 270..., in Worten . Zweihundertsiebzig
    Die Vorauszahlung auf die Nebenkosten beträgt monatlich EUR. 95 in Worten Fünfundneunzig.
    Der Untermieter zahlt an den Hauptmieter eine Kaution gem. § 551 BGB in Höhe von EUR 700 in Worten: Siebenhundert.
zur Sicherung aller Ansprüche aus dem Untermietverhältnis.
    § 8 Überlassung der Mietsache an Dritte - Unteruntervermietung
Eine weitere Untervermietung der Mietsache durch den Untermieter ist nicht gestattet.

    **JSON Output:**

    ```json
    {{
        "contract_type": "Untermietvertrag",
        "start_date": "2024-04-18",
        "address": "Musterstr. 12",
        "city": "Musterstadt",
        "postal_code": "12345",
        "property_type": "Wohnung",
        "number_of_rooms": 1,
        "kitchen": true,
        "bathroom": true,
        "separate_wc": true,
        "balcony_or_terrace": false,
        "garden": true,
        "garage_or_parking": true,
        "elevator": false,
        "floor": "",
        "basic_rent": 270,
        "operation_costs": 95,
        "heating_costs": 0,
        "garage_costs": 0,
        "deposit_amount": 700
        "pets_allowed": false,
        "subletting_allowed": false,
    }}
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
            temperature=0.4, top_p=0.9, top_k=64, max_output_tokens=8192
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


def analyze_neighborhood_with_gemini(address: str) -> tuple[str, int]:
    """Analyze the neighborhood of a given address"""
    image = get_neighborhood_map(address)

    if image is None:
        logger.error("Failed to fetch neighborhood map")
        return None, 0

    # Create the model
    logger.info("Creating Gemini client")
    client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

    neighborhood_analysis_prompt = (
        """
            Sie sind ein Immobilienexperte und analysieren die Umgebung einer Immobilie.
            Ihre Aufgabe ist es, eine kurze Analyse der Umgebung basierend auf dem bereitgestellten Kartenbild zu liefern.
        
            Wenn Sie spezifische Merkmale oder Wahrzeichen in der Umgebung sehen, beschreiben Sie diese bitte im Detail.
            Zum Beispiel, wenn es eine große Straße gibt, könnten Sie erwähnen, dass es sich um eine belebte Gegend handeln könnte und daher laut sein könnte.
            Wenn es einen nahegelegenen Park gibt, könnten Sie erwähnen, dass dieser eine grüne Oase für die Bewohner bietet, um sich zu entspannen.
            Wenn es eine nahegelegene Polizeistation oder ein Krankenhaus gibt, könnten Sie erwähnen, dass dies Sicherheit und Bequemlichkeit für die Bewohner bietet, aber auch zu mehr Lärm durch Sirenen führen könnte.
        
            **Anforderungen:**
        
            1. Beschreiben Sie die Umgebung basierend auf dem bereitgestellten Kartenbild.
            2. Erwähnen Sie spezifische Merkmale oder Wahrzeichen, die Sie sehen.
            3. Bieten Sie eine kurze Analyse darüber, wie diese Merkmale die Immobilie oder ihre Bewohner beeinflussen könnten.
            4. Geben Sie keine persönlichen Meinungen oder Vorurteile ab.
            5. Geben Sie keine rechtlichen Ratschläge oder Analysen.
            6. Geben Sie keine Informationen über die Immobilie selbst, nur über die Umgebung.
            7. Geben Sie keine Informationen über den Eigentümer der Immobilie oder die Bewohner.
            8. Antworten Sie in vollständigen Sätzen und verwenden Sie korrekte Grammatik und Interpunktion.
            9. Antworten Sie nur auf Deutsch.
        
            **Zusätzliche Informationen:**
        
            - Das Kartenbild zeigt die Umgebung der Immobilie, die sich befindet an:
            """
        + address
        + """
    - Das Bild ist eine Draufsicht auf das Gebiet und zeigt Straßen, Gebäude, Parks und andere Merkmale.

    **Beispielantwort:**
    Die Nachbarschaft um Max-Musterstraße 123 ist ruhig und bietet einen Park, eine Bäckerei und einen Supermarkt. Zu beachten ist, dass die Max-Musterstraße eine Durchfahrtsstraße ist, was mit Verkehrslärm verbunden sein kann. Der nahe Bahnhof sichert eine ausgezeichnete Anbindung. Musterstadt begeistert mit der Musterbrücke und dem Mustertheater, die das kulturelle Leben bereichern. Zudem bietet die Stadt zahlreiche Restaurants und Cafés sowie ein vielfältiges Angebot an Bildungseinrichtungen und Grünflächen.
    """
    )

    contents = [neighborhood_analysis_prompt, image]

    # Generate content with the model
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.5,
            top_p=0.9,
            top_k=64,
            max_output_tokens=8192,
        ),
    )

    usage_metadata = response.usage_metadata
    total_token_count = usage_metadata.total_token_count
    if total_token_count is None:
        total_token_count = 0

    response_text = response.text

    logger.info("Successfully analyzed neighborhood with Gemini")
    return response_text, total_token_count
