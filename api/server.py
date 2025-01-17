import base64
import logging
import os
import secrets
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from typing import Dict, List

import jwt
from PIL import Image
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi import File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from openai import OpenAI
from pydantic import BaseModel
from pyotp import TOTP

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
logger = logging.getLogger(__name__)
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


def process_upload(files: list[UploadFile]):
    # Check the file types
    for file in files:
        validate_file(file)

    # if it's a PDF, convert it to images
    images = []
    for file in files:
        if file.content_type == "application/pdf":
            images.extend(pdf_to_image(file))
        elif file.content_type.startswith("image"):
            images.append(Image.open(file.file))
        else:
            raise HTTPException(status_code=400, detail="Bitte laden Sie nur PDF- oder Bilddateien hoch")

    # Process the images
    texts = []
    for image in images:
        texts.append(extract_text_with_gpt4o_mini(image))

    # Explain the text
    explanations = []
    for text in texts:
        explanations.append(explain_text_with_gpt4o_mini(text))

    return explanations


MAX_FILE_SIZE = 10 * 1024 * 1024


async def validate_file(file: UploadFile):
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    allowed_types = ["application/pdf", "image/jpeg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")


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
        return encoded_bytes.decode('utf-8')


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
                        {"type": "text", "text": "Extract text from the uploaded PDF file"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "low"
                            }
                        }
                    ]
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


@app.post("/upload/")
async def upload_file(files: list[UploadFile] = File(...)):
    # Call the fake function with the uploaded file
    result = process_upload(files)
    return JSONResponse(content={"message": "Datei erfolgreich hochgeladen", "details": result})


otp_store: Dict[str, Dict] = {}
auth_tokens: Dict[str, list[str]] = {}

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

OTP_EXPIRES_IN = 300  # OTP expires in 5 minutes


def send_email(recipient_email: str, otp: str):
    # Email configuration
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    print(sender_email, sender_password, smtp_server, smtp_port)

    # Email content
    subject = "Your OTP Code"
    body = f"Your OTP code is: {otp}. It is valid for 5 minutes."

    # Create the email
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, sender_password)  # Log in to the SMTP server
            server.sendmail(sender_email, recipient_email, message.as_string())  # Send the email
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")


def generate_otp():
    totp = TOTP("base32secret3232")
    return totp.now()


# Models
class OTPRequest(BaseModel):
    email: str


class OTPVerify(BaseModel):
    email: str
    otp: str


class User(BaseModel):
    email: str
    credits: int = 0
    auth_tokens: List[str] = []
    legal_texts: List[str] = []


# Endpoint to request an OTP
@app.post("/request-otp")
async def request_otp(data: OTPRequest):
    email = data.email
    otp = generate_otp()
    otp_store[email] = {"otp": otp, "expires_at": time.time() + OTP_EXPIRES_IN}
    send_email(email, otp)
    return {"message": "OTP sent to your email"}


# Endpoint to verify OTP and authenticate
@app.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    email = data.email
    otp = data.otp

    # Check if OTP exists and is valid
    if email not in otp_store:
        raise HTTPException(status_code=400, detail="Invalid email or OTP")

    stored_otp_data = otp_store[email]
    if stored_otp_data["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if time.time() > stored_otp_data["expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired")

    # OTP is valid; authenticate the user
    del otp_store[email]
    token = jwt.encode({"email": email}, os.getenv("JWT_SECRET"), algorithm="HS256")

    # Save the token in the auth_tokens
    if email not in auth_tokens:
        auth_tokens[email] = []
    auth_tokens[email].append(token)

    # Generate a JWT token and return it
    return {"message": "Authentication successful", "token": token}


@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    # Check if the token is valid
    for email, tokens in auth_tokens.items():
        if token in tokens:
            return {"message": "You are authenticated"}
    raise HTTPException(status_code=401, detail="Invalid token")
