import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings

from cryptography.fernet import Fernet

cipher = Fernet(settings.webhook_encryption_key)

def generate_api_key() -> str:
    random_part = secrets.token_urlsafe(32)

    return f"hf_live_{random_part}"

def hash_api_key(api_key: str) -> str:
    value = api_key + settings.api_key_pepper

    return hashlib.sha256(
        value.encode()
    ).hexdigest()

def generate_webhook_secret() -> str:
    return (
        "whsec_"
        + secrets.token_urlsafe(32)
    )

def encrypt_webhook_secret(secret: str) -> str:
    return cipher.encrypt(
        secret.encode()
    ).decode()

def decrypt_webhook_secret(encrypted_secret: str) -> str:
    return cipher.decrypt(
        encrypted_secret.encode()
    ).decode()

def create_access_token(
        user_id: str,
) -> str:
    expires = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    )

    payload = {
        "sub": user_id,
        "exp": expires,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )