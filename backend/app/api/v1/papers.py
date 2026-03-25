from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import Paper, PaperSummary
from app.schemas.paper import (
    PaperDetail,
    PaperDetailResponseModel,
    PaperListItem,
    PaperListPayload,
    PaperListResponseModel,
)

router = APIRouter()


def _normalize_authors(raw_authors):
    normalized = []
    for author in raw_authors or []:
        if isinstance(author, dict):
            normalized.append(
                {
                    "name": str(author.get("name", "")).strip(),
                    "affiliation": str(author.get("affiliation", "")).strip(),
                }
            )
        else:
            normalized.append({"name": str(author).strip(), "affiliation": ""})
    return normalized


def _serialize_list_item(summary: PaperSummary, paper: Paper) -> PaperListItem:
    return PaperListItem(
        id=paper.id,
        arxiv_id=paper.arxiv_id,
        title_zh=paper.title_zh,
        title_original=paper.title_original,
        score=summary.score,
        category=summary.category,
        candidate_reason=summary.candidate_reason,
        direction=summary.direction,
        issue_date=summary.issue_date,
        score_reasons=summary.score_reasons,
        one_line_summary=summary.one_line_summary,
        one_line_summary_en=summary.one_line_summary_en,
    )


@router.get("/papers", response_model=PaperListResponseModel)
def get_papers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    direction: Optional[str] = None,
    issue_date: Optional[date] = None,
    include_candidates: bool = Query(False),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * limit
    query = db.query(PaperSummary, Paper).join(Paper)

    if not include_candidates:
        query = query.filter(PaperSummary.category.in_(("focus", "watching")))
    if category:
        query = query.filter(PaperSummary.category == category)
    if direction:
        query = query.filter(PaperSummary.direction == direction)
    if issue_date:
        query = query.filter(PaperSummary.issue_date == issue_date)

    category_order = case(
        (PaperSummary.category == "focus", 0),
        (PaperSummary.category == "watching", 1),
        else_=2,
    )

    total = query.count()
    rows = (
        query.order_by(PaperSummary.issue_date.desc(), category_order.asc(), PaperSummary.score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return PaperListResponseModel(
        data=PaperListPayload(
            total=total,
            items=[_serialize_list_item(summary, paper) for summary, paper in rows],
        )
    )


@router.get("/papers/{paper_id}", response_model=PaperDetailResponseModel)
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(PaperSummary, Paper)
        .join(Paper)
        .filter(Paper.id == paper_id)
        .order_by(PaperSummary.issue_date.desc())
        .first()
    )

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    summary, paper = row
    list_item = _serialize_list_item(summary, paper)
    detail_payload = list_item.model_dump()
    detail_payload.update(
        {
            "authors": _normalize_authors(paper.authors),
            "venue": paper.venue,
            "abstract": paper.abstract,
            "pdf_url": paper.pdf_url,
            "arxiv_publish_date": paper.arxiv_publish_date,
            "core_highlights": summary.core_highlights,
            "core_highlights_en": summary.core_highlights_en,
            "application_scenarios": summary.application_scenarios,
            "application_scenarios_en": summary.application_scenarios_en,
        }
    )

    return PaperDetailResponseModel(
        data=PaperDetail(**detail_payload)
    )
