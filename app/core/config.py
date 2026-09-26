from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DistributedWebhookSystem"
    environment: str = "development"

    database_url: str
    redis_url: str
    rabbitmq_url: str

    celery_result_backend: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    api_key_pepper: str

    webhook_encryption_key: str

    webhook_timeout_seconds: int = 10

    max_retry_attempts: int = 5

    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    log_level: str = "INFO"

    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    public_app_url: str

    access_token_minutes: int =15
    refresh_token_days: int = 30
    verification_token_minutes: int =60
    password_reset_token_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()