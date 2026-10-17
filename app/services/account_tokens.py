from datetime import datetime, timezone

from asyncpg.pgproto.pgproto import timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_opaque_token, hash_opaque_token
from app.models.auth_token import AuthToken
from app.models.user import User

async def issue_auth_token(
    db: AsyncSession,
    *,
    user: User,
    kind: str,
) -> str:
    now = datetime.now(timezone.utc)

    if kind == "email_verification":
        lifetime = settings.verification_token_minutes
    elif kind == "password_reset":
        lifetime = settings.password_reset_token_minutes
    else:
        raise ValueError("Unsupported auth token kind")

    # Invalidate outstanding tokens of the same kind before issuing another.
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.kind == kind,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = create_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            kind=kind,
            expires_at=now + timedelta(minutes=lifetime)
        )
    )
    await db.flush()
    return raw_token

async def consume_auth_token(
    db: AsyncSession,
    *,
    raw_token: str,
    kind: str,
) -> User | None:
    now = datetime.now(timezone.utc)
    token_hash = hash_opaque_token(raw_token)

    #Lock the token row so two concurrent request cannot bot consume it.
    record = await db.scalar(
        select(AuthToken)
        .where(
            AuthToken.token_hash == token_hash,
            AuthToken.kind == kind,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > now,
        )
        .with_for_update()
    )
    if record is None:
        return None

    record.used_at = now
    user = await db.get(User, record.user_id)
    return user