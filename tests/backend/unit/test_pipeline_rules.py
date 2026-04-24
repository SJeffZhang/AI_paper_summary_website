from types import SimpleNamespace
from datetime import date

import pytest

from app.core.config import settings
from app.models.domain import Paper, PaperAITrace, PaperSummary, SystemTaskLog
from app.services.ai_processor import StructuredOutputError
import app.services.pipeline as pipeline_module
from app.services.pipeline import Pipeline


def test_seed_summary_snapshots_assigns_candidate_reasons(db_session):
    pipeline = Pipeline(db_session)
    issue_date = Pipeline._resolve_issue_date("2026-03-23")
    scored_papers = [
        {
            "arxiv_id": "2503.11001",
            "title_zh": "焦点论文",
            "title_original": "Focus Paper",
            "authors": [{"name": "Alice", "affiliation": "OpenAI"}],
            "venue": "ICLR 2026",
            "abstract": "Focus abstract",
            "pdf_url": "https://arxiv.org/pdf/2503.11001.pdf",
            "upvotes": 120,
            "arxiv_publish_date": "2026-03-20",
            "score": 96,
            "score_reasons": {"hf_recommend": 30},
            "direction": "Agent",
        },
        {
            "arxiv_id": "2503.11002",
            "title_zh": "观察候补",
            "title_original": "Watching Overflow",
            "authors": [{"name": "Bob", "affiliation": "Meta"}],
            "venue": "ACL 2026",
            "abstract": "Watching abstract",
            "pdf_url": "https://arxiv.org/pdf/2503.11002.pdf",
            "upvotes": 60,
            "arxiv_publish_date": "2026-03-20",
            "score": 55,
            "score_reasons": {"community_popularity": 20},
            "direction": "RAG",
        },
        {
            "arxiv_id": "2503.11003",
            "title_zh": "低分候选",
            "title_original": "Low Score Candidate",
            "authors": [{"name": "Carol", "affiliation": "Independent"}],
            "venue": None,
            "abstract": "Candidate abstract",
            "pdf_url": "https://arxiv.org/pdf/2503.11003.pdf",
            "upvotes": 5,
            "arxiv_publish_date": "2026-03-20",
            "score": 35,
            "score_reasons": {"academic_influence": 4},
            "direction": "Benchmarking",
        },
    ]

    paper_map = pipeline._upsert_papers(scored_papers)
    pipeline._seed_summary_snapshots(
        issue_date=issue_date,
        scored_papers=scored_papers,
        paper_map=paper_map,
        focus_selected_ids={"2503.11001"},
        watching_selected_ids=set(),
    )
    db_session.commit()

    summaries = {
        summary.paper.arxiv_id: summary
        for summary in db_session.query(PaperSummary).filter(PaperSummary.issue_date == issue_date).all()
    }

    assert summaries["2503.11001"].category == "focus"
    assert summaries["2503.11001"].candidate_reason is None
    assert summaries["2503.11002"].category == "candidate"
    assert summaries["2503.11002"].candidate_reason == "capacity_overflow"
    assert summaries["2503.11003"].category == "candidate"
    assert summaries["2503.11003"].candidate_reason == "low_score"


def test_process_category_batch_backfills_after_rejection():
    accepted_summary = SimpleNamespace(
        category="focus",
        candidate_reason=None,
        one_line_summary=None,
        one_line_summary_en=None,
        core_highlights=None,
        core_highlights_en=None,
        application_scenarios=None,
        application_scenarios_en=None,
    )
    rejected_summary = SimpleNamespace(
        category="focus",
        candidate_reason=None,
        one_line_summary="old",
        one_line_summary_en="old",
        core_highlights=["old"],
        core_highlights_en=["old"],
        application_scenarios="old",
        application_scenarios_en="old",
    )
    overflow_summary = SimpleNamespace(
        category="candidate",
        candidate_reason="capacity_overflow",
        one_line_summary=None,
        one_line_summary_en=None,
        core_highlights=None,
        core_highlights_en=None,
        application_scenarios=None,
        application_scenarios_en=None,
    )

    initial_batch = [
        {"arxiv_id": "focus-a", "_summary": accepted_summary},
        {"arxiv_id": "focus-b", "_summary": rejected_summary},
    ]
    overflow_batch = [{"arxiv_id": "focus-c", "_summary": overflow_summary}]

    pipeline = Pipeline.__new__(Pipeline)
    calls = []
    pipeline._ensure_localized_title = lambda paper: None

    def fake_run_ai_batch(papers, category):
        calls.append([paper["arxiv_id"] for paper in papers])
        if len(calls) == 1:
            return (
                [
                    {
                        "arxiv_id": "focus-a",
                        "one_line_summary": "中文 A",
                        "one_line_summary_en": "English A",
                        "core_highlights": ["A1", "A2", "A3"],
                        "core_highlights_en": ["A1", "A2", "A3"],
                        "application_scenarios": "场景 A",
                        "application_scenarios_en": "Scenario A",
                    }
                ],
                [],
            )
        if len(calls) == 2:
            return ([], ["focus-b"])
        return (
            [
                {
                    "arxiv_id": "focus-c",
                    "one_line_summary": "中文 C",
                    "one_line_summary_en": "English C",
                    "core_highlights": ["C1", "C2", "C3"],
                    "core_highlights_en": ["C1", "C2", "C3"],
                    "application_scenarios": "场景 C",
                    "application_scenarios_en": "Scenario C",
                }
            ],
            [],
        )

    pipeline._run_ai_batch = fake_run_ai_batch

    processed_count = pipeline._process_category_batch(
        initial_batch=initial_batch,
        overflow_batch=overflow_batch,
        category="focus",
        target_count=2,
    )

    assert processed_count == 2
    assert calls == [["focus-a"], ["focus-b"], ["focus-c"]]
    assert accepted_summary.category == "focus"
    assert accepted_summary.one_line_summary == "中文 A"
    assert rejected_summary.category == "candidate"
    assert rejected_summary.candidate_reason == "reviewer_rejected"
    assert rejected_summary.one_line_summary is None
    assert overflow_summary.category == "focus"
    assert overflow_summary.candidate_reason is None
    assert overflow_summary.one_line_summary == "中文 C"


