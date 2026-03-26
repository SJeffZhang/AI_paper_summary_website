import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings


class MailConfigurationError(RuntimeError):
    pass


class MailDeliveryError(RuntimeError):
    pass


@dataclass(slots=True)
class EmailPayload:
    to_email: str
    subject: str
    text_body: str
    html_body: str | None = None


def validate_mail_settings() -> None:
    required_values = {
        "SMTP_HOST": settings.SMTP_HOST.strip(),
        "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL.strip(),
    }
    missing = [key for key, value in required_values.items() if not value]
    if missing:
        raise MailConfigurationError(
            "Missing required SMTP settings: " + ", ".join(missing)
        )

    if settings.SMTP_PORT <= 0:
        raise MailConfigurationError("SMTP_PORT must be a positive integer.")

    if settings.SMTP_USE_SSL and settings.SMTP_USE_STARTTLS:
        raise MailConfigurationError("SMTP_USE_SSL and SMTP_USE_STARTTLS cannot both be enabled.")

    has_username = bool(settings.SMTP_USERNAME.strip())
    has_password = bool(settings.SMTP_PASSWORD.strip())
    if has_username != has_password:
        raise MailConfigurationError("SMTP_USERNAME and SMTP_PASSWORD must be configured together.")


def build_email_message(payload: EmailPayload) -> EmailMessage:
    message = EmailMessage()
    from_name = settings.SMTP_FROM_NAME.strip()
    from_email = settings.SMTP_FROM_EMAIL.strip()
    message["From"] = formataddr((from_name, from_email)) if from_name else from_email
    message["To"] = payload.to_email
    message["Subject"] = payload.subject
    message.set_content(payload.text_body)
    if payload.html_body:
        message.add_alternative(payload.html_body, subtype="html")
    return message


def send_email(payload: EmailPayload) -> None:
    validate_mail_settings()
    message = build_email_message(payload)

    smtp_host = settings.SMTP_HOST.strip()
    smtp_port = int(settings.SMTP_PORT)
    username = settings.SMTP_USERNAME.strip()
    password = settings.SMTP_PASSWORD

    try:
        if settings.SMTP_USE_SSL:
            smtp_client = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            smtp_client = smtplib.SMTP(smtp_host, smtp_port, timeout=30)

        with smtp_client as client:
            client.ehlo()
            if settings.SMTP_USE_STARTTLS:
                client.starttls()
                client.ehlo()
            if username:
                client.login(username, password)
            client.send_message(message)
    except MailConfigurationError:
        raise
    except Exception as exc:  # pragma: no cover - exact SMTP failures are platform-specific
        raise MailDeliveryError(f"SMTP delivery failed: {exc}") from exc
