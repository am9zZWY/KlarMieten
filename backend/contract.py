def pdf_to_image(file: UploadFile) -> List[Image.Image]:
    """
    Convert a PDF file to a list of images
    Uses poppler. You need to install poppler on your system
    :param file: PDF file
    :return: List of images
    """
    import pdf2image

    images = pdf2image.convert_from_bytes(file.file.read())
    return images


def image_to_base64(pil_image):
    with BytesIO() as buffer:
        pil_image.save(buffer, format="PNG")
        encoded_bytes = base64.b64encode(buffer.getvalue())
        return encoded_bytes.decode("utf-8")


def extract_text_with_gpt4o_mini(image: Image.Image):
    try:
        base64_image = image_to_base64(image)

        # Send the request to the GPT-4o mini API
        response = client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o model identifier
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract text from the uploaded PDF file",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=300,
        )

        # Extract and return the AI's response
        print(response)
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Ein Fehler ist aufgetreten"


def explain_text_with_gpt4o_mini(legal_text: str):
    try:
        # Send the request to the GPT-4o mini API
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
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
                    ),
                },
                {
                    "role": "user",
                    "content": f"Legal text: {legal_text}\n\nSimplify this text in plain German:",
                },
            ],
            model="gpt-4o-mini-2024-07-18",
        )

        # Extract and return the AI's response
        print(chat_completion)
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Ein Fehler ist aufgetreten"