def test_process_category_batch_returns_partial_count_when_backfill_is_exhausted():
    accepted_summary = SimpleNamespace(
        category="watching",
        candidate_reason=None,
        one_line_summary=None,
        one_line_summary_en=None,
        core_highlights=None,
        core_highlights_en=None,
        application_scenarios=None,
        application_scenarios_en=None,
    )

    pipeline = Pipeline.__new__(Pipeline)
    pipeline._ensure_localized_title = lambda paper: None
    pipeline._run_ai_batch = lambda papers, category: (
        [
            {
                "arxiv_id": "watch-1",
                "one_line_summary": "中文",
                "one_line_summary_en": "English",
                "core_highlights": ["P1"],
                "core_highlights_en": ["P1"],
                "application_scenarios": "场景",
                "application_scenarios_en": "Scenario",
            }
        ],
        [],
    )

    processed_count = pipeline._process_category_batch(
        initial_batch=[{"arxiv_id": "watch-1", "_summary": accepted_summary}],
        overflow_batch=[],
        category="watching",
        target_count=2,
    )

    assert processed_count == 1
    assert accepted_summary.category == "watching"
    assert accepted_summary.one_line_summary == "中文"


def test_process_category_batch_skips_watching_items_promoted_to_focus():
    promoted_summary = SimpleNamespace(category="focus")

    pipeline = Pipeline.__new__(Pipeline)
    pipeline._ensure_localized_title = lambda paper: (_ for _ in ()).throw(
        AssertionError("localized_title should not be called for promoted focus rows")
    )
    run_calls = []
    pipeline._run_ai_batch = lambda papers, category: (run_calls.append((category, papers)), ([], []))

    processed_count = pipeline._process_category_batch(
        initial_batch=[{"arxiv_id": "promoted-paper", "_summary": promoted_summary}],
        overflow_batch=[],
        category="watching",
        target_count=1,
    )

    assert processed_count == 0
    assert run_calls == []


def test_process_category_batch_skips_items_already_attempted_in_previous_category():
    shared_summary = SimpleNamespace(
        category="watching",
        candidate_reason=None,
        one_line_summary=None,
        one_line_summary_en=None,
        core_highlights=None,
        core_highlights_en=None,
        application_scenarios=None,
        application_scenarios_en=None,
    )

    pipeline = Pipeline.__new__(Pipeline)
    pipeline._ensure_localized_title = lambda paper: None
    run_calls = []

    def fake_run_ai_batch(papers, category):
        run_calls.append((category, [paper["arxiv_id"] for paper in papers]))
        return ([], ["overlap-paper"])

    pipeline._run_ai_batch = fake_run_ai_batch
    seen_ids = set()

    processed_focus = pipeline._process_category_batch(
        initial_batch=[],
        overflow_batch=[{"arxiv_id": "overlap-paper", "_summary": shared_summary}],
        category="focus",
        target_count=1,
        seen_ids=seen_ids,
    )
    processed_watching = pipeline._process_category_batch(
        initial_batch=[{"arxiv_id": "overlap-paper", "_summary": shared_summary}],
        overflow_batch=[],
        category="watching",
        target_count=1,
        seen_ids=seen_ids,
    )

    assert processed_focus == 0
    assert processed_watching == 0
    assert run_calls == [("focus", ["overlap-paper"])]


def test_process_category_batch_processes_each_paper_in_isolation():
    summaries = [
        SimpleNamespace(
            category="focus",
            candidate_reason=None,
            one_line_summary=None,
            one_line_summary_en=None,
            core_highlights=None,
            core_highlights_en=None,
            application_scenarios=None,
            application_scenarios_en=None,
        )
        for _ in range(5)
    ]
    papers = [{"arxiv_id": f"focus-{index}", "_summary": summary} for index, summary in enumerate(summaries, start=1)]

    pipeline = Pipeline.__new__(Pipeline)
    pipeline._ensure_localized_title = lambda paper: None
    calls = []

    def fake_run_ai_batch(batch, category):
        calls.append([paper["arxiv_id"] for paper in batch])
        return (
            [
                {
                    "arxiv_id": paper["arxiv_id"],
                    "one_line_summary": f"中文 {paper['arxiv_id']}",
                    "one_line_summary_en": f"English {paper['arxiv_id']}",
                    "core_highlights": ["A1", "A2", "A3"],
                    "core_highlights_en": ["A1", "A2", "A3"],
                    "application_scenarios": "场景",
                    "application_scenarios_en": "Scenario",
                }
                for paper in batch
            ],
            [],
        )

    pipeline._run_ai_batch = fake_run_ai_batch

    processed_count = pipeline._process_category_batch(
        initial_batch=papers,
        overflow_batch=[],
        category="focus",
        target_count=5,
    )

    assert processed_count == 5
    assert calls == [["focus-1"], ["focus-2"], ["focus-3"], ["focus-4"], ["focus-5"]]


