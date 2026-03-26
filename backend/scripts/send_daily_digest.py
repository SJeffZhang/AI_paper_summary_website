import argparse
import json
import sys
from datetime import datetime
from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal
from app.models.domain import SystemTaskLog
from app.services import notification_service
from scripts.setup_local_db import ensure_database_ready


def _parse_recipient_override(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    return [part.strip() for part in raw_value.split(",") if part.strip()]


def send_daily_digest(
    *,
    issue_date=None,
    recipient_override: list[str] | None = None,
    dry_run: bool = False,
    session_factory=SessionLocal,
    ensure_database=ensure_database_ready,
) -> dict[str, object]:
    issue_date = issue_date or notification_service.shanghai_today()
    run_date = notification_service.shanghai_today()
    ensure_database()

    with session_factory() as db:
        task_log = (
            db.query(SystemTaskLog)
            .filter(SystemTaskLog.issue_date == issue_date)
            .first()
        )
        if task_log is None or task_log.status != "SUCCESS":
            return {
                "issue_date": issue_date.isoformat(),
                "status": "skipped",
                "reason": "missing_successful_issue",
            }

        focus_items, watching_items = notification_service.query_digest_items(db, issue_date)
        if not focus_items and not watching_items:
            return {
                "issue_date": issue_date.isoformat(),
                "status": "skipped",
                "reason": "no_publishable_items",
            }

        subscribers, missing_override_emails = notification_service.get_active_subscribers(
            db,
            recipient_override=recipient_override,
        )
        if recipient_override is not None and not subscribers:
            raise RuntimeError(
                "No active subscribers matched recipient_override: "
                + ", ".join(recipient_override)
            )
        if not subscribers:
            return {
                "issue_date": issue_date.isoformat(),
                "status": "skipped",
                "reason": "no_active_subscribers",
            }

        sent_count = 0
        failed_recipients: list[str] = []
        skipped_recipients: list[str] = []

        for subscriber in subscribers:
            if notification_service.delivery_already_sent(
                db,
                notification_type="daily_digest",
                run_date=run_date,
                recipient_email=subscriber.email,
            ):
                skipped_recipients.append(subscriber.email)
                continue

            unsubscribe_token = notification_service.refresh_unsubscribe_token(subscriber)
            db.flush()
            unsubscribe_link = notification_service.build_unsubscribe_link(unsubscribe_token)
            subject, text_body, html_body = notification_service.render_digest_email(
                issue_date=issue_date,
                focus_items=focus_items,
                watching_items=watching_items,
                unsubscribe_link=unsubscribe_link,
            )

            try:
                result = notification_service.deliver_logged_email(
                    db,
                    notification_type="daily_digest",
                    run_date=run_date,
                    issue_date=issue_date,
                    recipient_email=subscriber.email,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    dry_run=dry_run,
                )
            except Exception:
                failed_recipients.append(subscriber.email)
                continue

            if result["status"] == "sent":
                sent_count += 1
            else:
                skipped_recipients.append(subscriber.email)

        result = {
            "issue_date": issue_date.isoformat(),
            "status": "completed" if not failed_recipients else "partial_failure",
            "sent_count": sent_count,
            "failed_recipients": failed_recipients,
            "skipped_recipients": skipped_recipients,
            "missing_override_emails": missing_override_emails,
            "dry_run": dry_run,
        }

        if failed_recipients:
            subject = f"[AI Paper Summary] Daily digest delivery issues: {issue_date.isoformat()}"
            text_body = (
                f"run_date: {run_date.isoformat()}\n"
                f"issue_date: {issue_date.isoformat()}\n"
                f"failed_recipients: {', '.join(failed_recipients)}"
            )
            html_body = (
                f"<p><strong>run_date:</strong> {run_date.isoformat()}<br />"
                f"<strong>issue_date:</strong> {issue_date.isoformat()}<br />"
                f"<strong>failed_recipients:</strong> {', '.join(map(escape, failed_recipients))}</p>"
            )
            try:
                notification_service.send_owner_alert(
                    db,
                    run_date=run_date,
                    issue_date=issue_date,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                )
            except Exception as alert_exc:  # pragma: no cover - best effort secondary alert
                print(f"[daily-digest] owner alert failed: {alert_exc}", file=sys.stderr, flush=True)
            raise RuntimeError(json.dumps(result, ensure_ascii=False))

        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the daily digest email to active subscribers.")
    parser.add_argument("--issue-date", help="Override the issue_date in YYYY-MM-DD format.")
    parser.add_argument(
        "--recipient-override",
        help="Comma-separated list of active subscriber emails for safe test sends.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the digest and resolve recipients without sending any real email.",
    )
    args = parser.parse_args()

    issue_date = datetime.strptime(args.issue_date, "%Y-%m-%d").date() if args.issue_date else None
    result = send_daily_digest(
        issue_date=issue_date,
        recipient_override=_parse_recipient_override(args.recipient_override),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
