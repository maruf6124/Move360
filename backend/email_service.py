
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_otp(recipient: str, code: str):
    sender = os.getenv("SMTP_EMAIL", "").strip()
    password = os.getenv("SMTP_APP_PASSWORD", "").replace(" ", "").strip()

    if not sender or not password:
        raise RuntimeError(
            "Set SMTP_EMAIL and SMTP_APP_PASSWORD in backend/.env"
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = "Move360 - Your verification code"

    message.set_content(
        f"Your Move360 verification code is {code}. "
        "It expires in 5 minutes. "
        "Do not share this code."
    )

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=20,
        context=context
    ) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)