def test_process_category_batch_stops_when_attempt_cap_is_reached(monkeypatch):
    summaries = [
        SimpleNamespace(
            category="focus",
            candidate_reason=None,
            one_line_summary=None,
            one_line_summary_en=None,
            core_highlights=None,
            core_highlights_en=None,
            application_scenarios=None,
            application_scenarios_en=None,
        )
        for _ in range(8)
    ]
    papers = [{"arxiv_id": f"focus-{index}", "_summary": summary} for index, summary in enumerate(summaries, start=1)]

    pipeline = Pipeline.__new__(Pipeline)
    pipeline._ensure_localized_title = lambda paper: None
    calls = []

    def always_fail(batch, category):
        calls.append(batch[0]["arxiv_id"])
        raise RuntimeError("rate limit")

    pipeline._run_ai_batch = always_fail

    monkeypatch.setattr(settings, "PIPELINE_MAX_CATEGORY_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "PIPELINE_FOCUS_ATTEMPT_MULTIPLIER", 10)

    processed_count = pipeline._process_category_batch(
        initial_batch=papers[:5],
        overflow_batch=papers[5:],
        category="focus",
        target_count=5,
    )

    assert processed_count == 0
    assert calls == ["focus-1", "focus-2", "focus-3"]


def test_run_ai_batch_accepts_reviewer_rejections_in_non_strict_mode(monkeypatch):
    paper = {
        "arxiv_id": "focus-1",
        "_summary": SimpleNamespace(id=1),
    }
    writer_record = {
        "arxiv_id": "focus-1",
        "content": "writer content",
        "one_line_summary": "中文总结",
        "one_line_summary_en": "English summary",
        "core_highlights": ["亮点1", "亮点2", "亮点3"],
        "core_highlights_en": ["Point1", "Point2", "Point3"],
        "application_scenarios": "中文场景",
        "application_scenarios_en": "English scenario",
    }

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.db = SimpleNamespace(add=lambda *_args, **_kwargs: None, flush=lambda: None)
    pipeline._record_editor_traces = lambda *args, **kwargs: None
    pipeline._record_uniform_stage_traces = lambda *args, **kwargs: None
    pipeline._record_writer_traces = lambda *args, **kwargs: None
    pipeline._record_reviewer_traces = lambda *args, **kwargs: None

    pipeline.ai_processor = SimpleNamespace(
        run_editor=lambda papers, category: "editor-output",
        parse_editor_records=lambda editor_output, papers: [
            {
                "arxiv_id": "focus-1",
                "writing_angle": "angle",
                "core_problem": "problem",
                "solution": "solution",
                "content": "editor-content",
            }
        ],
        run_writer=lambda **kwargs: "writer-output",
        parse_writer_records=lambda writer_output, papers, category: [writer_record],
        run_reviewer=lambda writer_output: {
            "status": "REJECTED",
            "rejected_ids": ["focus-1"],
            "raw_output": "- **整体结论**: REJECTED\n- **拒绝名单**: [focus-1]",
        },
    )

    monkeypatch.setattr(settings, "PIPELINE_REVIEWER_STRICT", False)

    parsed_results, rejected_ids = pipeline._run_ai_batch([paper], "focus")

    assert rejected_ids == []
    assert len(parsed_results) == 1
    assert parsed_results[0]["arxiv_id"] == "focus-1"
    assert parsed_results[0]["one_line_summary"] == "中文总结"


def test_run_ai_batch_accepts_reviewer_invalid_output_in_non_strict_mode(monkeypatch):
    paper = {
        "arxiv_id": "focus-2",
        "_summary": SimpleNamespace(id=2),
    }
    writer_record = {
        "arxiv_id": "focus-2",
        "content": "writer content",
        "one_line_summary": "中文总结",
        "one_line_summary_en": "English summary",
        "core_highlights": ["亮点1", "亮点2", "亮点3"],
        "core_highlights_en": ["Point1", "Point2", "Point3"],
        "application_scenarios": "中文场景",
        "application_scenarios_en": "English scenario",
    }

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.db = SimpleNamespace(add=lambda *_args, **_kwargs: None, flush=lambda: None)
    pipeline._record_editor_traces = lambda *args, **kwargs: None
    pipeline._record_uniform_stage_traces = lambda *args, **kwargs: None
    pipeline._record_writer_traces = lambda *args, **kwargs: None
    pipeline._record_reviewer_traces = lambda *args, **kwargs: None

    pipeline.ai_processor = SimpleNamespace(
        run_editor=lambda papers, category: "editor-output",
        parse_editor_records=lambda editor_output, papers: [
            {
                "arxiv_id": "focus-2",
                "writing_angle": "angle",
                "core_problem": "problem",
                "solution": "solution",
                "content": "editor-content",
            }
        ],
        run_writer=lambda **kwargs: "writer-output",
        parse_writer_records=lambda writer_output, papers, category: [writer_record],
        run_reviewer=lambda writer_output: (_ for _ in ()).throw(
            StructuredOutputError("bad reviewer", "garbled reviewer output")
        ),
    )

    monkeypatch.setattr(settings, "PIPELINE_REVIEWER_STRICT", False)

    parsed_results, rejected_ids = pipeline._run_ai_batch([paper], "focus")

    assert rejected_ids == []
    assert len(parsed_results) == 1
    assert parsed_results[0]["arxiv_id"] == "focus-2"


def test_run_ai_batch_requeues_full_agent_pipeline_after_reviewer_rejection(monkeypatch):
    paper = {
        "arxiv_id": "focus-requeue",
        "_summary": SimpleNamespace(id=3),
    }
    writer_record = {
        "arxiv_id": "focus-requeue",
        "content": "writer content",
        "one_line_summary": "中文总结",
        "one_line_summary_en": "English summary",
        "core_highlights": ["亮点1", "亮点2", "亮点3"],
        "core_highlights_en": ["Point1", "Point2", "Point3"],
        "application_scenarios": "中文场景",
        "application_scenarios_en": "English scenario",
    }

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.db = SimpleNamespace(add=lambda *_args, **_kwargs: None, flush=lambda: None)
    pipeline._record_editor_traces = lambda *args, **kwargs: None
    pipeline._record_uniform_stage_traces = lambda *args, **kwargs: None
    pipeline._record_writer_traces = lambda *args, **kwargs: None
    pipeline._record_reviewer_traces = lambda *args, **kwargs: None
    pipeline._send_reviewer_exhausted_alert = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("exhaustion alert should not fire on successful retry")
    )

    editor_feedback = []
    reviewer_calls = {"count": 0}

    def fake_run_editor(papers, category, retry_feedback=None):
        editor_feedback.append(retry_feedback)
        return f"editor-output-{len(editor_feedback)}"

    def fake_run_reviewer(writer_output):
        reviewer_calls["count"] += 1
        if reviewer_calls["count"] <= 3:
            return {
                "status": "REJECTED",
                "rejected_ids": ["focus-requeue"],
                "raw_output": "- **整体结论**: REJECTED\n- **拒绝名单**: [focus-requeue]",
            }
        return {
            "status": "PASSED",
            "rejected_ids": [],
            "raw_output": "- **整体结论**: PASSED\n- **拒绝名单**: []",
        }

    pipeline.ai_processor = SimpleNamespace(
        run_editor=fake_run_editor,
        parse_editor_records=lambda editor_output, papers: [
            {
                "arxiv_id": "focus-requeue",
                "writing_angle": "angle",
                "core_problem": "problem",
                "solution": "solution",
                "content": f"editor::{editor_output}",
            }
        ],
        run_writer=lambda **kwargs: "writer-output",
        parse_writer_records=lambda writer_output, papers, category: [writer_record],
        run_reviewer=fake_run_reviewer,
    )

    monkeypatch.setattr(settings, "PIPELINE_REVIEWER_STRICT", True)
    monkeypatch.setattr(settings, "PIPELINE_REVIEW_REQUEUE_ATTEMPTS", 5)

    parsed_results, rejected_ids = pipeline._run_ai_batch([paper], "focus")

    assert rejected_ids == []
    assert len(parsed_results) == 1
    assert editor_feedback[0] is None
    assert "Reviewer 原始结论如下" in editor_feedback[1]
    assert "focus-requeue" in editor_feedback[1]
    assert reviewer_calls["count"] == 4


