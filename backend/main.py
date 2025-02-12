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
            raise HTTPException(
                status_code=400, detail="Bitte laden Sie nur PDF- oder Bilddateien hoch"
            )

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


@app.post("/upload/")
async def upload_file(files: list[UploadFile] = File(...)):
    # Call the fake function with the uploaded file
    result = process_upload(files)
    return JSONResponse(
        content={"message": "Datei erfolgreich hochgeladen", "details": result}
    )


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
            server.sendmail(
                sender_email, recipient_email, message.as_string()
            )  # Send the email
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
