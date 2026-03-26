import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Iterable, Sequence

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.domain import NotificationDeliveryLog, Paper, PaperSummary, Subscriber
from app.services import mailer


SHANGHAI_TZ = timezone(timedelta(hours=8))


@dataclass(slots=True)
class DigestItem:
    paper_id: int
    title_zh: str
    title_original: str
    one_line_summary: str
    category: str


def shanghai_today() -> date:
    return datetime.now(SHANGHAI_TZ).date()


def build_verify_link(token: str) -> str:
    backend_url = settings.BACKEND_PUBLIC_URL.strip().rstrip("/")
    if not backend_url:
        raise mailer.MailConfigurationError("BACKEND_PUBLIC_URL must be configured for verification emails.")
    return f"{backend_url}/api/v1/subscribe/verify?token={token}"


def build_unsubscribe_link(token: str) -> str:
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/")
    if not frontend_url:
        raise mailer.MailConfigurationError("FRONTEND_URL must be configured for unsubscribe emails.")
    return f"{frontend_url}/unsubscribe?token={token}"


def build_paper_link(paper_id: int) -> str:
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/")
    if not frontend_url:
        raise mailer.MailConfigurationError("FRONTEND_URL must be configured for digest emails.")
    return f"{frontend_url}/paper/{paper_id}"


def send_subscription_verification_email(email: str, verify_token: str) -> None:
    verify_link = build_verify_link(verify_token)
    text_body = f"请在 24 小时内点击以下链接完成订阅验证：{verify_link}"
    html_body = (
        "<p>请在 24 小时内点击以下链接完成订阅验证：</p>"
        f'<p><a href="{escape(verify_link)}">{escape(verify_link)}</a></p>'
    )
    mailer.send_email(
        mailer.EmailPayload(
            to_email=email,
            subject="请验证您的订阅",
            text_body=text_body,
            html_body=html_body,
        )
    )


def send_subscription_management_email(email: str, unsub_token: str) -> None:
    unsubscribe_link = build_unsubscribe_link(unsub_token)
    text_body = (
        "该邮箱已处于订阅状态。\n"
        f"如果需要管理订阅或退订，请在 24 小时内使用此链接：{unsubscribe_link}"
    )
    html_body = (
        "<p>该邮箱已处于订阅状态。</p>"
        "<p>如果需要管理订阅或退订，请在 24 小时内使用此链接：</p>"
        f'<p><a href="{escape(unsubscribe_link)}">{escape(unsubscribe_link)}</a></p>'
    )
    mailer.send_email(
        mailer.EmailPayload(
            to_email=email,
            subject="您的订阅仍然有效",
            text_body=text_body,
            html_body=html_body,
        )
    )


def _get_delivery_log(
    db: Session,
    *,
    notification_type: str,
    run_date: date,
    recipient_email: str,
) -> NotificationDeliveryLog | None:
    return (
        db.query(NotificationDeliveryLog)
        .filter(NotificationDeliveryLog.notification_type == notification_type)
        .filter(NotificationDeliveryLog.run_date == run_date)
        .filter(NotificationDeliveryLog.recipient_email == recipient_email)
        .first()
    )


def delivery_already_sent(
    db: Session,
    *,
    notification_type: str,
    run_date: date,
    recipient_email: str,
) -> bool:
    record = _get_delivery_log(
        db,
        notification_type=notification_type,
        run_date=run_date,
        recipient_email=recipient_email,
    )
    return record is not None and record.status == "sent"


def upsert_delivery_log(
    db: Session,
    *,
    notification_type: str,
    run_date: date,
    issue_date: date | None,
    recipient_email: str,
    status: str,
    subject: str,
    error_log: str | None = None,
) -> NotificationDeliveryLog:
    record = _get_delivery_log(
        db,
        notification_type=notification_type,
        run_date=run_date,
        recipient_email=recipient_email,
    )
    if record is None:
        record = NotificationDeliveryLog(
            notification_type=notification_type,
            run_date=run_date,
            issue_date=issue_date,
            recipient_email=recipient_email,
            status=status,
            subject=subject,
            error_log=error_log,
        )
        db.add(record)
    else:
        record.issue_date = issue_date
        record.status = status
        record.subject = subject
        record.error_log = error_log
        record.sent_at = datetime.now(SHANGHAI_TZ).replace(tzinfo=None)
    db.flush()
    return record