def test_run_ai_batch_sends_owner_alert_when_review_requeue_attempts_are_exhausted(monkeypatch):
    paper = {
        "arxiv_id": "focus-exhausted",
        "_summary": SimpleNamespace(id=4, issue_date=date(2026, 4, 18)),
    }
    writer_record = {
        "arxiv_id": "focus-exhausted",
        "content": "writer content",
        "one_line_summary": "中文总结",
        "one_line_summary_en": "English summary",
        "core_highlights": ["亮点1", "亮点2", "亮点3"],
        "core_highlights_en": ["Point1", "Point2", "Point3"],
        "application_scenarios": "中文场景",
        "application_scenarios_en": "English scenario",
    }

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.db = SimpleNamespace(add=lambda *_args, **_kwargs: None, flush=lambda: None)
    pipeline._record_editor_traces = lambda *args, **kwargs: None
    pipeline._record_uniform_stage_traces = lambda *args, **kwargs: None
    pipeline._record_writer_traces = lambda *args, **kwargs: None
    pipeline._record_reviewer_traces = lambda *args, **kwargs: None

    alert_calls = []
    pipeline._send_reviewer_exhausted_alert = lambda **kwargs: alert_calls.append(kwargs)

    pipeline.ai_processor = SimpleNamespace(
        run_editor=lambda papers, category, retry_feedback=None: "editor-output",
        parse_editor_records=lambda editor_output, papers: [
            {
                "arxiv_id": "focus-exhausted",
                "writing_angle": "angle",
                "core_problem": "problem",
                "solution": "solution",
                "content": "editor-content",
            }
        ],
        run_writer=lambda **kwargs: "writer-output",
        parse_writer_records=lambda writer_output, papers, category: [writer_record],
        run_reviewer=lambda writer_output: {
            "status": "REJECTED",
            "rejected_ids": ["focus-exhausted"],
            "raw_output": "- **整体结论**: REJECTED\n- **拒绝名单**: [focus-exhausted]",
        },
    )

    monkeypatch.setattr(settings, "PIPELINE_REVIEWER_STRICT", True)
    monkeypatch.setattr(settings, "PIPELINE_REVIEW_REQUEUE_ATTEMPTS", 2)

    parsed_results, rejected_ids = pipeline._run_ai_batch([paper], "focus")

    assert parsed_results == []
    assert rejected_ids == ["focus-exhausted"]
    assert len(alert_calls) == 1
    assert alert_calls[0]["exhausted_attempts"] == 2
    assert alert_calls[0]["rejected_ids"] == ["focus-exhausted"]


def test_max_category_attempts_respects_target_multiplier_and_global_cap(monkeypatch):
    monkeypatch.setattr(settings, "PIPELINE_MAX_CATEGORY_ATTEMPTS", 25)
    monkeypatch.setattr(settings, "PIPELINE_FOCUS_ATTEMPT_MULTIPLIER", 4)
    monkeypatch.setattr(settings, "PIPELINE_WATCHING_ATTEMPT_MULTIPLIER", 2)

    assert Pipeline._max_category_attempts("focus", target_count=5, queued_count=200) == 20
    assert Pipeline._max_category_attempts("watching", target_count=12, queued_count=200) == 24
    assert Pipeline._max_category_attempts("focus", target_count=8, queued_count=10) == 10


def test_record_uniform_stage_traces_offsets_invalid_attempt_number():
    collected = []

    class FakeDB:
        @staticmethod
        def add(obj):
            collected.append(obj)

        @staticmethod
        def flush():
            return None

    pipeline = Pipeline.__new__(Pipeline)
    pipeline.db = FakeDB()

    pipeline._record_uniform_stage_traces(
        papers=[{"_summary": SimpleNamespace(id=123)}],
        stage="writer",
        stage_status="invalid",
        attempt_no=2,
        content="invalid output",
    )

    assert len(collected) == 1
    assert collected[0].attempt_no == 21


def test_refresh_selected_titles_updates_all_issue_fallbacks(db_session):
    issue_date = Pipeline._resolve_issue_date("2026-03-27")
    focus_paper = Paper(
        arxiv_id="2603.00001",
        title_zh="待翻译：Agentic Planning for Production",
        title_original="Agentic Planning for Production",
        authors=[{"name": "Alice", "affiliation": "OpenAI"}],
        venue="ICLR 2026",
        abstract="demo",
        pdf_url="https://arxiv.org/pdf/2603.00001.pdf",
        upvotes=12,
        arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-24"),
    )
    candidate_paper = Paper(
        arxiv_id="2603.00002",
        title_zh="待翻译：Long Horizon Training Signals",
        title_original="Long Horizon Training Signals",
        authors=[{"name": "Bob", "affiliation": "CMU"}],
        venue="arXiv",
        abstract="demo",
        pdf_url="https://arxiv.org/pdf/2603.00002.pdf",
        upvotes=3,
        arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-24"),
    )
    db_session.add_all([focus_paper, candidate_paper])
    db_session.flush()

    focus_summary = PaperSummary(
        paper_id=focus_paper.id,
        issue_date=issue_date,
        score=91,
        score_reasons={},
        category="focus",
        candidate_reason=None,
        direction="Agent",
    )
    candidate_summary = PaperSummary(
        paper_id=candidate_paper.id,
        issue_date=issue_date,
        score=47,
        score_reasons={},
        category="candidate",
        candidate_reason="low_score",
        direction="Agent",
    )
    db_session.add_all([focus_summary, candidate_summary])
    db_session.commit()

    pipeline = Pipeline(db_session)
    pipeline.ai_processor.localize_titles = lambda papers, batch_size=None, progress_callback=None: {
        paper["arxiv_id"]: (
            "面向生产的智能体规划"
            if paper["arxiv_id"] == "2603.00001"
            else "长周期训练信号"
        )
        for paper in papers
    }

    updated = pipeline._refresh_selected_titles(issue_date)
    db_session.refresh(focus_paper)
    db_session.refresh(candidate_paper)

    assert updated == 2
    assert focus_paper.title_zh == "面向生产的智能体规划"
    assert candidate_paper.title_zh == "长周期训练信号"


