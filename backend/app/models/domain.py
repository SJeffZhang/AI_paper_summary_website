from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.specs import (
    AI_TRACE_STAGES,
    AI_TRACE_STATUSES,
    CANDIDATE_REASONS,
    DIRECTIONS,
    NOTIFICATION_DELIVERY_STATUSES,
    NOTIFICATION_TYPES,
    SUMMARY_CATEGORIES,
)
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
    one_line_summary = Column(Text, nullable=True)
    one_line_summary_en = Column(Text, nullable=True)
    core_highlights = Column(JSON, nullable=True)
    core_highlights_en = Column(JSON, nullable=True)
    application_scenarios = Column(Text, nullable=True)
    application_scenarios_en = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    paper = relationship("Paper", back_populates="summaries")
    ai_traces = relationship("PaperAITrace", back_populates="summary", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("paper_id", "issue_date", name="uk_paper_issue"),
    )


class PaperAITrace(Base):
    __tablename__ = "paper_ai_trace"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_summary_id = Column(Integer, ForeignKey("paper_summary.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Enum(*AI_TRACE_STAGES, name="paper_ai_trace_stage"), index=True, nullable=False)
    stage_status = Column(Enum(*AI_TRACE_STATUSES, name="paper_ai_trace_status"), nullable=False)
    attempt_no = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    summary = relationship("PaperSummary", back_populates="ai_traces")

    __table_args__ = (
        UniqueConstraint("paper_summary_id", "stage", "attempt_no", name="uk_trace_summary_stage_attempt"),
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


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    notification_type = Column(Enum(*NOTIFICATION_TYPES, name="notification_type"), index=True, nullable=False)
    run_date = Column(Date, index=True, nullable=False)
    issue_date = Column(Date, index=True, nullable=True)
    recipient_email = Column(String(255), nullable=False)
    status = Column(
        Enum(*NOTIFICATION_DELIVERY_STATUSES, name="notification_delivery_status"),
        index=True,
        nullable=False,
    )
    subject = Column(String(255), nullable=False)
    error_log = Column(Text, nullable=True)
    sent_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "notification_type",
            "run_date",
            "recipient_email",
            name="uk_notification_type_run_recipient",
        ),
    )
