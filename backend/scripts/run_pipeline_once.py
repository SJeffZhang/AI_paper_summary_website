import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.specs import FOCUS_CAPACITY, FOCUS_THRESHOLD, WATCHING_CAPACITY, WATCHING_THRESHOLD
from app.db.session import SessionLocal
from app.models.domain import PaperSummary, SystemTaskLog
from app.services.crawler import Crawler
from app.services.issue_pipeline_runner import run_issue_pipeline
from app.services.scorer import Scorer
from scripts.check_kimi_api import run_checks
from scripts.setup_local_db import ensure_database_ready


PROMPT_FILES = [
    Path(__file__).resolve().parents[1] / "prompts" / "editor_prompt.md",
    Path(__file__).resolve().parents[1] / "prompts" / "writer_prompt.md",
    Path(__file__).resolve().parents[1] / "prompts" / "reviewer_prompt.md",
]


def _ensure_prompts_exist() -> None:
    missing = [str(path) for path in PROMPT_FILES if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing prompt files: {missing}")


def _validate_runtime_config() -> None:
    required_values = {
        "KIMI_API_KEY": settings.KIMI_API_KEY.strip(),
        "KIMI_MODEL": settings.KIMI_MODEL.strip(),
        "KIMI_BASE_URL": settings.KIMI_BASE_URL.strip(),
    }
    missing = [key for key, value in required_values.items() if not value]
    if missing:
        raise RuntimeError("Missing required Kimi runtime settings: " + ", ".join(missing))


def _probe_issue_date() -> dict[str, object]:
    crawler = Crawler()
    scorer = Scorer()
    today = datetime.now(timezone(timedelta(hours=8))).date()
    probe_days = int(settings.PIPELINE_PROBE_DAYS or 14)
    fallback_probe: dict[str, object] | None = None
    db = SessionLocal()
    try:
        for offset in range(probe_days):
            issue_date = today - timedelta(days=offset)
            existing_task = (
                db.query(SystemTaskLog)
                .filter(SystemTaskLog.issue_date == issue_date, SystemTaskLog.status == "SUCCESS")
                .first()
            )
            if existing_task is not None:
                print(f"[probe] skip {issue_date.isoformat()} because SUCCESS already exists", flush=True)
                continue

            fetch_date = issue_date - timedelta(days=3)
            print(
                f"[probe] evaluating issue_date={issue_date.isoformat()} fetch_date={fetch_date.isoformat()}",
                flush=True,
            )
            papers = crawler.fetch_papers(fetch_date=fetch_date.isoformat())
            scored = sorted(
                [scorer.score_paper(paper) for paper in papers],
                key=lambda paper: paper["score"],
                reverse=True,
            )
            if not scored:
                print(f"[probe] issue_date={issue_date.isoformat()} fetched=0", flush=True)
                continue

            focus_selected_ids = set()
            focus_selected = []
            for paper in scored:
                if paper["score"] >= FOCUS_THRESHOLD:
                    focus_selected.append(paper)
                    focus_selected_ids.add(paper["arxiv_id"])
                if len(focus_selected) >= FOCUS_CAPACITY:
                    break

            if len(focus_selected) < FOCUS_CAPACITY:
                for paper in scored:
                    if paper["arxiv_id"] in focus_selected_ids:
                        continue
                    focus_selected.append(paper)
                    focus_selected_ids.add(paper["arxiv_id"])
                    if len(focus_selected) >= FOCUS_CAPACITY:
                        break

            watching_selected = [
                paper
                for paper in scored
                if paper["arxiv_id"] not in focus_selected_ids and WATCHING_THRESHOLD <= paper["score"] < FOCUS_THRESHOLD
            ][:WATCHING_CAPACITY]
            focus_count = len(focus_selected)
            watching_count = len(watching_selected)
            print(
                (
                    f"[probe] issue_date={issue_date.isoformat()} fetched={len(papers)} "
                    f"focus={focus_count} watching={watching_count}"
                ),
                flush=True,
            )

            probe_result = {
                "issue_date": issue_date.isoformat(),
                "fetch_date": fetch_date.isoformat(),
                "fetched_count": len(papers),
                "focus_count": focus_count,
                "watching_count": watching_count,
            }
            if fallback_probe is None:
                fallback_probe = probe_result

            if focus_count >= FOCUS_CAPACITY:
                return {
                    **probe_result,
                    "fallback_probe": False,
                }
    finally:
        db.close()

    if fallback_probe is not None:
        fallback_probe["fallback_probe"] = True
        return fallback_probe

    raise RuntimeError(
        f"No non-empty issue_date was found in the last {probe_days} days."
    )


def run_pipeline_once() -> dict[str, object]:
    print("[run] validating prompt files", flush=True)
    _ensure_prompts_exist()
    print("[run] ensuring database schema is ready", flush=True)
    db_status = ensure_database_ready()
    print("[run] validating Kimi runtime settings", flush=True)
    _validate_runtime_config()
    print("[run] checking Kimi connectivity", flush=True)
    kimi_status = run_checks()
    fixed_issue_date = os.environ.get("PIPELINE_FIXED_ISSUE_DATE", "").strip()
    if fixed_issue_date:
        selected_issue_date = datetime.strptime(fixed_issue_date, "%Y-%m-%d").date()
        selected_fetch_date = selected_issue_date - timedelta(days=3)
        probe = {
            "issue_date": selected_issue_date.isoformat(),
            "fetch_date": selected_fetch_date.isoformat(),
        }
        print(
            f"[run] using fixed issue_date={probe['issue_date']} fetch_date={probe['fetch_date']}",
            flush=True,
        )
    else:
        print("[run] probing eligible issue_date", flush=True)
        probe = _probe_issue_date()
    print(
        (
            f"[run] selected issue_date={probe['issue_date']} "
            f"(fetch_date={probe['fetch_date']}"
            f"{', fetched=' + str(probe['fetched_count']) if 'fetched_count' in probe else ''})"
        ),
        flush=True,
    )

    print("[run] executing pipeline", flush=True)
    run_issue_pipeline(selected_issue_date)

    db = SessionLocal()
    try:
        summary_counts = dict(
            db.query(PaperSummary.category, func.count(PaperSummary.id))
            .filter(PaperSummary.issue_date == probe["issue_date"])
            .group_by(PaperSummary.category)
            .all()
        )
        task_log = (
            db.query(SystemTaskLog)
            .filter(SystemTaskLog.issue_date == probe["issue_date"])
            .first()
        )
        if task_log is None:
            raise RuntimeError("Pipeline finished without creating a system_task_log row.")

        return {
            "database": db_status,
            "kimi": kimi_status,
            "selected_issue_date": probe["issue_date"],
            "selected_fetch_date": probe["fetch_date"],
            "fetched_count": task_log.fetched_count,
            "processed_count": task_log.processed_count,
            "summary_counts": summary_counts,
            "system_task_log_status": task_log.status,
        }
    finally:
        db.close()


def main() -> None:
    result = run_pipeline_once()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
