import traceback
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.domain import Paper, PaperSummary, SystemTaskLog
from app.services.ai_processor import AIProcessor
from app.services.crawler import Crawler
from app.services.scorer import Scorer
from app.core.specs import (
    FOCUS_CAPACITY,
    FOCUS_MINIMUM,
    FOCUS_THRESHOLD,
    WATCHING_CAPACITY,
    WATCHING_MINIMUM,
    WATCHING_THRESHOLD,
)


class Pipeline:
    """
    Orchestrator implementing the PRD v2.25 pipeline:
    crawl -> score -> threshold/capacity -> AI -> review/backfill -> persist snapshots
    """

    def __init__(self, db: Session):
        self.db = db
        self.crawler = Crawler()
        self.scorer = Scorer()
        self.ai_processor = AIProcessor()

    def run(self, target_date: str = None) -> None:
        issue_date = self._resolve_issue_date(target_date)
        task_log = self._start_task(issue_date)

        fetched_count = 0
        processed_count = 0

        try:
            fetch_date = issue_date - timedelta(days=3)
            raw_papers = self.crawler.fetch_papers(fetch_date=fetch_date.isoformat())
            fetched_count = len(raw_papers)

            scored_papers = sorted(
                [self.scorer.score_paper(paper) for paper in raw_papers],
                key=lambda paper: paper["score"],
                reverse=True,
            )

            focus_pool = [paper for paper in scored_papers if paper["score"] >= FOCUS_THRESHOLD]
            watching_pool = [
                paper
                for paper in scored_papers
                if WATCHING_THRESHOLD <= paper["score"] < FOCUS_THRESHOLD
            ]

            if len(focus_pool) < FOCUS_MINIMUM or len(watching_pool) < WATCHING_MINIMUM:
                raise ValueError(
                    f"Supply insufficient for {issue_date.isoformat()}: focus={len(focus_pool)}, watching={len(watching_pool)}."
                )

            localized_titles = self.ai_processor.localize_titles(scored_papers)
            for paper in scored_papers:
                paper["title_zh"] = localized_titles[paper["arxiv_id"]]

            focus_selected = focus_pool[:FOCUS_CAPACITY]
            focus_overflow = focus_pool[FOCUS_CAPACITY:]
            watching_selected = watching_pool[:WATCHING_CAPACITY]
            watching_overflow = watching_pool[WATCHING_CAPACITY:]

            paper_map = self._upsert_papers(scored_papers)
            self._reset_issue_snapshots(issue_date)
            self._seed_summary_snapshots(
                issue_date=issue_date,
                scored_papers=scored_papers,
                paper_map=paper_map,
                focus_selected_ids={paper["arxiv_id"] for paper in focus_selected},
                watching_selected_ids={paper["arxiv_id"] for paper in watching_selected},
            )

            processed_count += self._process_category_batch(
                initial_batch=focus_selected,
                overflow_batch=focus_overflow,
                category="focus",
                minimum=FOCUS_MINIMUM,
            )
            processed_count += self._process_category_batch(
                initial_batch=watching_selected,
                overflow_batch=watching_overflow,
                category="watching",
                minimum=WATCHING_MINIMUM,
            )

            task_log.fetched_count = fetched_count
            task_log.processed_count = processed_count
            task_log.status = "SUCCESS"
            task_log.error_log = None
            task_log.finished_at = datetime.now()
            self.db.commit()
        except Exception:
            self.db.rollback()
            failed_task = self.db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == issue_date).first()
            if failed_task is None:
                failed_task = SystemTaskLog(issue_date=issue_date, status="FAILED")
                self.db.add(failed_task)
            failed_task.fetched_count = fetched_count
            failed_task.processed_count = processed_count
            failed_task.status = "FAILED"
            failed_task.error_log = traceback.format_exc()
            failed_task.finished_at = datetime.now()
            self.db.commit()
            raise

    def _start_task(self, issue_date: date) -> SystemTaskLog:
        task_log = self.db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == issue_date).first()
        if task_log and task_log.status == "SUCCESS":
            raise ValueError(f"Task for {issue_date.isoformat()} already succeeded and cannot rerun automatically.")

        if task_log is None:
            task_log = SystemTaskLog(issue_date=issue_date, status="RUNNING")
            self.db.add(task_log)
        else:
            task_log.status = "RUNNING"
            task_log.error_log = None
            task_log.finished_at = None
        task_log.started_at = datetime.now()
        self.db.commit()
        return task_log

    def _upsert_papers(self, papers: Sequence[Dict[str, Any]]) -> Dict[str, Paper]:
        paper_map: Dict[str, Paper] = {}

        for meta in papers:
            db_paper = self.db.query(Paper).filter(Paper.arxiv_id == meta["arxiv_id"]).first()
            if db_paper is None:
                db_paper = Paper(arxiv_id=meta["arxiv_id"])
                self.db.add(db_paper)

            if not meta.get("title_zh"):
                raise ValueError(f"title_zh is missing for {meta['arxiv_id']}.")

            db_paper.title_zh = meta["title_zh"]
            db_paper.title_original = meta["title_original"]
            db_paper.authors = meta["authors"]
            db_paper.venue = meta.get("venue")
            db_paper.abstract = meta["abstract"]
            db_paper.pdf_url = meta["pdf_url"]
            db_paper.upvotes = int(meta.get("upvotes", 0) or 0)
            db_paper.arxiv_publish_date = self._ensure_date(meta["arxiv_publish_date"])

            self.db.flush()
            meta["_paper"] = db_paper
            paper_map[meta["arxiv_id"]] = db_paper

        return paper_map

    def _reset_issue_snapshots(self, issue_date: date) -> None:
        self.db.query(PaperSummary).filter(PaperSummary.issue_date == issue_date).delete(synchronize_session=False)
        self.db.flush()

    def _seed_summary_snapshots(
        self,
        issue_date: date,
        scored_papers: Sequence[Dict[str, Any]],
        paper_map: Dict[str, Paper],
        focus_selected_ids: set[str],
        watching_selected_ids: set[str],
    ) -> None:
        for meta in scored_papers:
            arxiv_id = meta["arxiv_id"]
            if arxiv_id in focus_selected_ids:
                category = "focus"
                candidate_reason = None
            elif arxiv_id in watching_selected_ids:
                category = "watching"
                candidate_reason = None
            elif meta["score"] >= WATCHING_THRESHOLD:
                category = "candidate"
                candidate_reason = "capacity_overflow"
            else:
                category = "candidate"
                candidate_reason = "low_score"

            summary = PaperSummary(
                paper_id=paper_map[arxiv_id].id,
                issue_date=issue_date,
                score=meta["score"],
                score_reasons=meta["score_reasons"],
                category=category,
                candidate_reason=candidate_reason,
                direction=meta["direction"],
            )
            self.db.add(summary)
            self.db.flush()
            meta["_summary"] = summary

    def _process_category_batch(
        self,
        initial_batch: Sequence[Dict[str, Any]],
        overflow_batch: Sequence[Dict[str, Any]],
        category: str,
        minimum: int,
    ) -> int:
        accepted_ids = set()
        rejected_blacklist = set()
        overflow_index = 0
        pending_batch = list(initial_batch)

        while pending_batch:
            parsed_results, rejected_ids = self._run_ai_batch(pending_batch, category)
            result_map = {result["arxiv_id"]: result for result in parsed_results}

            for paper in pending_batch:
                summary = paper["_summary"]
                arxiv_id = paper["arxiv_id"]

                if arxiv_id in rejected_ids:
                    rejected_blacklist.add(arxiv_id)
                    self._demote_summary(summary)
                    continue

                result = result_map.get(arxiv_id)
                if result is None:
                    raise ValueError(f"Missing parsed summary for {arxiv_id} in {category} batch.")

                self._promote_summary(summary, category)
                self._apply_narrative(summary, result)
                accepted_ids.add(arxiv_id)

            if len(accepted_ids) >= minimum:
                return len(accepted_ids)

            needed = minimum - len(accepted_ids)
            pending_batch = []
            while overflow_index < len(overflow_batch) and len(pending_batch) < needed:
                candidate = overflow_batch[overflow_index]
                overflow_index += 1
                if candidate["arxiv_id"] in rejected_blacklist or candidate["arxiv_id"] in accepted_ids:
                    continue
                self._promote_summary(candidate["_summary"], category)
                pending_batch.append(candidate)

            if not pending_batch:
                raise ValueError(
                    f"{category} batch fell below baseline and no eligible backfill candidates remained."
                )

        if len(accepted_ids) < minimum:
            raise ValueError(f"{category} batch completed below minimum baseline.")
        return len(accepted_ids)

    def _run_ai_batch(
        self,
        papers: Sequence[Dict[str, Any]],
        category: str,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        max_retries = 2
        editor_brief = None

        for attempt in range(max_retries + 1):
            try:
                editor_brief = self.ai_processor.run_editor(papers, category)
                break
            except Exception:
                if attempt >= max_retries:
                    raise

        if editor_brief is None:
            raise ValueError("Editor failed to produce a valid brief.")

        writer_history: List[Dict[str, str]] = []
        last_rejected_ids: List[str] = []

        for attempt in range(max_retries + 1):
            try:
                writer_output = self.ai_processor.run_writer(
                    editor_brief=editor_brief,
                    papers_metadata=papers,
                    category=category,
                    history=writer_history,
                )
                review_result = self.ai_processor.run_reviewer(writer_output)
                rejected_ids = review_result["rejected_ids"] if review_result["status"] == "REJECTED" else []
                parsed_results = self.ai_processor.parse_final_summaries(writer_output, rejected_ids, category)

                if review_result["status"] == "PASSED":
                    return parsed_results, []

                last_rejected_ids = rejected_ids
                if attempt >= max_retries:
                    return parsed_results, rejected_ids

                writer_history.extend(
                    [
                        {"role": "assistant", "content": writer_output},
                        {
                            "role": "user",
                            "content": (
                                "The reviewer rejected part of the batch. "
                                f"Rejected IDs: {', '.join(rejected_ids)}. "
                                "Regenerate the FULL batch in the exact same format and fix the weak items."
                            ),
                        },
                    ]
                )
            except Exception as exc:
                if attempt >= max_retries:
                    raise
                writer_history.append(
                    {
                        "role": "user",
                        "content": f"The previous output failed validation: {exc}. Regenerate the FULL batch strictly.",
                    }
                )

        return [], last_rejected_ids

    @staticmethod
    def _promote_summary(summary: PaperSummary, category: str) -> None:
        summary.category = category
        summary.candidate_reason = None

    @staticmethod
    def _demote_summary(summary: PaperSummary) -> None:
        summary.category = "candidate"
        summary.candidate_reason = "reviewer_rejected"
        summary.one_line_summary = None
        summary.one_line_summary_en = None
        summary.core_highlights = None
        summary.core_highlights_en = None
        summary.application_scenarios = None
        summary.application_scenarios_en = None

    @staticmethod
    def _apply_narrative(summary: PaperSummary, result: Dict[str, Any]) -> None:
        summary.candidate_reason = None
        summary.one_line_summary = result["one_line_summary"]
        summary.one_line_summary_en = result["one_line_summary_en"]
        summary.core_highlights = result["core_highlights"]
        summary.core_highlights_en = result["core_highlights_en"]
        summary.application_scenarios = result["application_scenarios"]
        summary.application_scenarios_en = result["application_scenarios_en"]

    @staticmethod
    def _resolve_issue_date(target_date: str = None) -> date:
        if target_date is None:
            return datetime.now(timezone(timedelta(hours=8))).date()
        return datetime.strptime(target_date, "%Y-%m-%d").date()

    @staticmethod
    def _ensure_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        Pipeline(db).run()
    finally:
        db.close()
