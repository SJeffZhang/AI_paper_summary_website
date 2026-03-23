from sqlalchemy import Column, Integer, String, Date, DateTime, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base

class Paper(Base):
    __tablename__ = "paper"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    arxiv_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    authors = Column(JSON, nullable=False)
    abstract = Column(Text, nullable=False)
    pdf_url = Column(String(255), nullable=False)
    upvotes = Column(Integer, default=0)
    arxiv_publish_date = Column(Date, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    summaries = relationship("PaperSummary", back_populates="paper", cascade="all, delete-orphan")


class PaperSummary(Base):
    __tablename__ = "paper_summary"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("paper.id", ondelete="CASCADE"), nullable=False)
    one_line_summary = Column(String(255), nullable=False)
    core_highlights = Column(JSON, nullable=False)
    application_scenarios = Column(Text, nullable=False)
    issue_date = Column(Date, index=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    paper = relationship("Paper", back_populates="summaries")

    __table_args__ = (
        UniqueConstraint('paper_id', 'issue_date', name='uk_paper_issue'),
    )


class Subscriber(Base):
    __tablename__ = "subscriber"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(Integer, default=0, index=True) # 0: unverified, 1: active, 2: unsubscribed
    verify_token = Column(String(64), unique=True, index=True, nullable=True)
    unsubscribe_token = Column(String(64), unique=True, index=True, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SystemTaskLog(Base):
    __tablename__ = "system_task_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_date = Column(Date, unique=True, index=True, nullable=False)
    status = Column(String(20), nullable=False) # RUNNING, SUCCESS, FAILED
    fetched_count = Column(Integer, default=0)
    processed_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
