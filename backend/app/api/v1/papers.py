from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import date, timedelta # PRD v2.1
from app.db.session import get_db
from app.models.domain import Paper, PaperSummary
from app.schemas.paper import PaperListResponseModel, PaperListResponse, PaperSummaryBase, PaperDetailResponseModel, PaperDetail

router = APIRouter()

@router.get("/papers", response_model=PaperListResponseModel)
def get_papers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None, # focus, watching, candidate
    direction: Optional[str] = None,
    issue_date: Optional[date] = None,
    include_candidates: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get paginated feed of papers (v2.1).
    Supports filtering by category, direction, and date.
    """
    skip = (page - 1) * limit
    
    # If we only want summarized papers (default), we join with PaperSummary
    if not include_candidates:
        query = db.query(PaperSummary, Paper).join(Paper)
        if category:
            query = query.filter(Paper.category == category)
        if direction:
            query = query.filter(Paper.direction == direction)
        if issue_date:
            query = query.filter(PaperSummary.issue_date == issue_date)
            
        total = query.count()
        summaries = query.order_by(
            PaperSummary.issue_date.desc(),
            Paper.score.desc()
        ).offset(skip).limit(limit).all()
        
        items = [
            PaperSummaryBase(
                id=p.id, arxiv_id=p.arxiv_id, title=p.title, title_en=p.title_en,
                one_line_summary=s.one_line_summary, core_highlights=s.core_highlights,
                one_line_summary_en=s.one_line_summary_en, core_highlights_en=s.core_highlights_en,
                category=p.category, score=p.score, score_reasons=p.score_reasons,
                direction=p.direction, issue_date=s.issue_date
            ) for s, p in summaries
        ]
    else:
        # For the "Sources" page, we want ALL papers for a specific date, including candidates
        # We use a LEFT JOIN to get summaries if they exist
        query = db.query(Paper, PaperSummary).outerjoin(PaperSummary).filter(Paper.arxiv_publish_date != None)
        
        # In v2.0, we use T+3, so we filter by arxiv_publish_date = issue_date - 3 days
        if issue_date:
            target_fetch_date = issue_date - timedelta(days=3)
            query = query.filter(Paper.arxiv_publish_date == target_fetch_date)
        
        if direction:
            query = query.filter(Paper.direction == direction)
        if category:
            query = query.filter(Paper.category == category)

        total = query.count()
        results = query.order_by(Paper.score.desc()).offset(skip).limit(limit).all()
        
        items = []
        for p, s in results:
            items.append(
                PaperSummaryBase(
                    id=p.id, arxiv_id=p.arxiv_id, title=p.title, title_en=p.title_en,
                    one_line_summary=s.one_line_summary if s else "未选中进行深度解读",
                    core_highlights=s.core_highlights if s else [],
                    one_line_summary_en=s.one_line_summary_en if s else "Not selected for deep dive",
                    core_highlights_en=s.core_highlights_en if s else [],
                    category=p.category, score=p.score, score_reasons=p.score_reasons,
                    direction=p.direction, 
                    issue_date=issue_date or (p.arxiv_publish_date + timedelta(days=3))
                )
            )

    return PaperListResponseModel(data=PaperListResponse(total=total, items=items))

@router.get("/papers/{paper_id}", response_model=PaperDetailResponseModel)
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    """
    Get detailed summary with bilingual content and metadata (v2.0).
    """
    result = db.query(PaperSummary, Paper).join(Paper).filter(Paper.id == paper_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Paper not found"
        )
        
    summary, paper = result
    
    return PaperDetailResponseModel(
        data=PaperDetail(
            id=paper.id,
            arxiv_id=paper.arxiv_id,
            title=paper.title,
            title_en=paper.title_en, # PRD v2.0
            authors=paper.authors,
            abstract=paper.abstract,
            pdf_url=paper.pdf_url,
            # CN
            one_line_summary=summary.one_line_summary,
            core_highlights=summary.core_highlights,
            application_scenarios=summary.application_scenarios,
            # EN
            one_line_summary_en=summary.one_line_summary_en,
            core_highlights_en=summary.core_highlights_en,
            application_scenarios_en=summary.application_scenarios_en,
            # Meta
            category=paper.category,
            score=paper.score,
            score_reasons=paper.score_reasons,
            direction=paper.direction,
            issue_date=summary.issue_date,
            arxiv_publish_date=paper.arxiv_publish_date
        )
    )
