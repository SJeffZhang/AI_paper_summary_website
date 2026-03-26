from datetime import datetime, timedelta, timezone

import pytest

from app.models.domain import Subscriber
from app.services.mailer import MailDeliveryError


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def stub_subscription_emails(monkeypatch):
    sent_messages = []

    monkeypatch.setattr(
        "app.api.v1.subscribe.notification_service.send_subscription_verification_email",
        lambda email, token: sent_messages.append(("verify", email, token)),
    )
    monkeypatch.setattr(
        "app.api.v1.subscribe.notification_service.send_subscription_management_email",
        lambda email, token: sent_messages.append(("manage", email, token)),
    )
    return sent_messages


def test_subscribe_creates_pending_subscriber(api_client, session_factory):
    response = api_client.post("/api/v1/subscribe", json={"email": "new-user@example.com"})

    assert response.status_code == 200
    assert response.json()["msg"] == "邮件已发送"

    with session_factory() as session:
        subscriber = session.query(Subscriber).filter(Subscriber.email == "new-user@example.com").first()
        assert subscriber is not None
        assert subscriber.status == 0
        assert subscriber.verify_token
        assert subscriber.unsub_token
        assert subscriber.verify_expires_at is not None
        assert subscriber.unsub_expires_at is not None


def test_subscribe_refreshes_unsubscribe_token_for_active_user(api_client, session_factory, active_subscriber_seed):
    with session_factory() as session:
        subscriber = Subscriber(**active_subscriber_seed)
        session.add(subscriber)
        session.commit()
        old_token = subscriber.unsub_token

    response = api_client.post("/api/v1/subscribe", json={"email": active_subscriber_seed["email"]})

    assert response.status_code == 200
    assert response.json()["msg"] == "该邮箱已订阅，最新管理链接已发送"

    with session_factory() as session:
        refreshed = session.query(Subscriber).filter(Subscriber.email == active_subscriber_seed["email"]).first()
        assert refreshed is not None
        assert refreshed.unsub_token != old_token
        assert refreshed.unsub_expires_at is not None
        assert refreshed.unsub_expires_at.replace(tzinfo=None) > datetime.now(timezone.utc).replace(tzinfo=None)


def test_unsubscribe_rejects_expired_token(api_client, session_factory):
    with session_factory() as session:
        subscriber = Subscriber(
            email="expired@example.com",
            status=1,
            verify_token=None,
            unsub_token="expired-token",
            verify_expires_at=None,
            unsub_expires_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.add(subscriber)
        session.commit()

    response = api_client.post("/api/v1/unsubscribe", json={"token": "expired-token"})

    assert response.status_code == 400
    assert "退订链接已过期" in response.json()["msg"]


def test_unsubscribe_write_endpoint_is_rate_limited(api_client):
    for _ in range(5):
        response = api_client.post("/api/v1/unsubscribe", json={"token": "missing-token"})
        assert response.status_code == 400

    blocked = api_client.post("/api/v1/unsubscribe", json={"token": "missing-token"})

    assert blocked.status_code == 429
    assert blocked.json()["msg"] == "请求过于频繁，请一小时后再试。"


def test_subscribe_returns_503_when_mail_delivery_fails(api_client, session_factory, monkeypatch):
    def _raise_failure(_email, _token):
        raise MailDeliveryError("smtp down")

    monkeypatch.setattr(
        "app.api.v1.subscribe.notification_service.send_subscription_verification_email",
        _raise_failure,
    )

    response = api_client.post("/api/v1/subscribe", json={"email": "broken@example.com"})

    assert response.status_code == 503
    assert "邮件发送失败" in response.json()["msg"]

    with session_factory() as session:
        subscriber = session.query(Subscriber).filter(Subscriber.email == "broken@example.com").first()
        assert subscriber is None
