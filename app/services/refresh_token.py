
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_opaque_token,
    hash_opaque_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


class InvalidRefreshToken(Exception):
    pass


async def issue_refresh_token(
    db: AsyncSession,
    *,
    user_id: UUID,
    family_id: UUID | None = None,
) -> str:
    raw = create_opaque_token()

    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_opaque_token(raw),
            family_id=(
                family_id if family_id is not None else uuid4()
            ),
            expires_at=(
                datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_days)
            ),
        )
    )

    await db.flush()
    return raw


async def rotate_refresh_token(
    db: AsyncSession,
    *,
    raw_token: str,
) -> tuple[User, str]:
    now = datetime.now(timezone.utc)
    token_hash = hash_opaque_token(raw_token)

    invalid_token = False
    user: User | None = None
    replacement: str | None = None

    # This function owns the transaction.
    # Call it with a session that has no active transaction.
    async with db.begin():
        row = await db.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )

        if row is None:
            raise InvalidRefreshToken()

        # Reuse or replay of a used/revoked token:
        # revoke all active tokens in its family.
        if row.used_at is not None or row.revoked_at is not None:
            await db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == row.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            invalid_token = True

        elif row.expires_at <= now:
            row.revoked_at = now
            invalid_token = True

        else:
            user = await db.get(User, row.user_id)

            if (
                user is None
                or not user.is_active
                or user.email_verified_at is None
            ):
                row.revoked_at = now
                invalid_token = True

            else:
                # Consume the old token and issue its replacement
                # atomically within the same transaction.
                row.used_at = now

                replacement = await issue_refresh_token(
                    db,
                    user_id=user.id,
                    family_id=row.family_id,
                )

    # The transaction has committed before we raise.
    # This preserves the revocation changes.
    if invalid_token:
        raise InvalidRefreshToken()

    # Defensive checks for type safety and control-flow clarity.
    if user is None or replacement is None:
        raise RuntimeError("Refresh-token rotation failed unexpectedly")

    return user, replacement

async def revoke_refresh_token(
    db: AsyncSession,
    *,
    raw_token: str,
) -> None:
    now = datetime.now(timezone.utc)
    token_hash = hash_opaque_token(raw_token)
    row = await db.scalar(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
        )
        .with_for_update()
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = now

async def revoke_all_user_refresh_token(
    db: AsyncSession,
    *,
    user_id: UUID,
) -> None:
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at = datetime.now(timezone.utc))
    )