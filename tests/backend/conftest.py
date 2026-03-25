from datetime import date, datetime, timedelta, timezone
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.subscribe import rate_limit_store
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.models.domain import Paper, PaperAITrace, PaperSummary


@pytest.fixture(autouse=True)
def clear_rate_limit_store() -> Iterator[None]:
    rate_limit_store.clear()
    yield
    rate_limit_store.clear()


@pytest.fixture()
def db_engine(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def session_factory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture()
def db_session(session_factory) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(session_factory) -> Iterator[TestClient]:
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def sample_paper_payload():
    return {
        "arxiv_id": "2503.00001",
        "title_zh": "面向生产环境的智能体检索增强生成",
        "title_original": "Agentic RAG for Production Inference",
        "authors": [
            {"name": "Jane Doe", "affiliation": "OpenAI"},
            {"name": "John Smith", "affiliation": "Stanford University"},
        ],
        "venue": "ICLR 2026",
        "abstract": "Official code: https://github.com/example/agentic-rag. Designed for deployable inference.",
        "pdf_url": "https://arxiv.org/pdf/2503.00001.pdf",
        "upvotes": 128,
        "arxiv_publish_date": "2026-03-20",
        "citations": 9,
        "is_hf_daily": True,
        "is_trending": True,
    }


@pytest.fixture()
def seeded_papers(db_session: Session):
    paper_focus = Paper(
        arxiv_id="2503.01001",
        title_zh="中文焦点标题",
        title_original="Focus Title Original",
        authors=[{"name": "Alice", "affiliation": "OpenAI"}],
        venue="ICLR 2026",
        abstract="Focus abstract",
        pdf_url="https://arxiv.org/pdf/2503.01001.pdf",
        upvotes=100,
        arxiv_publish_date=date(2026, 3, 20),
    )
    paper_watching = Paper(
        arxiv_id="2503.01002",
        title_zh="中文观察标题",
        title_original="Watching Title Original",
        authors=[{"name": "Bob", "affiliation": "Meta"}],
        venue="ACL 2026",
        abstract="Watching abstract",
        pdf_url="https://arxiv.org/pdf/2503.01002.pdf",
        upvotes=80,
        arxiv_publish_date=date(2026, 3, 20),
    )
    paper_candidate = Paper(
        arxiv_id="2503.01003",
        title_zh="中文候选标题",
        title_original="Candidate Title Original",
        authors=[{"name": "Carol", "affiliation": "Independent"}],
        venue=None,
        abstract="Candidate abstract",
        pdf_url="https://arxiv.org/pdf/2503.01003.pdf",
        upvotes=10,
        arxiv_publish_date=date(2026, 3, 20),
    )
    paper_latest = Paper(
        arxiv_id="2503.01004",
        title_zh="最新候选标题",
        title_original="Latest Candidate Title Original",
        authors=[{"name": "Dave", "affiliation": "Google"}],
        venue="NeurIPS 2025",
        abstract="Latest candidate abstract",
        pdf_url="https://arxiv.org/pdf/2503.01004.pdf",
        upvotes=20,
        arxiv_publish_date=date(2026, 3, 19),
    )
    db_session.add_all([paper_focus, paper_watching, paper_candidate, paper_latest])
    db_session.flush()

    current_issue_date = date(2026, 3, 23)
    previous_issue_date = date(2026, 3, 22)

    db_session.add_all(
        [
            PaperSummary(
                paper_id=paper_focus.id,
                issue_date=current_issue_date,
                score=95,
                score_reasons={"hf_recommend": 30},
                category="focus",
                candidate_reason=None,
                direction="Agent",
                one_line_summary="焦点总结",
                one_line_summary_en="Focus summary",
                core_highlights=["亮点一", "亮点二", "亮点三"],
                core_highlights_en=["Point 1", "Point 2", "Point 3"],
                application_scenarios="企业应用",
                application_scenarios_en="Enterprise use",
            ),
            PaperSummary(
                paper_id=paper_watching.id,
                issue_date=current_issue_date,
                score=68,
                score_reasons={"community_popularity": 20},
                category="watching",
                candidate_reason=None,
                direction="RAG",
                one_line_summary="观察总结",
                one_line_summary_en="Watching summary",
                core_highlights=["观察亮点"],
                core_highlights_en=["Watching point"],
                application_scenarios="研发观察",
                application_scenarios_en="R&D watch",
            ),
            PaperSummary(
                paper_id=paper_candidate.id,
                issue_date=current_issue_date,
                score=42,
                score_reasons={"academic_influence": 12},
                category="candidate",
                candidate_reason="low_score",
                direction="Benchmarking",
                one_line_summary=None,
                one_line_summary_en=None,
                core_highlights=None,
                core_highlights_en=None,
                application_scenarios=None,
                application_scenarios_en=None,
            ),
            PaperSummary(
                paper_id=paper_latest.id,
                issue_date=previous_issue_date,
                score=84,
                score_reasons={"top_conf": 25},
                category="focus",
                candidate_reason=None,
                direction="Reasoning",
                one_line_summary="旧版本总结",
                one_line_summary_en="Older summary",
                core_highlights=["旧亮点一", "旧亮点二", "旧亮点三"],
                core_highlights_en=["Old point 1", "Old point 2", "Old point 3"],
                application_scenarios="旧场景",
                application_scenarios_en="Old use case",
            ),
            PaperSummary(
                paper_id=paper_latest.id,
                issue_date=current_issue_date,
                score=49,
                score_reasons={"community_popularity": 10},
                category="candidate",
                candidate_reason="capacity_overflow",
                direction="Reasoning",
                one_line_summary=None,
                one_line_summary_en=None,
                core_highlights=None,
                core_highlights_en=None,
                application_scenarios=None,
                application_scenarios_en=None,
            ),
        ]
    )
    db_session.flush()

    current_focus_summary = (
        db_session.query(PaperSummary)
        .filter(PaperSummary.paper_id == paper_focus.id, PaperSummary.issue_date == current_issue_date)
        .one()
    )
    current_watching_summary = (
        db_session.query(PaperSummary)
        .filter(PaperSummary.paper_id == paper_watching.id, PaperSummary.issue_date == current_issue_date)
        .one()
    )
    db_session.add_all(
        [
            PaperAITrace(
                paper_summary_id=current_focus_summary.id,
                stage="editor",
                stage_status="generated",
                attempt_no=1,
                content=(
                    "## 论文: [2503.01001]\n"
                    "- **写作角度**: 聚焦它如何把 Agent 能力真正推向生产环境。\n"
                    "- **核心痛点**: 线上推理场景缺少稳定的检索增强协同框架。\n"
                    "- **具体解法**: 通过 Agentic RAG 编排检索、规划和推理链路。"
                ),
            ),
            PaperAITrace(
                paper_summary_id=current_focus_summary.id,
                stage="writer",
                stage_status="generated",
                attempt_no=1,
                content=(
                    "## [2503.01001]\n"
                    "- **一句话总结**: 这篇工作把 Agentic RAG 做成了更接近生产可落地的推理框架。\n"
                    "- **One-line Summary**: This work turns Agentic RAG into a more production-ready inference stack.\n"
                    "- **核心亮点**:\n"
                    "- 亮点一\n- 亮点二\n- 亮点三\n"
                    "- **Core Highlights**:\n"
                    "- Point 1\n- Point 2\n- Point 3\n"
                    "- **应用场景**: 面向企业知识检索与复杂问答。\n"
                    "- **Application Scenarios**: Enterprise retrieval and complex QA."
                ),
            ),
            PaperAITrace(
                paper_summary_id=current_focus_summary.id,
                stage="reviewer",
                stage_status="accepted",
                attempt_no=1,
                content="- **整体结论**: PASSED\n- **拒绝名单**: []",
            ),
            PaperAITrace(
                paper_summary_id=current_watching_summary.id,
                stage="editor",
                stage_status="generated",
                attempt_no=1,
                content=(
                    "## 论文: [2503.01002]\n"
                    "- **写作角度**: 解释它为什么值得持续跟踪。\n"
                    "- **核心痛点**: 现有研发团队缺乏对该方向的稳定观察指标。\n"
                    "- **具体解法**: 通过更轻量的观察型总结突出长期价值。"
                ),
            ),
        ]
    )
    db_session.commit()

    return {
        "current_issue_date": current_issue_date,
        "previous_issue_date": previous_issue_date,
        "paper_ids": {
            "focus": paper_focus.id,
            "watching": paper_watching.id,
            "candidate": paper_candidate.id,
            "latest_candidate": paper_latest.id,
        },
    }


@pytest.fixture()
def active_subscriber_seed():
    now = datetime.now(timezone.utc)
    return {
        "email": "active@example.com",
        "status": 1,
        "verify_token": None,
        "verify_expires_at": None,
        "unsub_token": "old-unsub-token",
        "unsub_expires_at": now - timedelta(hours=1),
    }
