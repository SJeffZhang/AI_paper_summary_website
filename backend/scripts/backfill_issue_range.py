import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal, rebuild_engine
from app.models.domain import PaperSummary, SystemTaskLog
from app.services.pipeline import Pipeline
from scripts.check_kimi_api import run_checks
from scripts.run_pipeline_once import _ensure_prompts_exist
from scripts.setup_local_db import ensure_database_ready
from scripts.setup_local_mysql import ensure_mysql_server_ready


TZ_SHANGHAI = timezone(timedelta(hours=8))


@dataclass
class BackfillResult:
    issue_date: str
    action: str
    status: str
    fetched_count: int
    processed_count: int
    summary_counts: dict[str, int]
    error: str | None = None


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _default_end_date() -> date:
    return datetime.now(TZ_SHANGHAI).date()


def _iter_issue_dates(start_date: date, end_date: date):
    cursor = start_date
    while cursor <= end_date:
        yield cursor
        cursor += timedelta(days=1)


def _summarize_issue_date(issue_date: date) -> tuple[str, int, int, dict[str, int], str | None]:
    db = SessionLocal()
    try:
        task_log = (
            db.query(SystemTaskLog)
            .filter(SystemTaskLog.issue_date == issue_date)
            .first()
        )
        summary_counts = dict(
            db.query(PaperSummary.category, func.count(PaperSummary.id))
            .filter(PaperSummary.issue_date == issue_date)
            .group_by(PaperSummary.category)
            .all()
        )
        if task_log is None:
            return ("MISSING", 0, 0, summary_counts, "system_task_log row not found")
        return (
            task_log.status,
            int(task_log.fetched_count or 0),
            int(task_log.processed_count or 0),
            summary_counts,
            (task_log.error_log or "").strip()[:500] or None,
        )
    finally:
        db.close()


def backfill_issue_range(start_date: date, end_date: date) -> dict[str, object]:
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")

    _ensure_prompts_exist()
    mysql_status = ensure_mysql_server_ready()
    settings.MYSQL_UNIX_SOCKET = ""
    rebuild_engine()
    database_status = ensure_database_ready()
    kimi_status = run_checks()

    results: list[BackfillResult] = []
    skipped_success = 0
    new_success = 0
    failed = 0

    for issue_date in _iter_issue_dates(start_date, end_date):
        print(f"[range] issue_date={issue_date.isoformat()}", flush=True)
        db = SessionLocal()
        try:
            existing_task = (
                db.query(SystemTaskLog)
                .filter(SystemTaskLog.issue_date == issue_date, SystemTaskLog.status == "SUCCESS")
                .first()
            )
        finally:
            db.close()

        if existing_task is not None:
            print(f"[range] skip existing SUCCESS for {issue_date.isoformat()}", flush=True)
            status, fetched_count, processed_count, summary_counts, error = _summarize_issue_date(issue_date)
            results.append(
                BackfillResult(
                    issue_date=issue_date.isoformat(),
                    action="skipped_existing_success",
                    status=status,
                    fetched_count=fetched_count,
                    processed_count=processed_count,
                    summary_counts=summary_counts,
                    error=error,
                )
            )
            skipped_success += 1
            continue

        db = SessionLocal()
        try:
            print(f"[range] executing pipeline for {issue_date.isoformat()}", flush=True)
            Pipeline(db).run(issue_date.isoformat())
        except Exception:
            pass
        finally:
            db.close()

        status, fetched_count, processed_count, summary_counts, error = _summarize_issue_date(issue_date)
        print(
            (
                f"[range] completed {issue_date.isoformat()} status={status} "
                f"fetched={fetched_count} processed={processed_count} counts={summary_counts}"
            ),
            flush=True,
        )
        results.append(
            BackfillResult(
                issue_date=issue_date.isoformat(),
                action="executed",
                status=status,
                fetched_count=fetched_count,
                processed_count=processed_count,
                summary_counts=summary_counts,
                error=error,
            )
        )
        if status == "SUCCESS":
            new_success += 1
        else:
            failed += 1

    return {
        "mysql": mysql_status,
        "database": database_status,
        "kimi": kimi_status,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "skipped_existing_success": skipped_success,
        "new_success": new_success,
        "failed": failed,
        "results": [asdict(result) for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill pipeline results for an inclusive issue_date range.")
    parser.add_argument("--start-date", default="2026-02-13")
    parser.add_argument("--end-date", default=_default_end_date().isoformat())
    args = parser.parse_args()

    result = backfill_issue_range(
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
