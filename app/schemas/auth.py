from pydantic import BaseModel, ConfigDict, EmailStr, Field

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=1024)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    is_active: bool
    email_verified: bool

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=12, max_length=1024)

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)

class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)

class MessageResponse(BaseModel):
    message: str

