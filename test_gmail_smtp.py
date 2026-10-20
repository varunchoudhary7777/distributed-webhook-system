import asyncio
from app.infrastructure.email import send_account_email

async def main() -> None:
    await send_account_email(
        recipient="varunchoudhary11223344@gmail.com",
        subject="Webhook project Gmail SMTP test",
        text="This is a test message sent through Gmail SMTP."
    )
    print("Email sent")

if __name__ == "__main__":
    asyncio.run(main())