def test_refresh_selected_titles_emits_batch_progress_logs(db_session, monkeypatch):
    issue_date = Pipeline._resolve_issue_date("2026-03-27")
    papers = [
        Paper(
            arxiv_id=f"2603.1000{index}",
            title_zh=f"待翻译：Title {index}",
            title_original=f"Title {index}",
            authors=[{"name": f"Author {index}", "affiliation": "OpenAI"}],
            venue="arXiv",
            abstract="demo",
            pdf_url=f"https://arxiv.org/pdf/2603.1000{index}.pdf",
            upvotes=index,
            arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-24"),
        )
        for index in range(1, 4)
    ]
    db_session.add_all(papers)
    db_session.flush()
    db_session.add_all(
        [
            PaperSummary(
                paper_id=paper.id,
                issue_date=issue_date,
                score=50,
                score_reasons={},
                category="candidate",
                candidate_reason="low_score",
                direction="Agent",
            )
            for paper in papers
        ]
    )
    db_session.commit()

    logs = []
    monkeypatch.setattr(settings, "KIMI_TITLE_BATCH_SIZE", 2)
    monkeypatch.setattr(pipeline_module, "_safe_progress_log", logs.append)

    pipeline = Pipeline(db_session)

    def fake_localize_titles(payload, batch_size=None, progress_callback=None):
        if progress_callback is not None:
            progress_callback(1, 2, 2)
            progress_callback(2, 2, 1)
        return {paper["arxiv_id"]: f"中文标题 {paper['arxiv_id']}" for paper in payload}

    pipeline.ai_processor.localize_titles = fake_localize_titles

    updated = pipeline._refresh_selected_titles(issue_date)

    assert updated == 3
    assert logs == [
        "[pipeline][title-refresh] issue_date=2026-03-27 batch=1/2 size=2 total=3",
        "[pipeline][title-refresh] issue_date=2026-03-27 batch=2/2 size=1 total=3",
    ]


def test_run_ai_batch_persists_editor_writer_and_reviewer_traces(db_session):
    paper = Paper(
        arxiv_id="2503.22001",
        title_zh="测试标题",
        title_original="Test Title",
        authors=[{"name": "Alice", "affiliation": "OpenAI"}],
        venue="ICLR 2026",
        abstract="Test abstract",
        pdf_url="https://arxiv.org/pdf/2503.22001.pdf",
        upvotes=10,
        arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-20"),
    )
    db_session.add(paper)
    db_session.flush()

    summary = PaperSummary(
        paper_id=paper.id,
        issue_date=Pipeline._resolve_issue_date("2026-03-23"),
        score=95,
        score_reasons={},
        category="focus",
        candidate_reason=None,
        direction="Agent",
    )
    db_session.add(summary)
    db_session.flush()

    pipeline = Pipeline(db_session)
    pipeline.ai_processor.run_editor = lambda papers, category: "editor-output"
    pipeline.ai_processor.parse_editor_records = lambda output, papers: [
        {
            "arxiv_id": "2503.22001",
            "writing_angle": "生产落地",
            "core_problem": "推理链路不稳",
            "solution": "统一编排",
            "content": "## 论文: [2503.22001]\n- **写作角度**: 生产落地",
        }
    ]
    pipeline.ai_processor.run_writer = lambda editor_brief, papers_metadata, category, history=None: "writer-output"
    pipeline.ai_processor.parse_writer_records = lambda writer_output, papers_metadata, category: [
        {
            "arxiv_id": "2503.22001",
            "one_line_summary": "中文总结",
            "one_line_summary_en": "English summary",
            "core_highlights": ["亮点一", "亮点二", "亮点三"],
            "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
            "application_scenarios": "中文场景",
            "application_scenarios_en": "English scenario",
            "content": "## [2503.22001]\n- **一句话总结**: 中文总结",
        }
    ]
    pipeline.ai_processor.run_reviewer = lambda writer_output: {
        "status": "PASSED",
        "rejected_ids": [],
        "raw_output": "- **整体结论**: PASSED\n- **拒绝名单**: []",
    }

    results, rejected_ids = pipeline._run_ai_batch(
        [{"arxiv_id": "2503.22001", "_summary": summary}],
        "focus",
    )

    traces = (
        db_session.query(PaperAITrace)
        .filter(PaperAITrace.paper_summary_id == summary.id)
        .order_by(PaperAITrace.id.asc())
        .all()
    )

    assert rejected_ids == []
    assert results[0]["one_line_summary"] == "中文总结"
    assert [trace.stage for trace in traces] == ["editor", "writer", "reviewer"]
    assert traces[2].stage_status == "accepted"
    assert traces[1].content.startswith("## [2503.22001]")


def test_run_ai_batch_emits_stage_progress_logs(db_session, monkeypatch):
    paper = Paper(
        arxiv_id="2503.22003",
        title_zh="测试标题三",
        title_original="Test Title Three",
        authors=[{"name": "Cara", "affiliation": "OpenAI"}],
        venue="ICLR 2026",
        abstract="Test abstract",
        pdf_url="https://arxiv.org/pdf/2503.22003.pdf",
        upvotes=10,
        arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-20"),
    )
    db_session.add(paper)
    db_session.flush()

    summary = PaperSummary(
        paper_id=paper.id,
        issue_date=Pipeline._resolve_issue_date("2026-03-23"),
        score=95,
        score_reasons={},
        category="focus",
        candidate_reason=None,
        direction="Agent",
    )
    db_session.add(summary)
    db_session.flush()

    logs = []
    monkeypatch.setattr(pipeline_module, "_safe_progress_log", logs.append)

    pipeline = Pipeline(db_session)
    pipeline.ai_processor.run_editor = lambda papers, category: "editor-output"
    pipeline.ai_processor.parse_editor_records = lambda output, papers: [
        {
            "arxiv_id": "2503.22003",
            "writing_angle": "生产落地",
            "core_problem": "推理链路不稳",
            "solution": "统一编排",
            "content": "## 论文: [2503.22003]\n- **写作角度**: 生产落地",
        }
    ]
    pipeline.ai_processor.run_writer = lambda editor_brief, papers_metadata, category, history=None: "writer-output"
    pipeline.ai_processor.parse_writer_records = lambda writer_output, papers_metadata, category: [
        {
            "arxiv_id": "2503.22003",
            "one_line_summary": "中文总结",
            "one_line_summary_en": "English summary",
            "core_highlights": ["亮点一", "亮点二", "亮点三"],
            "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
            "application_scenarios": "中文场景",
            "application_scenarios_en": "English scenario",
            "content": "## [2503.22003]\n- **一句话总结**: 中文总结",
        }
    ]
    pipeline.ai_processor.run_reviewer = lambda writer_output: {
        "status": "PASSED",
        "rejected_ids": [],
        "raw_output": "- **整体结论**: PASSED\n- **拒绝名单**: []",
    }

    results, rejected_ids = pipeline._run_ai_batch(
        [{"arxiv_id": "2503.22003", "_summary": summary}],
        "focus",
    )

    assert rejected_ids == []
    assert results[0]["one_line_summary"] == "中文总结"
    assert logs == [
        "[pipeline][focus][2503.22003][editor] start attempt=1",
        "[pipeline][focus][2503.22003][editor] generated attempt=1",
        "[pipeline][focus][2503.22003][writer] start attempt=1",
        "[pipeline][focus][2503.22003][writer] generated attempt=1",
        "[pipeline][focus][2503.22003][reviewer] start attempt=1",
        "[pipeline][focus][2503.22003][reviewer] accepted attempt=1",
    ]


