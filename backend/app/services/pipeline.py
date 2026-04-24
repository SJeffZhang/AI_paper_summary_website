import traceback
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.domain import Paper, PaperAITrace, PaperSummary, SystemTaskLog
from app.services.ai_processor import AIProcessor, StructuredOutputError
from app.services.crawler import Crawler
from app.services.notification_service import send_owner_alert, shanghai_today
from app.services.scorer import Scorer
from app.core.config import settings
from app.core.specs import (
    FOCUS_CAPACITY,
    FOCUS_THRESHOLD,
    WATCHING_CAPACITY,
    WATCHING_THRESHOLD,
)


def _safe_progress_log(message: str) -> None:
    try:
        print(message, flush=True)
    except BrokenPipeError:
        # Keep pipeline execution alive when stdout pipe is closed
        # (for example detached SSH sessions during long backfill runs).
        return


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
            fetch_anchor_date = issue_date - timedelta(days=3)
            raw_papers, resolved_fetch_date = self._fetch_with_backtrack(fetch_anchor_date)
            fetched_count = len(raw_papers)
            if resolved_fetch_date != fetch_anchor_date:
                _safe_progress_log(
                    (
                        f"[pipeline] fetch_date fallback: issue_date={issue_date.isoformat()} "
                        f"anchor={fetch_anchor_date.isoformat()} resolved={resolved_fetch_date.isoformat()} "
                        f"fetched={fetched_count}"
                    )
                )

            scored_papers = sorted(
                [self.scorer.score_paper(paper) for paper in raw_papers],
                key=lambda paper: paper["score"],
                reverse=True,
            )
            if not scored_papers:
                raise ValueError(f"No papers fetched for {issue_date.isoformat()}.")

            (
                focus_pool,
                watching_pool,
                focus_selected,
                focus_overflow,
                watching_selected,
                watching_overflow,
            ) = self._select_batches(scored_papers)
            watching_enabled = bool(settings.PIPELINE_ENABLE_WATCHING)
            if not watching_enabled:
                watching_selected = []
                watching_overflow = []

            snapshot_papers = scored_papers
            issue_attempted_ids: set[str] = set()

            for paper in snapshot_papers:
                paper["title_zh"] = self.ai_processor.build_fallback_title(paper["title_original"])

            paper_map = self._upsert_papers(snapshot_papers)
            self._reset_issue_snapshots(issue_date)
            self._seed_summary_snapshots(
                issue_date=issue_date,
                scored_papers=snapshot_papers,
                paper_map=paper_map,
                focus_selected_ids={paper["arxiv_id"] for paper in focus_selected},
                watching_selected_ids={paper["arxiv_id"] for paper in watching_selected} if watching_enabled else set(),
            )

            processed_count += self._process_category_batch(
                initial_batch=focus_selected,
                overflow_batch=focus_overflow,
                category="focus",
                target_count=len(focus_selected),
                seen_ids=issue_attempted_ids,
            )
            if watching_enabled:
                processed_count += self._process_category_batch(
                    initial_batch=watching_selected,
                    overflow_batch=watching_overflow,
                    category="watching",
                    target_count=len(watching_selected),
                    seen_ids=issue_attempted_ids,
                )

            if processed_count == 0:
                raise ValueError(f"No papers passed AI processing for {issue_date.isoformat()}.")

            refreshed_titles = self._refresh_selected_titles(issue_date)
            if refreshed_titles:
                _safe_progress_log(f"[pipeline] refreshed localized titles: {refreshed_titles}")

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

    def _select_batches(
        self,
        scored_papers: Sequence[Dict[str, Any]],
    ) -> Tuple[
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
        List[Dict[str, Any]],
    ]:
        focus_pool = [paper for paper in scored_papers if paper["score"] >= FOCUS_THRESHOLD]
        focus_selected = list(focus_pool[:FOCUS_CAPACITY])
        focus_selected_ids = {paper["arxiv_id"] for paper in focus_selected}
        if len(focus_selected) < FOCUS_CAPACITY:
            for paper in scored_papers:
                if paper["arxiv_id"] in focus_selected_ids:
                    continue
                focus_selected.append(paper)
                focus_selected_ids.add(paper["arxiv_id"])
                if len(focus_selected) >= FOCUS_CAPACITY:
                    break

        focus_overflow = [paper for paper in scored_papers if paper["arxiv_id"] not in focus_selected_ids]
        watching_pool = [
            paper
            for paper in scored_papers
            if paper["arxiv_id"] not in focus_selected_ids and WATCHING_THRESHOLD <= paper["score"] < FOCUS_THRESHOLD
        ]
        watching_selected = list(watching_pool[:WATCHING_CAPACITY])
        watching_selected_ids = {paper["arxiv_id"] for paper in watching_selected}
        watching_overflow = [
            paper for paper in watching_pool[WATCHING_CAPACITY:]
            if paper["arxiv_id"] not in watching_selected_ids
        ]
        return (
            focus_pool,
            watching_pool,
            focus_selected,
            focus_overflow,
            watching_selected,
            watching_overflow,
        )

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
        target_count: int,
        seen_ids: set[str] | None = None,
    ) -> int:
        accepted_ids = set()
        rejected_blacklist = set()
        queued_batch = list(initial_batch) + list(overflow_batch)
        attempted_count = 0
        max_attempts = self._max_category_attempts(category, target_count, len(queued_batch))
        seen_ids = seen_ids if seen_ids is not None else set()

        while queued_batch and len(accepted_ids) < target_count and attempted_count < max_attempts:
            paper = queued_batch.pop(0)
            arxiv_id = paper["arxiv_id"]
            summary = paper["_summary"]
            # A paper may be promoted from watching -> focus in the previous category stage.
            # Skip it when iterating the watching stage to avoid duplicate AI trace writes.
            if category != "focus" and summary.category == "focus":
                continue
            if arxiv_id in seen_ids or arxiv_id in rejected_blacklist or arxiv_id in accepted_ids:
                continue

            attempted_count += 1
            seen_ids.add(arxiv_id)
            _safe_progress_log(
                (
                    f"[pipeline][{category}] processing {arxiv_id} "
                    f"attempted={attempted_count}/{max_attempts} accepted={len(accepted_ids)}/{target_count}"
                )
            )

            try:
                self._ensure_localized_title(paper)
                parsed_results, rejected_ids = self._run_ai_batch([paper], category)
            except Exception as exc:
                _safe_progress_log(
                    f"[pipeline][{category}] {arxiv_id} failed before reviewer acceptance: {exc}"
                )
                rejected_blacklist.add(arxiv_id)
                self._demote_summary(summary)
                continue

            if arxiv_id in rejected_ids:
                _safe_progress_log(
                    f"[pipeline][{category}] {arxiv_id} rejected by reviewer after retries."
                )
                rejected_blacklist.add(arxiv_id)
                self._demote_summary(summary)
                continue

            if not parsed_results:
                _safe_progress_log(
                    f"[pipeline][{category}] {arxiv_id} returned no parsed summary payload."
                )
                rejected_blacklist.add(arxiv_id)
                self._demote_summary(summary)
                continue

            result = parsed_results[0]
            self._promote_summary(summary, category)
            self._apply_narrative(summary, result)
            accepted_ids.add(arxiv_id)

        if attempted_count >= max_attempts and len(accepted_ids) < target_count:
            _safe_progress_log(
                (
                    f"[pipeline][{category}] reached attempt cap "
                    f"{max_attempts} with accepted={len(accepted_ids)}/{target_count}; stopping early."
                )
            )

        return len(accepted_ids)

    @staticmethod
    def _max_category_attempts(category: str, target_count: int, queued_count: int) -> int:
        if queued_count <= 0:
            return 0

        if category == "focus":
            multiplier = max(1, int(settings.PIPELINE_FOCUS_ATTEMPT_MULTIPLIER or 1))
        else:
            multiplier = max(1, int(settings.PIPELINE_WATCHING_ATTEMPT_MULTIPLIER or 1))

        configured_cap = max(1, int(settings.PIPELINE_MAX_CATEGORY_ATTEMPTS or 1))
        candidate_limit = max(target_count, target_count * multiplier)
        return min(queued_count, configured_cap, candidate_limit)

    def _refresh_selected_titles(self, issue_date: date) -> int:
        targeted_summaries = (
            self.db.query(PaperSummary)
            .join(Paper, Paper.id == PaperSummary.paper_id)
            .filter(
                PaperSummary.issue_date == issue_date,
                Paper.title_zh.like("待翻译：%"),
            )
            .all()
        )
        if not targeted_summaries:
            return 0

        title_payload = [
            {
                "arxiv_id": summary.paper.arxiv_id,
                "title_original": summary.paper.title_original,
                "title_zh": summary.paper.title_zh,
            }
            for summary in targeted_summaries
        ]
        localized_titles = self.ai_processor.localize_titles(title_payload, batch_size=settings.KIMI_TITLE_BATCH_SIZE)
        updated = 0
        for summary in targeted_summaries:
            paper = summary.paper
            localized_title = str(localized_titles.get(paper.arxiv_id) or "").strip()
            if (
                localized_title
                and not localized_title.startswith("待翻译：")
                and localized_title.casefold() != paper.title_original.casefold()
            ):
                paper.title_zh = localized_title
                updated += 1

        if updated:
            self.db.flush()
        return updated

    def _ensure_localized_title(self, paper: Dict[str, Any]) -> None:
        localized_title = self.ai_processor.localize_title(paper)
        paper["title_zh"] = localized_title
        db_paper = paper.get("_paper")
        if db_paper is not None:
            db_paper.title_zh = localized_title
            self.db.flush()

    def _run_ai_batch(
        self,
        papers: Sequence[Dict[str, Any]],
        category: str,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        max_pipeline_attempts = max(1, int(settings.PIPELINE_REVIEW_REQUEUE_ATTEMPTS or 1))
        reviewer_retry_feedback: str | None = None
        last_rejected_ids: List[str] = []
        last_review_output = ""

        for pipeline_attempt in range(max_pipeline_attempts):
            parsed_results, rejected_ids, review_output = self._run_ai_batch_once(
                papers,
                category,
                attempt_offset=pipeline_attempt * 100,
                reviewer_retry_feedback=reviewer_retry_feedback,
            )

            if not rejected_ids:
                return parsed_results, []

            last_rejected_ids = list(rejected_ids)
            last_review_output = review_output
            if pipeline_attempt >= max_pipeline_attempts - 1:
                self._send_reviewer_exhausted_alert(
                    papers=papers,
                    category=category,
                    rejected_ids=rejected_ids,
                    review_output=review_output,
                    exhausted_attempts=max_pipeline_attempts,
                )
                return parsed_results, rejected_ids

            reviewer_retry_feedback = self._build_reviewer_retry_feedback(review_output, rejected_ids)
            _safe_progress_log(
                (
                    f"[pipeline][{category}] reviewer rejected IDs {','.join(rejected_ids) or '-'}; "
                    f"restarting full agent pipeline {pipeline_attempt + 2}/{max_pipeline_attempts}."
                )
            )

        return [], last_rejected_ids

    def _run_ai_batch_once(
        self,
        papers: Sequence[Dict[str, Any]],
        category: str,
        *,
        attempt_offset: int = 0,
        reviewer_retry_feedback: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], List[str], str]:
        max_retries = 2
        editor_brief = None
        editor_records: List[Dict[str, Any]] = []

        for attempt in range(max_retries + 1):
            editor_brief = None
            trace_attempt_no = attempt_offset + attempt + 1
            try:
                if reviewer_retry_feedback:
                    editor_brief = self.ai_processor.run_editor(
                        papers,
                        category,
                        retry_feedback=reviewer_retry_feedback,
                    )
                else:
                    editor_brief = self.ai_processor.run_editor(papers, category)
                editor_records = self.ai_processor.parse_editor_records(editor_brief, papers)
                self._record_editor_traces(papers, editor_records, attempt_no=trace_attempt_no)
                break
            except StructuredOutputError as exc:
                self._record_uniform_stage_traces(
                    papers,
                    stage="editor",
                    stage_status="invalid",
                    attempt_no=trace_attempt_no,
                    content=exc.raw_output,
                )
                try:
                    editor_brief = self.ai_processor.repair_editor_output(exc.raw_output, papers, category)
                    editor_records = self.ai_processor.parse_editor_records(editor_brief, papers)
                    self._record_editor_traces(papers, editor_records, attempt_no=trace_attempt_no)
                    break
                except Exception:
                    pass
                if attempt >= max_retries:
                    raise
            except Exception:
                if editor_brief:
                    self._record_uniform_stage_traces(
                        papers,
                        stage="editor",
                        stage_status="invalid",
                        attempt_no=trace_attempt_no,
                        content=editor_brief,
                    )
                if attempt >= max_retries:
                    raise

        if editor_brief is None:
            raise ValueError("Editor failed to produce a valid brief.")

        writer_history: List[Dict[str, str]] = []
        last_rejected_ids: List[str] = []
        last_review_output = ""

        for attempt in range(max_retries + 1):
            writer_output = None
            trace_attempt_no = attempt_offset + attempt + 1
            try:
                writer_output = self.ai_processor.run_writer(
                    editor_brief=editor_brief,
                    papers_metadata=papers,
                    category=category,
                    history=writer_history,
                )
                writer_records = self.ai_processor.parse_writer_records(writer_output, papers, category)
                self._record_writer_traces(papers, writer_records, attempt_no=trace_attempt_no)
            except StructuredOutputError as exc:
                self._record_uniform_stage_traces(
                    papers,
                    stage="writer",
                    stage_status="invalid",
                    attempt_no=trace_attempt_no,
                    content=exc.raw_output,
                )
                try:
                    writer_output = self.ai_processor.repair_writer_output(exc.raw_output, papers, category)
                    writer_records = self.ai_processor.parse_writer_records(writer_output, papers, category)
                    self._record_writer_traces(papers, writer_records, attempt_no=trace_attempt_no)
                except Exception:
                    if attempt >= max_retries:
                        raise
                    writer_history.append(
                        {
                            "role": "user",
                            "content": f"The previous output failed validation: {exc}. Regenerate the FULL batch strictly.",
                        }
                    )
                    continue
            except Exception as exc:
                if writer_output:
                    self._record_uniform_stage_traces(
                        papers,
                        stage="writer",
                        stage_status="invalid",
                        attempt_no=trace_attempt_no,
                        content=writer_output,
                    )
                if attempt >= max_retries:
                    raise
                writer_history.append(
                    {
                        "role": "user",
                        "content": f"The previous output failed validation: {exc}. Regenerate the FULL batch strictly.",
                    }
                )
                continue

            try:
                review_result = self.ai_processor.run_reviewer(writer_output)
                rejected_ids = review_result["rejected_ids"] if review_result["status"] == "REJECTED" else []
                self._record_reviewer_traces(
                    papers,
                    review_output=review_result["raw_output"],
                    rejected_ids=rejected_ids,
                    attempt_no=trace_attempt_no,
                )
                last_review_output = review_result["raw_output"]
                parsed_results = [
                    {
                        "arxiv_id": record["arxiv_id"],
                        "one_line_summary": record["one_line_summary"],
                        "one_line_summary_en": record["one_line_summary_en"],
                        "core_highlights": record["core_highlights"],
                        "core_highlights_en": record["core_highlights_en"],
                        "application_scenarios": record["application_scenarios"],
                        "application_scenarios_en": record["application_scenarios_en"],
                    }
                    for record in writer_records
                    if record["arxiv_id"] not in set(rejected_ids)
                ]

                if review_result["status"] == "PASSED":
                    return parsed_results, [], review_result["raw_output"]

                last_rejected_ids = rejected_ids
                if not settings.PIPELINE_REVIEWER_STRICT:
                    _safe_progress_log(
                        (
                            f"[pipeline][{category}] reviewer rejected IDs "
                            f"{','.join(rejected_ids) or '-'}; accepting writer output in non-strict mode."
                        )
                    )
                    return [
                        {
                            "arxiv_id": record["arxiv_id"],
                            "one_line_summary": record["one_line_summary"],
                            "one_line_summary_en": record["one_line_summary_en"],
                            "core_highlights": record["core_highlights"],
                            "core_highlights_en": record["core_highlights_en"],
                            "application_scenarios": record["application_scenarios"],
                            "application_scenarios_en": record["application_scenarios_en"],
                        }
                        for record in writer_records
                    ], [], review_result["raw_output"]
                if attempt >= max_retries:
                    return parsed_results, rejected_ids, review_result["raw_output"]

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
            except StructuredOutputError as exc:
                self._record_uniform_stage_traces(
                    papers,
                    stage="reviewer",
                    stage_status="invalid",
                    attempt_no=trace_attempt_no,
                    content=exc.raw_output,
                )
                if not settings.PIPELINE_REVIEWER_STRICT:
                    _safe_progress_log(
                        (
                            f"[pipeline][{category}] reviewer output invalid ({exc}); "
                            "accepting writer output in non-strict mode."
                        )
                    )
                    return [
                        {
                            "arxiv_id": record["arxiv_id"],
                            "one_line_summary": record["one_line_summary"],
                            "one_line_summary_en": record["one_line_summary_en"],
                            "core_highlights": record["core_highlights"],
                            "core_highlights_en": record["core_highlights_en"],
                            "application_scenarios": record["application_scenarios"],
                            "application_scenarios_en": record["application_scenarios_en"],
                        }
                        for record in writer_records
                    ], [], exc.raw_output
                try:
                    review_result = self.ai_processor.repair_reviewer_output(exc.raw_output, writer_output)
                    rejected_ids = review_result["rejected_ids"] if review_result["status"] == "REJECTED" else []
                    self._record_reviewer_traces(
                        papers,
                        review_output=review_result["raw_output"],
                        rejected_ids=rejected_ids,
                        attempt_no=trace_attempt_no,
                    )
                    last_review_output = review_result["raw_output"]
                    parsed_results = [
                        {
                            "arxiv_id": record["arxiv_id"],
                            "one_line_summary": record["one_line_summary"],
                            "one_line_summary_en": record["one_line_summary_en"],
                            "core_highlights": record["core_highlights"],
                            "core_highlights_en": record["core_highlights_en"],
                            "application_scenarios": record["application_scenarios"],
                            "application_scenarios_en": record["application_scenarios_en"],
                        }
                        for record in writer_records
                        if record["arxiv_id"] not in set(rejected_ids)
                    ]
                    if review_result["status"] == "PASSED":
                        return parsed_results, [], review_result["raw_output"]

                    last_rejected_ids = rejected_ids
                    if not settings.PIPELINE_REVIEWER_STRICT:
                        _safe_progress_log(
                            (
                                f"[pipeline][{category}] reviewer rejected IDs "
                                f"{','.join(rejected_ids) or '-'}; accepting writer output in non-strict mode."
                            )
                        )
                        return [
                            {
                                "arxiv_id": record["arxiv_id"],
                                "one_line_summary": record["one_line_summary"],
                                "one_line_summary_en": record["one_line_summary_en"],
                                "core_highlights": record["core_highlights"],
                                "core_highlights_en": record["core_highlights_en"],
                                "application_scenarios": record["application_scenarios"],
                                "application_scenarios_en": record["application_scenarios_en"],
                            }
                            for record in writer_records
                        ], [], review_result["raw_output"]
                    if attempt >= max_retries:
                        return parsed_results, rejected_ids, review_result["raw_output"]

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
                    continue
                except Exception:
                    if attempt >= max_retries:
                        raise
                    writer_history.append(
                        {
                            "role": "user",
                            "content": f"The previous output failed validation: {exc}. Regenerate the FULL batch strictly.",
                        }
                    )
            except Exception as exc:
                if not settings.PIPELINE_REVIEWER_STRICT:
                    _safe_progress_log(
                        (
                            f"[pipeline][{category}] reviewer stage exception ({exc}); "
                            "accepting writer output in non-strict mode."
                        )
                    )
                    return [
                        {
                            "arxiv_id": record["arxiv_id"],
                            "one_line_summary": record["one_line_summary"],
                            "one_line_summary_en": record["one_line_summary_en"],
                            "core_highlights": record["core_highlights"],
                            "core_highlights_en": record["core_highlights_en"],
                            "application_scenarios": record["application_scenarios"],
                            "application_scenarios_en": record["application_scenarios_en"],
                        }
                        for record in writer_records
                    ], [], last_review_output
                if attempt >= max_retries:
                    raise
                writer_history.append(
                    {
                        "role": "user",
                        "content": f"The previous output failed validation: {exc}. Regenerate the FULL batch strictly.",
                    }
                )

        return [], last_rejected_ids, last_review_output

    @staticmethod
    def _build_reviewer_retry_feedback(review_output: str, rejected_ids: Sequence[str]) -> str:
        rejected_label = ", ".join(rejected_ids) or "-"
        review_output = str(review_output or "").strip()
        sections = [
            "上一轮完整 agent 管线没有通过 Reviewer。",
            f"被拒绝的 arxiv_id: {rejected_label}",
            "请重新执行完整的 Editor -> Writer -> Reviewer 三阶段，并优先修复 Reviewer 指出的质量问题。",
        ]
        if review_output:
            sections.extend(["", "Reviewer 原始结论如下：", review_output])
        return "\n".join(sections)

    def _send_reviewer_exhausted_alert(
        self,
        *,
        papers: Sequence[Dict[str, Any]],
        category: str,
        rejected_ids: Sequence[str],
        review_output: str,
        exhausted_attempts: int,
    ) -> None:
        summary = papers[0].get("_summary") if papers else None
        issue_date = getattr(summary, "issue_date", None)
        paper_ids = [paper["arxiv_id"] for paper in papers]
        subject = (
            "[AI Paper Summary] Reviewer exhausted after "
            f"{exhausted_attempts} full attempts: {', '.join(paper_ids)}"
        )
        text_body = (
            "以下论文在 Reviewer 拒绝后重新进入完整 agent 管线，"
            f"但连续失败 {exhausted_attempts} 次，已被降级为 candidate。\n"
            f"issue_date: {issue_date.isoformat() if isinstance(issue_date, date) else issue_date or 'unknown'}\n"
            f"category: {category}\n"
            f"paper_ids: {', '.join(paper_ids)}\n"
            f"rejected_ids: {', '.join(rejected_ids) or '-'}\n\n"
            "最后一次 Reviewer 输出：\n"
            f"{review_output or '(empty)'}\n"
        )
        try:
            send_owner_alert(
                None,
                run_date=shanghai_today(),
                issue_date=issue_date if isinstance(issue_date, date) else None,
                subject=subject,
                text_body=text_body,
            )
        except Exception as exc:  # pragma: no cover - best effort alerting
            _safe_progress_log(
                f"[pipeline][{category}] failed to send reviewer exhaustion alert for {','.join(paper_ids)}: {exc}"
            )

    def _record_uniform_stage_traces(
        self,
        papers: Sequence[Dict[str, Any]],
        stage: str,
        stage_status: str,
        attempt_no: int,
        content: str | None,
    ) -> None:
        if not content:
            return
        trace_attempt_no = attempt_no
        if stage_status == "invalid":
            # Keep invalid raw output without colliding with generated traces
            # under the unique key (paper_summary_id, stage, attempt_no).
            trace_attempt_no = attempt_no * 10 + 1
        for paper in papers:
            self.db.add(
                PaperAITrace(
                    paper_summary_id=paper["_summary"].id,
                    stage=stage,
                    stage_status=stage_status,
                    attempt_no=trace_attempt_no,
                    content=content,
                )
            )
        self.db.flush()

    def _record_editor_traces(
        self,
        papers: Sequence[Dict[str, Any]],
        editor_records: Sequence[Dict[str, Any]],
        attempt_no: int,
    ) -> None:
        record_map = {record["arxiv_id"]: record for record in editor_records}
        for paper in papers:
            record = record_map.get(paper["arxiv_id"])
            if record is None:
                raise ValueError(f"Missing editor trace record for {paper['arxiv_id']}.")
            self.db.add(
                PaperAITrace(
                    paper_summary_id=paper["_summary"].id,
                    stage="editor",
                    stage_status="generated",
                    attempt_no=attempt_no,
                    content=record["content"],
                )
            )
        self.db.flush()

    def _record_writer_traces(
        self,
        papers: Sequence[Dict[str, Any]],
        writer_records: Sequence[Dict[str, Any]],
        attempt_no: int,
    ) -> None:
        record_map = {record["arxiv_id"]: record for record in writer_records}
        for paper in papers:
            record = record_map.get(paper["arxiv_id"])
            if record is None:
                raise ValueError(f"Missing writer trace record for {paper['arxiv_id']}.")
            self.db.add(
                PaperAITrace(
                    paper_summary_id=paper["_summary"].id,
                    stage="writer",
                    stage_status="generated",
                    attempt_no=attempt_no,
                    content=record["content"],
                )
            )
        self.db.flush()

    def _record_reviewer_traces(
        self,
        papers: Sequence[Dict[str, Any]],
        review_output: str,
        rejected_ids: Sequence[str],
        attempt_no: int,
    ) -> None:
        rejected_set = set(rejected_ids)
        for paper in papers:
            self.db.add(
                PaperAITrace(
                    paper_summary_id=paper["_summary"].id,
                    stage="reviewer",
                    stage_status="rejected" if paper["arxiv_id"] in rejected_set else "accepted",
                    attempt_no=attempt_no,
                    content=review_output,
                )
            )
        self.db.flush()

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

    def _fetch_with_backtrack(self, fetch_anchor_date: date) -> Tuple[List[Dict[str, Any]], date]:
        max_backtrack_days = max(0, int(settings.PIPELINE_FETCH_BACKTRACK_DAYS or 0))
        for offset in range(0, max_backtrack_days + 1):
            candidate_date = fetch_anchor_date - timedelta(days=offset)
            raw_papers = self.crawler.fetch_papers(fetch_date=candidate_date.isoformat())
            if raw_papers:
                return raw_papers, candidate_date
        return [], fetch_anchor_date


if __name__ == "__main__":
    db = SessionLocal()
    try:
        Pipeline(db).run()
    finally:
        db.close()
