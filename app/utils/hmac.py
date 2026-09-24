import hashlib
import hmac

def generate_signature(
        secret: str,
        payload: bytes,
) -> str:

    digest = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"