from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    try:
        key = settings.webhook_encryption_key.encode("ascii")
        return Fernet(key)
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            "WEBHOOK_ENCRYPTION_KEY must be a valid Fernet key"
        ) from exc


def encrypt_secret(secret: str) -> str:
    if not secret:
        raise ValueError("Webhook secret cannot be empty")
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("Unable to decrypt webhook secret") from exc