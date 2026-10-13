import hashlib
import json
from typing import Any

from passlib.context import CryptContext
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
def verify_password(
        plain_password: str,
        password_hash: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        password_hash,
    )

def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def event_request_hash(event_type: str, payload: dict) -> str:
    return sha256_hex(
        canonical_json_bytes(
            {
                "event_type": event_type,
                "payload": payload,
            }
        )
    )