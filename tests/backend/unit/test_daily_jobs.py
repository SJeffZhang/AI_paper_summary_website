from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts import backfill_issue_range as backfill_script
from app.models.domain import NotificationDeliveryLog, Subscriber, SystemTaskLog
from app.services import mailer as mailer_service
from scripts.install_linux_cron import build_cron_block, merge_managed_block
from scripts.run_daily_update_job import run_daily_update_job
from scripts.send_daily_digest import send_daily_digest


def test_build_cron_block_contains_expected_schedule_entries():
    cron_block = build_cron_block(
        python_bin="/usr/bin/python3",
        repo_root=Path("/srv/AI_paper_summary_website"),
        backend_dir=Path("/srv/AI_paper_summary_website/backend"),
        log_dir=Path("/srv/AI_paper_summary_website/runtime/logs"),
    )

    assert "CRON_TZ=Asia/Shanghai" in cron_block
    assert "0 8 * * *" in cron_block
    assert "30 8 * * *" in cron_block
    assert "scripts/run_daily_update_job.py" in cron_block
    assert "scripts/send_daily_digest.py" in cron_block


def test_merge_managed_block_replaces_existing_block():
    existing = "\n".join(
        [
            "MAILTO=ops@example.com",
            "# >>> AI_PAPER_SUMMARY_CRON >>>",
            "0 1 * * * old command",
            "# <<< AI_PAPER_SUMMARY_CRON <<<",
            "15 9 * * * /usr/bin/true",
        ]
    )
    merged = merge_managed_block(existing, "# >>> AI_PAPER_SUMMARY_CRON >>>\nnew block\n# <<< AI_PAPER_SUMMARY_CRON <<<")

    assert "old command" not in merged
    assert "new block" in merged
    assert "MAILTO=ops@example.com" in merged
    assert "15 9 * * * /usr/bin/true" in merged


def test_run_daily_update_job_sends_owner_alert_on_failure(session_factory):
    alerts = []

    class FailingPipeline:
        def __init__(self, _db):
            pass

        def run(self, _issue_date: str):
            raise RuntimeError("pipeline boom")

    def fake_alert_sender(_db, **kwargs):
        alerts.append(kwargs)
        return {"status": "sent"}

    with pytest.raises(RuntimeError, match="pipeline boom"):
        run_daily_update_job(
            issue_date=date(2026, 3, 27),
            skip_owner_alert=False,
            session_factory=session_factory,
            pipeline_cls=FailingPipeline,
            ensure_database=lambda: None,
            alert_sender=fake_alert_sender,
        )

    assert len(alerts) == 1
    assert alerts[0]["issue_date"] == date(2026, 3, 27)
    assert "Daily update failed" in alerts[0]["subject"]


def test_send_daily_digest_refreshes_tokens_and_logs_delivery(monkeypatch, session_factory, seeded_papers):
    sent_payloads = []
    now = datetime.now(timezone.utc)

    with session_factory() as session:
        session.add(
            Subscriber(
                email="active@example.com",
                status=1,
                verify_token=None,
                verify_expires_at=None,
                unsub_token="stale-token",
                unsub_expires_at=now - timedelta(hours=1),
            )
        )
        session.add(
            SystemTaskLog(
                issue_date=seeded_papers["current_issue_date"],
                status="SUCCESS",
                fetched_count=12,
                processed_count=5,
            )
        )
        session.commit()

    monkeypatch.setattr(
        mailer_service,
        "send_email",
        lambda payload: sent_payloads.append(payload),
    )

    result = send_daily_digest(
        issue_date=seeded_papers["current_issue_date"],
        session_factory=session_factory,
        ensure_database=lambda: None,
    )

    assert result["status"] == "completed"
    assert result["sent_count"] == 1
    assert len(sent_payloads) == 1
    assert "退订链接" in sent_payloads[0].text_body

    with session_factory() as session:
        subscriber = session.query(Subscriber).filter(Subscriber.email == "active@example.com").one()
        assert subscriber.unsub_token != "stale-token"
        assert subscriber.unsub_expires_at is not None

        log_row = session.query(NotificationDeliveryLog).filter_by(recipient_email="active@example.com").one()
        assert log_row.notification_type == "daily_digest"
        assert log_row.status == "sent"


def test_send_daily_digest_skips_without_successful_issue(session_factory, seeded_papers):
    result = send_daily_digest(
        issue_date=seeded_papers["current_issue_date"],
        session_factory=session_factory,
        ensure_database=lambda: None,
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "missing_successful_issue"


def test_backfill_issue_range_uses_standard_pipeline_without_mysql_bootstrap(monkeypatch, session_factory):
    executed_issue_dates = []

    monkeypatch.setattr(backfill_script, "SessionLocal", session_factory)
    monkeypatch.setattr(backfill_script, "_ensure_prompts_exist", lambda: None)
    monkeypatch.setattr(backfill_script, "ensure_database_ready", lambda: {"database_ready": True})
    monkeypatch.setattr(backfill_script, "_validate_runtime_config", lambda: None)
    monkeypatch.setattr(backfill_script, "run_checks", lambda: {"kimi_ready": True})

    class RecordingPipeline:
        def __init__(self, db):
            self.db = db

        def run(self, issue_date: str):
            issue_date_value = date.fromisoformat(issue_date)
            executed_issue_dates.append(issue_date_value)
            self.db.add(
                SystemTaskLog(
                    issue_date=issue_date_value,
                    status="SUCCESS",
                    fetched_count=9,
                    processed_count=5,
                )
            )
            self.db.commit()

    monkeypatch.setattr(backfill_script, "Pipeline", RecordingPipeline)

    result = backfill_script.backfill_issue_range(date(2026, 3, 25), date(2026, 3, 26))

    assert result["database"] == {"database_ready": True}
    assert result["kimi"] == {"kimi_ready": True}
    assert result["new_success"] == 2
    assert result["failed"] == 0
    assert executed_issue_dates == [date(2026, 3, 25), date(2026, 3, 26)]
