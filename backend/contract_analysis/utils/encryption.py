# utils/encryption.py
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def get_encryption_key():
    """Get or generate encryption key"""
    if hasattr(settings, "FILE_ENCRYPTION_KEY"):
        key = settings.FILE_ENCRYPTION_KEY
        if isinstance(key, str):
            # Convert hex string to bytes
            return bytes.fromhex(key)
        return key

    # Look for key file
    key_path = os.path.join(settings.BASE_DIR, ".encryption_key")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()

    # Generate new key
    key = secrets.token_bytes(32)  # 256-bit key

    # Save key to file (for development)
    with open(key_path, "wb") as f:
        f.write(key)

    return key


def encrypt_file(file_content):
    """
    Encrypt file content using AES-GCM

    Args:
        file_content: bytes to encrypt

    Returns:
        bytes: encrypted data with format [12-byte nonce][ciphertext]
    """
    if not file_content:
        return None

    key = get_encryption_key()
    nonce = secrets.token_bytes(12)  # GCM requires a unique 12-byte nonce

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, file_content, b"")

    # Store nonce with ciphertext for decryption
    return nonce + ciphertext


def decrypt_file(encrypted_data):
    """
    Decrypt file content encrypted using AES-GCM

    Args:
        encrypted_data: bytes with format [12-byte nonce][ciphertext]

    Returns:
        bytes: decrypted file content
    """
    if not encrypted_data:
        return None

    key = get_encryption_key()

    # Extract nonce (first 12 bytes)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, b"")
    except Exception as e:
        # InvalidTag exception will be raised if tampered with
        logging.error(f"Decryption error: {e}")
        raise ValueError("File decryption failed - data may be corrupted")
