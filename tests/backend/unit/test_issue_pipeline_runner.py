from datetime import date

from app.models.domain import Paper, PaperAITrace, PaperSummary, SystemTaskLog
from app.services.issue_pipeline_runner import clear_issue_pipeline_state, run_issue_pipeline


def test_run_issue_pipeline_uses_shared_pipeline_entry(session_factory):
    executed = []

    class RecordingPipeline:
        def __init__(self, db):
            self.db = db

        def run(self, issue_date: str):
            executed.append(issue_date)
            self.db.add(
                SystemTaskLog(
                    issue_date=date.fromisoformat(issue_date),
                    status="SUCCESS",
                    fetched_count=11,
                    processed_count=5,
                )
            )
            self.db.commit()

    result = run_issue_pipeline(
        date(2026, 3, 27),
        session_factory=session_factory,
        pipeline_cls=RecordingPipeline,
    )

    assert executed == ["2026-03-27"]
    assert result["status"] == "SUCCESS"
    assert result["fetched_count"] == 11
    assert result["processed_count"] == 5


def test_clear_issue_pipeline_state_removes_only_issue_scoped_rows(session_factory):
    with session_factory() as db:
        paper = Paper(
            arxiv_id="2604.14001",
            title_zh="测试标题",
            title_original="Test Title",
            authors=[{"name": "Alice", "affiliation": "OpenAI"}],
            venue="ICLR 2026",
            abstract="test abstract",
            pdf_url="https://arxiv.org/pdf/2604.14001.pdf",
            upvotes=12,
            arxiv_publish_date=date(2026, 4, 10),
        )
        db.add(paper)
        db.flush()

        summary = PaperSummary(
            paper_id=paper.id,
            issue_date=date(2026, 4, 14),
            score=88,
            score_reasons={"hf_recommend": 30},
            category="focus",
            candidate_reason=None,
            direction="Agent",
        )
        db.add(summary)
        db.flush()

        db.add(
            PaperAITrace(
                paper_summary_id=summary.id,
                stage="editor",
                stage_status="generated",
                attempt_no=1,
                content="editor content",
            )
        )
        db.add(
            SystemTaskLog(
                issue_date=date(2026, 4, 14),
                status="FAILED",
                fetched_count=266,
                processed_count=5,
            )
        )
        db.commit()

    cleanup_result = clear_issue_pipeline_state(date(2026, 4, 14), session_factory=session_factory)

    assert cleanup_result == {
        "deleted_traces": 1,
        "deleted_summaries": 1,
        "deleted_tasks": 1,
    }

    with session_factory() as db:
        assert db.query(Paper).count() == 1
        assert db.query(PaperSummary).count() == 0
        assert db.query(PaperAITrace).count() == 0
        assert db.query(SystemTaskLog).count() == 0


def test_run_issue_pipeline_retries_once_after_cleanup(session_factory):
    executed = []

    class RecoveringPipeline:
        attempt = 0

        def __init__(self, db):
            self.db = db

        def run(self, issue_date: str):
            RecoveringPipeline.attempt += 1
            executed.append((RecoveringPipeline.attempt, issue_date))
            issue_date_value = date.fromisoformat(issue_date)

            if RecoveringPipeline.attempt == 1:
                paper = Paper(
                    arxiv_id="2604.14002",
                    title_zh="第一次尝试标题",
                    title_original="First Attempt Paper",
                    authors=[{"name": "Bob", "affiliation": "Stanford"}],
                    venue="NeurIPS 2026",
                    abstract="first attempt abstract",
                    pdf_url="https://arxiv.org/pdf/2604.14002.pdf",
                    upvotes=18,
                    arxiv_publish_date=date(2026, 4, 11),
                )
                self.db.add(paper)
                self.db.flush()

                summary = PaperSummary(
                    paper_id=paper.id,
                    issue_date=issue_date_value,
                    score=81,
                    score_reasons={"community_popularity": 20},
                    category="focus",
                    candidate_reason=None,
                    direction="Reasoning",
                )
                self.db.add(summary)
                self.db.flush()
                self.db.add(
                    PaperAITrace(
                        paper_summary_id=summary.id,
                        stage="editor",
                        stage_status="generated",
                        attempt_no=1,
                        content="stale editor output",
                    )
                )
                self.db.add(
                    SystemTaskLog(
                        issue_date=issue_date_value,
                        status="FAILED",
                        fetched_count=266,
                        processed_count=5,
                    )
                )
                self.db.commit()
                raise RuntimeError("transient failure after partial write")

            assert self.db.query(Paper).filter(Paper.arxiv_id == "2604.14002").count() == 1
            assert self.db.query(PaperSummary).filter(PaperSummary.issue_date == issue_date_value).count() == 0
            assert self.db.query(PaperAITrace).count() == 0
            assert self.db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == issue_date_value).count() == 0

            paper = self.db.query(Paper).filter(Paper.arxiv_id == "2604.14002").one()
            summary = PaperSummary(
                paper_id=paper.id,
                issue_date=issue_date_value,
                score=92,
                score_reasons={"top_conf": 25},
                category="focus",
                candidate_reason=None,
                direction="Reasoning",
            )
            self.db.add(summary)
            self.db.flush()
            self.db.add(
                PaperAITrace(
                    paper_summary_id=summary.id,
                    stage="editor",
                    stage_status="generated",
                    attempt_no=1,
                    content="fresh editor output",
                )
            )
            self.db.add(
                SystemTaskLog(
                    issue_date=issue_date_value,
                    status="SUCCESS",
                    fetched_count=266,
                    processed_count=5,
                )
            )
            self.db.commit()

    result = run_issue_pipeline(
        date(2026, 4, 14),
        session_factory=session_factory,
        pipeline_cls=RecoveringPipeline,
    )

    assert executed == [(1, "2026-04-14"), (2, "2026-04-14")]
    assert result["status"] == "SUCCESS"
    assert result["fetched_count"] == 266
    assert result["processed_count"] == 5

    with session_factory() as db:
        assert db.query(Paper).filter(Paper.arxiv_id == "2604.14002").count() == 1
        assert db.query(PaperSummary).filter(PaperSummary.issue_date == date(2026, 4, 14)).count() == 1
        assert db.query(PaperAITrace).count() == 1
        task = db.query(SystemTaskLog).filter(SystemTaskLog.issue_date == date(2026, 4, 14)).one()
        assert task.status == "SUCCESS"