def deliver_logged_email(
    db: Session,
    *,
    notification_type: str,
    run_date: date,
    issue_date: date | None,
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    existing = _get_delivery_log(
        db,
        notification_type=notification_type,
        run_date=run_date,
        recipient_email=recipient_email,
    )
    if existing is not None and existing.status == "sent":
        return {
            "status": "skipped",
            "reason": "already_sent",
            "recipient_email": recipient_email,
        }

    if dry_run:
        return {
            "status": "skipped",
            "reason": "dry_run",
            "recipient_email": recipient_email,
        }

    try:
        mailer.send_email(
            mailer.EmailPayload(
                to_email=recipient_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        )
    except Exception as exc:
        upsert_delivery_log(
            db,
            notification_type=notification_type,
            run_date=run_date,
            issue_date=issue_date,
            recipient_email=recipient_email,
            status="failed",
            subject=subject,
            error_log=str(exc),
        )
        db.commit()
        raise

    upsert_delivery_log(
        db,
        notification_type=notification_type,
        run_date=run_date,
        issue_date=issue_date,
        recipient_email=recipient_email,
        status="sent",
        subject=subject,
        error_log=None,
    )
    db.commit()
    return {
        "status": "sent",
        "recipient_email": recipient_email,
    }


def send_owner_alert(
    db: Session | None,
    *,
    run_date: date,
    issue_date: date | None,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> dict[str, object]:
    recipient_email = settings.OWNER_ALERT_EMAIL.strip()
    if not recipient_email:
        raise mailer.MailConfigurationError("OWNER_ALERT_EMAIL must be configured for alert delivery.")

    if db is None:
        mailer.send_email(
            mailer.EmailPayload(
                to_email=recipient_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        )
        return {"status": "sent", "recipient_email": recipient_email, "logged": False}

    return deliver_logged_email(
        db,
        notification_type="job_alert",
        run_date=run_date,
        issue_date=issue_date,
        recipient_email=recipient_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def refresh_unsubscribe_token(subscriber: Subscriber) -> str:
    unsub_token = str(uuid.uuid4())
    subscriber.unsub_token = unsub_token
    subscriber.unsub_expires_at = datetime.now(SHANGHAI_TZ) + timedelta(hours=24)
    return unsub_token


def query_digest_items(db: Session, issue_date: date) -> tuple[list[DigestItem], list[DigestItem]]:
    rows = (
        db.query(PaperSummary, Paper)
        .join(Paper)
        .filter(PaperSummary.issue_date == issue_date)
        .filter(PaperSummary.category.in_(("focus", "watching")))
        .order_by(PaperSummary.category.asc(), PaperSummary.score.desc())
        .all()
    )

    focus_items: list[DigestItem] = []
    watching_items: list[DigestItem] = []
    for summary, paper in rows:
        item = DigestItem(
            paper_id=paper.id,
            title_zh=paper.title_zh,
            title_original=paper.title_original,
            one_line_summary=summary.one_line_summary or "",
            category=summary.category,
        )
        if summary.category == "focus":
            focus_items.append(item)
        else:
            watching_items.append(item)
    return focus_items, watching_items


def render_digest_email(
    *,
    issue_date: date,
    focus_items: Sequence[DigestItem],
    watching_items: Sequence[DigestItem],
    unsubscribe_link: str,
) -> tuple[str, str, str]:
    subject = f"AI Paper Summary | {issue_date.isoformat()} 每日简报"
    intro = f"{issue_date.isoformat()} 的 AI 论文简报已经生成。"
    lines = [intro, "", "Focus:"]
    html_focus: list[str] = []
    html_watching: list[str] = []

    if focus_items:
        for index, item in enumerate(focus_items, start=1):
            link = build_paper_link(item.paper_id)
            summary = item.one_line_summary or "暂无一句话总结"
            lines.extend(
                [
                    f"{index}. {item.title_zh} / {item.title_original}",
                    f"   {summary}",
                    f"   {link}",
                ]
            )
            html_focus.append(
                "<li>"
                f"<strong>{escape(item.title_zh)}</strong> / {escape(item.title_original)}<br />"
                f"{escape(summary)}<br />"
                f'<a href="{escape(link)}">查看详情</a>'
                "</li>"
            )
    else:
        lines.append("暂无 Focus 内容")
        html_focus.append("<li>暂无 Focus 内容</li>")

    lines.extend(["", "Watching:"])
    if watching_items:
        for index, item in enumerate(watching_items, start=1):
            link = build_paper_link(item.paper_id)
            summary = item.one_line_summary or "暂无一句话总结"
            lines.extend(
                [
                    f"{index}. {item.title_zh} / {item.title_original}",
                    f"   {summary}",
                    f"   {link}",
                ]
            )
            html_watching.append(
                "<li>"
                f"<strong>{escape(item.title_zh)}</strong> / {escape(item.title_original)}<br />"
                f"{escape(summary)}<br />"
                f'<a href="{escape(link)}">查看详情</a>'
                "</li>"
            )
    else:
        lines.append("暂无 Watching 内容")
        html_watching.append("<li>暂无 Watching 内容</li>")

    lines.extend(["", f"退订链接（24 小时有效）：{unsubscribe_link}"])
    text_body = "\n".join(lines)
    html_body = (
        f"<p>{escape(intro)}</p>"
        "<h3>Focus</h3>"
        f"<ol>{''.join(html_focus)}</ol>"
        "<h3>Watching</h3>"
        f"<ol>{''.join(html_watching)}</ol>"
        f'<p>退订链接（24 小时有效）：<a href="{escape(unsubscribe_link)}">{escape(unsubscribe_link)}</a></p>'
    )
    return subject, text_body, html_body


def get_active_subscribers(
    db: Session,
    *,
    recipient_override: Iterable[str] | None = None,
) -> tuple[list[Subscriber], list[str]]:
    query = db.query(Subscriber).filter(Subscriber.status == 1)
    if recipient_override is None:
        subscribers = query.order_by(Subscriber.email.asc()).all()
        return subscribers, []

    override_emails = [email.strip() for email in recipient_override if email.strip()]
    subscribers = query.filter(Subscriber.email.in_(override_emails)).order_by(Subscriber.email.asc()).all()
    found_emails = {subscriber.email for subscriber in subscribers}
    missing = [email for email in override_emails if email not in found_emails]
    return subscribers, missing
