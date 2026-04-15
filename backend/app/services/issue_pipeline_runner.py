from __future__ import annotations

from datetime import date
from typing import Callable, Dict, Optional, Type

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.domain import PaperAITrace, PaperSummary, SystemTaskLog
from app.services.pipeline import Pipeline


def clear_issue_pipeline_state(
    issue_date: date,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> Dict[str, int]:
    """
    Remove issue-scoped snapshots and traces before retrying the same issue_date.

    This is the operational recovery path used when a run fails after writing
    partial per-issue artifacts. `paper` rows are intentionally preserved because
    they are shared facts across issue dates; only issue-scoped snapshots and
    task rows are reset.
    """
    with session_factory() as db:
        summary_ids = [
            summary_id
            for (summary_id,) in db.query(PaperSummary.id).filter(PaperSummary.issue_date == issue_date).all()
        ]

        deleted_traces = 0
        if summary_ids:
            deleted_traces = (
                db.query(PaperAITrace)
                .filter(PaperAITrace.paper_summary_id.in_(summary_ids))
                .delete(synchronize_session=False)
            )

        deleted_summaries = (
            db.query(PaperSummary)
            .filter(PaperSummary.issue_date == issue_date)
            .delete(synchronize_session=False)
        )
        deleted_tasks = (
            db.query(SystemTaskLog)
            .filter(SystemTaskLog.issue_date == issue_date)
            .delete(synchronize_session=False)
        )
        db.commit()

        return {
            "deleted_traces": int(deleted_traces or 0),
            "deleted_summaries": int(deleted_summaries or 0),
            "deleted_tasks": int(deleted_tasks or 0),
        }


def run_issue_pipeline(
    issue_date: date,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    pipeline_cls: Type[Pipeline] = Pipeline,
    cleanup_on_failure: bool = True,
) -> Dict[str, Optional[object]]:
    """
    Shared execution entry for both daily update and historical backfill.
    Guarantees both paths call the same crawler + scorer + Editor->Writer->Reviewer pipeline.
    """
    max_attempts = 2 if cleanup_on_failure else 1
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with session_factory() as db:
                pipeline_cls(db).run(issue_date.isoformat())
                task_log = (
                    db.query(SystemTaskLog)
                    .filter(SystemTaskLog.issue_date == issue_date)
                    .first()
                )
                if task_log is None:
                    raise RuntimeError("Pipeline finished without creating a system_task_log row.")

                return {
                    "issue_date": issue_date.isoformat(),
                    "status": task_log.status,
                    "fetched_count": int(task_log.fetched_count or 0),
                    "processed_count": int(task_log.processed_count or 0),
                    "finished_at": task_log.finished_at.isoformat() if task_log.finished_at else None,
                }
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                raise

            cleanup_result = clear_issue_pipeline_state(issue_date, session_factory=session_factory)
            print(
                (
                    f"[issue-runner] recovered from failed attempt {attempt} for {issue_date.isoformat()} "
                    f"by clearing issue state: {cleanup_result}"
                ),
                flush=True,
            )

    raise RuntimeError("Issue pipeline retry loop exited unexpectedly.") from last_error