def test_run_ai_batch_persists_invalid_attempt_traces(db_session):
    paper = Paper(
        arxiv_id="2503.22002",
        title_zh="测试标题二",
        title_original="Test Title Two",
        authors=[{"name": "Bob", "affiliation": "OpenAI"}],
        venue="ICLR 2026",
        abstract="Test abstract",
        pdf_url="https://arxiv.org/pdf/2503.22002.pdf",
        upvotes=10,
        arxiv_publish_date=Pipeline._resolve_issue_date("2026-03-20"),
    )
    db_session.add(paper)
    db_session.flush()

    summary = PaperSummary(
        paper_id=paper.id,
        issue_date=Pipeline._resolve_issue_date("2026-03-23"),
        score=95,
        score_reasons={},
        category="focus",
        candidate_reason=None,
        direction="Agent",
    )
    db_session.add(summary)
    db_session.flush()

    pipeline = Pipeline(db_session)
    editor_attempts = {"count": 0}
    writer_attempts = {"count": 0}
    reviewer_attempts = {"count": 0}

    def fake_run_editor(papers, category):
        editor_attempts["count"] += 1
        if editor_attempts["count"] == 1:
            raise StructuredOutputError("Editor zero-prefix failure", "bad editor output")
        return "editor-output"

    def fake_run_writer(editor_brief, papers_metadata, category, history=None):
        writer_attempts["count"] += 1
        if writer_attempts["count"] == 1:
            raise StructuredOutputError("Writer format failure", "bad writer output")
        return f"writer-output-{writer_attempts['count']}"

    def fake_run_reviewer(writer_output):
        reviewer_attempts["count"] += 1
        if reviewer_attempts["count"] == 1:
            raise StructuredOutputError("Reviewer wrapper noise", "bad reviewer output")
        return {
            "status": "PASSED",
            "rejected_ids": [],
            "raw_output": "- **整体结论**: PASSED\n- **拒绝名单**: []",
        }

    pipeline.ai_processor.run_editor = fake_run_editor
    pipeline.ai_processor.parse_editor_records = lambda output, papers: [
        {
            "arxiv_id": "2503.22002",
            "writing_angle": "生产落地",
            "core_problem": "推理链路不稳",
            "solution": "统一编排",
            "content": "## 论文: [2503.22002]\n- **写作角度**: 生产落地",
        }
    ]
    pipeline.ai_processor.run_writer = fake_run_writer
    pipeline.ai_processor.parse_writer_records = lambda writer_output, papers_metadata, category: [
        {
            "arxiv_id": "2503.22002",
            "one_line_summary": f"中文总结 {writer_output}",
            "one_line_summary_en": f"English summary {writer_output}",
            "core_highlights": ["亮点一", "亮点二", "亮点三"],
            "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
            "application_scenarios": "中文场景",
            "application_scenarios_en": "English scenario",
            "content": f"## [2503.22002]\n- **一句话总结**: 中文总结 {writer_output}",
        }
    ]
    pipeline.ai_processor.run_reviewer = fake_run_reviewer
    pipeline.ai_processor.repair_editor_output = (
        lambda raw_output, papers, category: (_ for _ in ()).throw(ValueError("repair failed"))
    )
    pipeline.ai_processor.repair_writer_output = (
        lambda raw_output, papers_metadata, category: (_ for _ in ()).throw(ValueError("repair failed"))
    )
    pipeline.ai_processor.repair_reviewer_output = (
        lambda raw_output, writer_output: (_ for _ in ()).throw(ValueError("repair failed"))
    )

    results, rejected_ids = pipeline._run_ai_batch(
        [{"arxiv_id": "2503.22002", "_summary": summary}],
        "focus",
    )

    traces = (
        db_session.query(PaperAITrace)
        .filter(PaperAITrace.paper_summary_id == summary.id)
        .order_by(PaperAITrace.id.asc())
        .all()
    )

    assert rejected_ids == []
    assert results[0]["one_line_summary"] == "中文总结 writer-output-3"
    assert [(trace.stage, trace.attempt_no, trace.stage_status) for trace in traces] == [
        ("editor", 11, "invalid"),
        ("editor", 2, "generated"),
        ("writer", 11, "invalid"),
        ("writer", 2, "generated"),
        ("reviewer", 21, "invalid"),
        ("writer", 3, "generated"),
        ("reviewer", 3, "accepted"),
    ]
    assert traces[0].content == "bad editor output"
    assert traces[2].content == "bad writer output"
    assert traces[4].content == "bad reviewer output"


