import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.issue_pipeline_runner import run_issue_pipeline
from app.services.notification_service import send_owner_alert, shanghai_today
from app.services.pipeline import Pipeline
from scripts.run_pipeline_once import _ensure_prompts_exist
from scripts.setup_local_db import ensure_database_ready


def _validate_runtime_config() -> None:
    required_values = {
        "LLM_API_KEY": settings.LLM_API_KEY,
        "LLM_MODEL": settings.LLM_MODEL.strip(),
        "LLM_BASE_URL": settings.LLM_BASE_URL.strip(),
    }
    missing = [key for key, value in required_values.items() if not value]
    if missing:
        raise RuntimeError("Missing required LLM runtime settings: " + ", ".join(missing))


def _safe_owner_alert(
    issue_date,
    subject: str,
    error_message: str,
    skip_owner_alert: bool,
    *,
    session_factory=SessionLocal,
    alert_sender=send_owner_alert,
) -> None:
    if skip_owner_alert:
        return

    run_date = shanghai_today()
    text_body = (
        f"AI Paper Summary 每日更新任务失败。\n"
        f"run_date: {run_date.isoformat()}\n"
        f"issue_date: {issue_date.isoformat()}\n"
        f"error: {error_message}\n"
    )
    html_body = (
        "<p>AI Paper Summary 每日更新任务失败。</p>"
        f"<p><strong>run_date:</strong> {run_date.isoformat()}<br />"
        f"<strong>issue_date:</strong> {issue_date.isoformat()}<br />"
        f"<strong>error:</strong> {error_message}</p>"
    )

    db = None
    try:
        db = session_factory()
        alert_sender(
            db,
            run_date=run_date,
            issue_date=issue_date,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return
    except Exception as alert_exc:  # pragma: no cover - best-effort alerting
        print(f"[daily-update] db-backed owner alert failed: {alert_exc}", file=sys.stderr, flush=True)
    finally:
        if db is not None:
            db.close()

    try:
        alert_sender(
            None,
            run_date=run_date,
            issue_date=issue_date,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception as fallback_exc:  # pragma: no cover - best-effort alerting
        print(f"[daily-update] fallback owner alert failed: {fallback_exc}", file=sys.stderr, flush=True)


def run_daily_update_job(
    *,
    issue_date=None,
    skip_owner_alert: bool = False,
    session_factory=SessionLocal,
    pipeline_cls=Pipeline,
    ensure_database=ensure_database_ready,
    alert_sender=send_owner_alert,
) -> dict[str, object]:
    issue_date = issue_date or shanghai_today()

    try:
        _ensure_prompts_exist()
        ensure_database()
        _validate_runtime_config()
        return run_issue_pipeline(
            issue_date,
            session_factory=session_factory,
            pipeline_cls=pipeline_cls,
        )
    except Exception as exc:
        subject = f"[AI Paper Summary] Daily update failed: {issue_date.isoformat()}"
        _safe_owner_alert(
            issue_date,
            subject,
            str(exc),
            skip_owner_alert,
            session_factory=session_factory,
            alert_sender=alert_sender,
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the production daily update pipeline for a specific issue date.")
    parser.add_argument("--issue-date", help="Override the issue_date in YYYY-MM-DD format.")
    parser.add_argument(
        "--skip-owner-alert",
        action="store_true",
        help="Do not send the owner failure alert email when the job fails.",
    )
    args = parser.parse_args()

    issue_date = datetime.strptime(args.issue_date, "%Y-%m-%d").date() if args.issue_date else None
    result = run_daily_update_job(issue_date=issue_date, skip_owner_alert=args.skip_owner_alert)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
