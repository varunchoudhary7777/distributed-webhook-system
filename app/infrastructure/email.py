from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings

async def send_account_email(*, recipient: str, subject: str, text: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(text)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        start_tls=True,
        use_tls=False,
        timeout=15,
    )