def test_run_uses_quantity_first_fallback_when_supply_is_insufficient(db_session):
    pipeline = Pipeline(db_session)
    pipeline.crawler.fetch_papers = lambda fetch_date: [
        {"arxiv_id": "paper-focus"},
        {"arxiv_id": "paper-watch"},
    ]
    pipeline.scorer.score_paper = lambda paper: {
        "arxiv_id": paper["arxiv_id"],
        "title_original": paper["arxiv_id"],
        "authors": [],
        "venue": None,
        "abstract": "",
        "pdf_url": "https://arxiv.org/pdf/example.pdf",
        "upvotes": 0,
        "arxiv_publish_date": "2026-03-20",
        "score": 90 if paper["arxiv_id"] == "paper-focus" else 60,
        "score_reasons": {},
        "direction": "Agent",
    }

    localized_ids = []
    ai_calls = []
    pipeline.ai_processor.localize_title = lambda paper: (
        localized_ids.append(paper["arxiv_id"]) or f"中文标题 {paper['arxiv_id']}"
    )
    pipeline._run_ai_batch = lambda papers, category: (
        ai_calls.append((category, [paper["arxiv_id"] for paper in papers])) or
        (
            [
                {
                    "arxiv_id": paper["arxiv_id"],
                    "one_line_summary": f"中文总结 {paper['arxiv_id']}",
                    "one_line_summary_en": f"English summary {paper['arxiv_id']}",
                    "core_highlights": ["亮点一", "亮点二", "亮点三"],
                    "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
                    "application_scenarios": f"场景 {paper['arxiv_id']}",
                    "application_scenarios_en": f"Scenario {paper['arxiv_id']}",
                }
                for paper in papers
            ],
            [],
        )
    )

    pipeline.run("2026-03-23")

    task_log = (
        db_session.query(SystemTaskLog)
        .filter(SystemTaskLog.issue_date == Pipeline._resolve_issue_date("2026-03-23"))
        .one()
    )
    summaries = (
        db_session.query(PaperSummary)
        .filter(PaperSummary.issue_date == Pipeline._resolve_issue_date("2026-03-23"))
        .all()
    )

    assert localized_ids == ["paper-focus", "paper-watch"]
    assert ai_calls == [("focus", ["paper-focus"]), ("focus", ["paper-watch"])]
    assert task_log.status == "SUCCESS"
    assert task_log.processed_count == 2
    assert len(summaries) == 2
    assert all(summary.category == "focus" for summary in summaries)


def test_run_requeues_full_agent_pipeline_after_reviewer_rejections_until_success(db_session, monkeypatch):
    pipeline = Pipeline(db_session)
    pipeline.crawler.fetch_papers = lambda fetch_date: [
        {
            "arxiv_id": "paper-review-requeue",
            "title_original": "Reviewer Requeue Paper",
            "authors": [{"name": "Alice", "affiliation": "OpenAI"}],
            "venue": "ICLR 2026",
            "abstract": "A pipeline test abstract",
            "pdf_url": "https://arxiv.org/pdf/paper-review-requeue.pdf",
            "upvotes": 42,
            "arxiv_publish_date": "2026-03-20",
        }
    ]
    pipeline.scorer.score_paper = lambda paper: {
        "arxiv_id": paper["arxiv_id"],
        "title_original": paper["title_original"],
        "authors": paper["authors"],
        "venue": paper["venue"],
        "abstract": paper["abstract"],
        "pdf_url": paper["pdf_url"],
        "upvotes": paper["upvotes"],
        "arxiv_publish_date": paper["arxiv_publish_date"],
        "score": 95,
        "score_reasons": {"hf_recommend": 30},
        "direction": "Agent",
    }

    editor_feedback = []
    reviewer_calls = {"count": 0}

    pipeline.ai_processor.localize_title = lambda paper: "评审重排论文"
    pipeline.ai_processor.localize_titles = lambda papers, batch_size=None, progress_callback=None: {
        paper["arxiv_id"]: "评审重排论文" for paper in papers
    }

    def fake_run_editor(papers, category, retry_feedback=None):
        editor_feedback.append(retry_feedback)
        return f"editor-output-{len(editor_feedback)}"

    pipeline.ai_processor.run_editor = fake_run_editor
    pipeline.ai_processor.parse_editor_records = lambda editor_output, papers: [
        {
            "arxiv_id": "paper-review-requeue",
            "writing_angle": "angle",
            "core_problem": "problem",
            "solution": "solution",
            "content": f"editor::{editor_output}",
        }
    ]
    pipeline.ai_processor.run_writer = lambda editor_brief, papers_metadata, category, history=None: "writer-output"
    pipeline.ai_processor.parse_writer_records = lambda writer_output, papers, category: [
        {
            "arxiv_id": "paper-review-requeue",
            "one_line_summary": "中文总结",
            "one_line_summary_en": "English summary",
            "core_highlights": ["亮点1", "亮点2", "亮点3"],
            "core_highlights_en": ["Point1", "Point2", "Point3"],
            "application_scenarios": "中文场景",
            "application_scenarios_en": "English scenario",
            "content": "## [paper-review-requeue]\n- **一句话总结**: 中文总结",
        }
    ]

    def fake_run_reviewer(writer_output):
        reviewer_calls["count"] += 1
        if reviewer_calls["count"] <= 3:
            return {
                "status": "REJECTED",
                "rejected_ids": ["paper-review-requeue"],
                "raw_output": "- **整体结论**: REJECTED\n- **拒绝名单**: [paper-review-requeue]",
            }
        return {
            "status": "PASSED",
            "rejected_ids": [],
            "raw_output": "- **整体结论**: PASSED\n- **拒绝名单**: []",
        }

    pipeline.ai_processor.run_reviewer = fake_run_reviewer

    monkeypatch.setattr(settings, "PIPELINE_ENABLE_WATCHING", False)
    monkeypatch.setattr(settings, "PIPELINE_REVIEWER_STRICT", True)
    monkeypatch.setattr(settings, "PIPELINE_REVIEW_REQUEUE_ATTEMPTS", 5)

    pipeline.run("2026-03-23")

    issue_date = Pipeline._resolve_issue_date("2026-03-23")
    task_log = (
        db_session.query(SystemTaskLog)
        .filter(SystemTaskLog.issue_date == issue_date)
        .one()
    )
    summary = (
        db_session.query(PaperSummary)
        .join(Paper)
        .filter(PaperSummary.issue_date == issue_date, Paper.arxiv_id == "paper-review-requeue")
        .one()
    )

    assert task_log.status == "SUCCESS"
    assert task_log.processed_count == 1
    assert summary.category == "focus"
    assert summary.one_line_summary == "中文总结"
    assert editor_feedback[0] is None
    assert "Reviewer 原始结论如下" in editor_feedback[1]
    assert reviewer_calls["count"] == 4


def test_fetch_with_backtrack_uses_previous_available_date(db_session, monkeypatch):
    pipeline = Pipeline(db_session)
    calls = []

    def fake_fetch(fetch_date):
        calls.append(fetch_date)
        if fetch_date == "2026-02-13":
            return [{"arxiv_id": "paper-available"}]
        return []

    pipeline.crawler.fetch_papers = fake_fetch
    monkeypatch.setattr(settings, "PIPELINE_FETCH_BACKTRACK_DAYS", 3)

    papers, resolved_date = pipeline._fetch_with_backtrack(date(2026, 2, 15))

    assert papers == [{"arxiv_id": "paper-available"}]
    assert resolved_date.isoformat() == "2026-02-13"
    assert calls == ["2026-02-15", "2026-02-14", "2026-02-13"]


