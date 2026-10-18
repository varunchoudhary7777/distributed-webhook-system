from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.security import (
    ACCESS_TOKEN_MINUTES,
    create_access_token,
    hash_password,
    verify_password,
)
from app.infrastructure.email import send_account_email
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    ResendVerificationRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.account_tokens import consume_auth_token, issue_auth_token
from app.services.audit import record_audit
from app.services.refresh_token import (
    InvalidRefreshToken,
    issue_refresh_token,
    revoke_all_user_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter(
    prefix="/v1/auth",
    tags=["auth"],
)



def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        email_verified=user.email_verified_at is not None,
    )

def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/signup",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def signup(
    body: SignupRequest,
    request: Request,
    db: DbSession,
):
    email = body.email.lower()

    try:
        async with db.begin():

            user = User(
                email=email,
                password_hash=hash_password(body.password),
                is_active=True,
            )
            db.add(user)

            # Flush to get user.id before creating the verification token.
            await db.flush()
            token = await issue_auth_token(
                db,
                user=user,
                kind="email_verification",
            )
            await record_audit(
                db,
                action="auth.signup",
                resource_type="user",
                actor_user_id=user.id,
                resource_id=str(user.id),
                source_ip=_client_ip(request),
            )
    except IntegrityError:
        await db.rollback()
        # Do not reveal whether this email is already registered.
        return MessageResponse(
            message="If the address can be registered, verification instructions will be sent."
        )

    verify_url = (
        f"{settings.public_app_url.rstrip('/')}/verify-email"
        f"?token={token}"
    )
    try:
        await send_account_email(
            recipient=email,
            subject="Verify your account",
            text=f"Verify your account using this link:\n{verify_url}\n",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account created, but verification email could not be sent. Request a new verification email.",
        )

    return MessageResponse(
        message="If the address can be registered, verification instructions will be sent."
    )

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    db: DbSession,
):
    async with db.begin():
        user = await consume_auth_token(
            db,
            raw_token=body.token,
            kind="email_verification",
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token is invalid or expired",
            )

        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(timezone.utc)

        await record_audit(
            db,
            action="auth.email_verified",
            resource_type="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            source_ip=_client_ip(request),
        )

    return MessageResponse(message="Email verified")

@router.post("/resend-verification", response_model= MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    db: DbSession,
):
    generic = MessageResponse(
        message="If the account needs verification, instructions will be sent."
    )

    async with db.begin():
        user = await db.scalar(
            select(User).where(User.email == body.email.lower())
        )
        if user is None or not user.is_active or user.email_verified_at is not None:
            return generic


        token = await issue_auth_token(
            db,
            user=user,
            kind="email_verification",
        )

    verify_url = (
        f"{settings.public_app_url.rstrip('/')}/verify-email"
        f"?token={token}"
    )
    try:
        await send_account_email(
            recipient=user.email,
            subject="Verify your account",
            text=f"Verify your account using this link:\n{verify_url}\n"
        )
    except Exception:
        pass

    return generic

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: DbSession):
    email = body.email.lower()

    async with db.begin():
        user = await db.scalar(select(User).where(User.email == email))

        if (
                user is None
                or not user.is_active
                or not verify_password(body.password, user.password_hash)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

        if user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification is required",
            )


        refresh_token = await issue_refresh_token(db, user_id=user.id)
        await record_audit(
            db,
            action="auth.login",
            resource_type="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            source_ip=_client_ip(request),
        )

    return (TokenResponse(
        access_token=create_access_token(user_id=user.id),
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    ))

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    db: DbSession,
):
    try:
        async with db.begin():
            user, replacement = await rotate_refresh_token(
                db,
                raw_token=body.refresh_token,
            )
            await record_audit(
                db,
                action="auth.refresh",
                resource_type="user",
                actor_user_id=user.id,
                resource_id=str(user.id),
                source_ip=_client_ip(request),
            )
    except InvalidRefreshToken as exc:
        # Important: if the service marked a token family revoked after
        # reuse detection, that revocation must commit. Do not raise inside
        # the transaction and roll it back.
        await db.rollback()
        # The service must perform reuse-family revocation in a separate
        # committed transaction for this exception path. See note below.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    return TokenResponse(
        access_token=create_access_token(user_id=user.id),
        refresh_token=replacement,
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )

@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: LogoutRequest,
    request: Request,
    db: DbSession,
):
    async with db.begin():
        await revoke_refresh_token(db, raw_token=body.refresh_token)

    return MessageResponse(message="Logged out")

@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    body: PasswordResetRequest,
    db: DbSession,
):
    # Same response whether the account exists, is inactive, or is unknown.
    generic = MessageResponse(
        message="If an active account exists for this address, reset instructions will be sent."
    )


    async with db.begin():
        user = await db.scalar(
            select(User).where(User.email == body.email.lower())
        )
        if user is None or not user.is_active:
            return generic

        token = await issue_auth_token(
            db,
            user=user,
            kind="password_reset",
        )

    reset_url = (
        f"{settings.public_app_url.rstrip('/')}/reset-password"
        f"?token={token}"
    )
    try:
        await send_account_email(
            recipient=user.email,
            subject="Reset your password",
            text=f"Reset your password using this link:\n{reset_url}\n",
        )
    except Exception:
        # Do not expose account existence or token delivery errors publicly.
        pass

    return generic

@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    body: PasswordResetConfirmRequest,
    request: Request,
    db: DbSession,
):
    async with db.begin():
        user = await consume_auth_token(
            db,
            raw_token=body.token,
            kind="password_reset",
        )
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token is invalid or expired",
            )

        user.password_hash = hash_password(body.new_password)
        await revoke_all_user_refresh_token(db, user_id=user.id)

        await record_audit(
            db,
            action="auth.password_reset",
            resource_type="user",
            actor_user_id=user.id,
            resource_id=str(user.id),
            source_ip=_client_ip(request),
        )

    return MessageResponse(message="Password updated; please sign in again")


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser):
    return UserResponse.model_validate(user)