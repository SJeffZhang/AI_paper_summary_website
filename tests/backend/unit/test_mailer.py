import pytest

from app.core.config import settings
from app.services import mailer, notification_service


def test_validate_mail_settings_requires_required_fields(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")

    with pytest.raises(mailer.MailConfigurationError):
        mailer.validate_mail_settings()


def test_build_email_message_contains_text_and_html(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.com")
    monkeypatch.setattr(settings, "SMTP_FROM_NAME", "AI Paper Summary")

    message = mailer.build_email_message(
        mailer.EmailPayload(
            to_email="reader@example.com",
            subject="Digest",
            text_body="plain body",
            html_body="<p>html body</p>",
        )
    )

    assert message["To"] == "reader@example.com"
    assert message["Subject"] == "Digest"
    assert message.is_multipart()
    assert "plain body" in message.get_body(preferencelist=("plain",)).get_content()
    assert "html body" in message.get_body(preferencelist=("html",)).get_content()


def test_render_digest_email_contains_focus_watching_and_unsubscribe_link(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://frontend.example.com")

    subject, text_body, html_body = notification_service.render_digest_email(
        issue_date=notification_service.shanghai_today(),
        focus_items=[
            notification_service.DigestItem(
                paper_id=101,
                title_zh="中文标题",
                title_original="Original Title",
                one_line_summary="一句话总结",
                category="focus",
            )
        ],
        watching_items=[],
        unsubscribe_link="https://frontend.example.com/unsubscribe?token=abc",
    )

    assert "每日简报" in subject
    assert "中文标题 / Original Title" in text_body
    assert "Watching" in text_body
    assert "unsubscribe?token=abc" in text_body
    assert "查看详情" in html_body