def test_quantity_first_pipeline_uses_full_snapshots_and_standard_ai_batches(db_session):
    pipeline = Pipeline(db_session)
    raw_ids = [f"paper-{index}" for index in range(11)]
    score_map = {
        "paper-0": 95,
        "paper-1": 92,
        "paper-2": 89,
        "paper-3": 79,
        "paper-4": 78,
        "paper-5": 77,
        "paper-6": 76,
        "paper-7": 75,
        "paper-8": 74,
        "paper-9": 73,
        "paper-10": 72,
    }

    pipeline.crawler.fetch_papers = lambda fetch_date: [
        {"arxiv_id": paper_id} for paper_id in raw_ids
    ]
    pipeline.scorer.score_paper = lambda paper: {
        "arxiv_id": paper["arxiv_id"],
        "title_original": f"Original {paper['arxiv_id']}",
        "authors": [{"name": "Author", "affiliation": "OpenAI"}],
        "venue": "ICLR 2026" if score_map[paper["arxiv_id"]] >= 80 else None,
        "abstract": f"Abstract {paper['arxiv_id']}",
        "pdf_url": f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf",
        "upvotes": 0,
        "arxiv_publish_date": "2026-03-20",
        "score": score_map[paper["arxiv_id"]],
        "score_reasons": {},
        "direction": "Agent",
    }

    localized_ids = []
    ai_calls = []

    def fake_localize_title(paper):
        localized_ids.append(paper["arxiv_id"])
        return f"中文标题 {paper['arxiv_id']}"

    def fake_run_ai_batch(papers, category):
        ai_calls.append((category, [paper["arxiv_id"] for paper in papers]))
        return (
            [
                {
                    "arxiv_id": paper["arxiv_id"],
                    "one_line_summary": f"中文总结 {paper['arxiv_id']}",
                    "one_line_summary_en": f"English summary {paper['arxiv_id']}",
                    "core_highlights": ["亮点一", "亮点二", "亮点三"],
                    "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
                    "application_scenarios": f"场景 {paper['arxiv_id']}",
                    "application_scenarios_en": f"Scenario {paper['arxiv_id']}",
                }
                for paper in papers
            ],
            [],
        )

    pipeline.ai_processor.localize_title = fake_localize_title
    pipeline._run_ai_batch = fake_run_ai_batch

    pipeline.run("2026-03-23")

    issue_date = Pipeline._resolve_issue_date("2026-03-23")
    task_log = (
        db_session.query(SystemTaskLog)
        .filter(SystemTaskLog.issue_date == issue_date)
        .one()
    )
    summaries = (
        db_session.query(PaperSummary)
        .filter(PaperSummary.issue_date == issue_date)
        .all()
    )

    assert task_log.status == "SUCCESS"
    assert task_log.processed_count == 11
    assert localized_ids == raw_ids
    assert ai_calls == [
        ("focus", ["paper-0"]),
        ("focus", ["paper-1"]),
        ("focus", ["paper-2"]),
        ("focus", ["paper-3"]),
        ("focus", ["paper-4"]),
        ("watching", ["paper-5"]),
        ("watching", ["paper-6"]),
        ("watching", ["paper-7"]),
        ("watching", ["paper-8"]),
        ("watching", ["paper-9"]),
        ("watching", ["paper-10"]),
    ]
    assert len(summaries) == 11
    assert sum(1 for summary in summaries if summary.category == "focus") == 5
    assert sum(1 for summary in summaries if summary.category == "watching") == 6


def test_run_persists_full_daily_snapshot_for_candidate_pool(db_session):
    pipeline = Pipeline(db_session)
    raw_ids = [f"paper-{index:02d}" for index in range(60)]
    score_map = {paper_id: 200 - index for index, paper_id in enumerate(raw_ids)}

    pipeline.crawler.fetch_papers = lambda fetch_date: [{"arxiv_id": paper_id} for paper_id in raw_ids]
    pipeline.scorer.score_paper = lambda paper: {
        "arxiv_id": paper["arxiv_id"],
        "title_original": f"Original {paper['arxiv_id']}",
        "authors": [{"name": "Author", "affiliation": "OpenAI"}],
        "venue": "ICLR 2026",
        "abstract": f"Abstract {paper['arxiv_id']}",
        "pdf_url": f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf",
        "upvotes": 0,
        "arxiv_publish_date": "2026-03-20",
        "score": score_map[paper["arxiv_id"]],
        "score_reasons": {},
        "direction": "Agent",
    }

    pipeline.ai_processor.localize_title = lambda paper: f"中文标题 {paper['arxiv_id']}"
    pipeline.ai_processor.localize_titles = lambda papers, batch_size=None, progress_callback=None: {
        paper["arxiv_id"]: f"候选中文标题 {paper['arxiv_id']}" for paper in papers
    }
    pipeline._run_ai_batch = lambda papers, category: (
        [
            {
                "arxiv_id": paper["arxiv_id"],
                "one_line_summary": f"中文总结 {paper['arxiv_id']}",
                "one_line_summary_en": f"English summary {paper['arxiv_id']}",
                "core_highlights": ["亮点一", "亮点二", "亮点三"],
                "core_highlights_en": ["Point 1", "Point 2", "Point 3"],
                "application_scenarios": f"场景 {paper['arxiv_id']}",
                "application_scenarios_en": f"Scenario {paper['arxiv_id']}",
            }
            for paper in papers
        ],
        [],
    )

    pipeline.run("2026-03-23")

    issue_date = Pipeline._resolve_issue_date("2026-03-23")
    task_log = (
        db_session.query(SystemTaskLog)
        .filter(SystemTaskLog.issue_date == issue_date)
        .one()
    )
    summaries = (
        db_session.query(PaperSummary, Paper.arxiv_id)
        .join(Paper, Paper.id == PaperSummary.paper_id)
        .filter(PaperSummary.issue_date == issue_date)
        .all()
    )

    snapshot_ids = {arxiv_id for _, arxiv_id in summaries}
    expected_ids = set(raw_ids)

    assert task_log.status == "SUCCESS"
    assert task_log.fetched_count == 60
    assert task_log.processed_count == 5
    assert len(summaries) == 60
    assert snapshot_ids == expected_ids
    assert "paper-50" in snapshot_ids
    assert "paper-59" in snapshot_ids
    assert sum(1 for summary, _ in summaries if summary.category == "focus") == 5
    assert sum(1 for summary, _ in summaries if summary.category == "candidate") == 55
