from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.specs import CANDIDATE_REASONS, DIRECTIONS, SUMMARY_CATEGORIES
from app.models.base import Base


class Paper(Base):
    __tablename__ = "paper"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    arxiv_id = Column(String(50), unique=True, index=True, nullable=False)
    title_zh = Column(String(500), nullable=False)
    title_original = Column(String(500), nullable=False)
    authors = Column(JSON, nullable=False)
    venue = Column(String(255), nullable=True)
    abstract = Column(Text, nullable=False)
    pdf_url = Column(String(255), nullable=False)
    upvotes = Column(Integer, default=0, nullable=False)
    arxiv_publish_date = Column(Date, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    summaries = relationship("PaperSummary", back_populates="paper", cascade="all, delete-orphan")


class PaperSummary(Base):
    __tablename__ = "paper_summary"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("paper.id", ondelete="CASCADE"), nullable=False)
    issue_date = Column(Date, index=True, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    score_reasons = Column(JSON, nullable=True)
    category = Column(Enum(*SUMMARY_CATEGORIES, name="summary_category"), index=True, nullable=False)
    candidate_reason = Column(
        Enum(*CANDIDATE_REASONS, name="candidate_reason"),
        nullable=True,
    )
    direction = Column(Enum(*DIRECTIONS, name="paper_direction"), index=True, nullable=False)
    one_line_summary = Column(String(255), nullable=True)
    one_line_summary_en = Column(String(255), nullable=True)
    core_highlights = Column(JSON, nullable=True)
    core_highlights_en = Column(JSON, nullable=True)
    application_scenarios = Column(Text, nullable=True)
    application_scenarios_en = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    paper = relationship("Paper", back_populates="summaries")

    __table_args__ = (
        UniqueConstraint("paper_id", "issue_date", name="uk_paper_issue"),
    )


class Subscriber(Base):
    __tablename__ = "subscriber"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(Integer, default=0, index=True, nullable=False)
    verify_token = Column(String(64), unique=True, index=True, nullable=True)
    unsub_token = Column(String(64), unique=True, index=True, nullable=True)
    verify_expires_at = Column(DateTime, nullable=True)
    unsub_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class SystemTaskLog(Base):
    __tablename__ = "system_task_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_date = Column(Date, unique=True, index=True, nullable=False)
    status = Column(String(20), nullable=False)
    fetched_count = Column(Integer, default=0, nullable=False)
    processed_count = Column(Integer, default=0, nullable=False)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    finished_at = Column(DateTime, nullable=True)
