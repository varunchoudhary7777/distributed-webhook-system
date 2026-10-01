import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jose import JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

API_KEY_PREFIX = "whk_"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(
    plain_password: str,
    password_hash: str,
) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(*, user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "type": "access",
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> UUID | None:
    try:
        claims=jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithm=[JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp", "type"]},
        )
        if claims.get("type") != "access":
            return None
        return UUID(claims["sub"])
    except(JWTError, ValueError, KeyError):
        return None

def create_api_key() -> type[str, str, str]:
    secret_part = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{secret_part}"
    prefix = raw_key[:12]
    return raw_key, prefix, hash_api_key(raw_key)

def hash_api_key(raw_key: str) -> str:
    return hmac.new(
        settings.api_key_pepper.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), stored_hash)