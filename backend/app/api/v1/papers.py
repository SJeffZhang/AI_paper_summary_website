from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.db.session import get_db
from app.models.domain import Paper, PaperSummary
from app.schemas.paper import PaperListResponseModel, PaperListResponse, PaperSummaryBase, PaperDetailResponseModel, PaperDetail

router = APIRouter()

@router.get("/papers", response_model=PaperListResponseModel)
def get_papers(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get paginated feed of paper summaries.
    """
    skip = (page - 1) * limit
    
    # Query total count
    total = db.query(func.count(PaperSummary.id)).scalar()
    
    # Query items with joined Paper data, ordered by issue_date descending
    summaries = db.query(PaperSummary, Paper).join(Paper).order_by(
        PaperSummary.issue_date.desc(),
        Paper.upvotes.desc() # Secondary sort by quality within the same day
    ).offset(skip).limit(limit).all()
    
    items = []
    for summary, paper in summaries:
        items.append(
            PaperSummaryBase(
                id=paper.id,
                arxiv_id=paper.arxiv_id,
                title=paper.title,
                one_line_summary=summary.one_line_summary,
                core_highlights=summary.core_highlights,
                issue_date=summary.issue_date
            )
        )
        
    return PaperListResponseModel(
        data=PaperListResponse(
            total=total,
            items=items
        )
    )

@router.get("/papers/{paper_id}", response_model=PaperDetailResponseModel)
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    """
    Get detailed summary of a specific paper by its ID.
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
            authors=paper.authors,
            abstract=paper.abstract,
            pdf_url=paper.pdf_url,
            one_line_summary=summary.one_line_summary,
            core_highlights=summary.core_highlights,
            application_scenarios=summary.application_scenarios,
            issue_date=summary.issue_date,
            arxiv_publish_date=paper.arxiv_publish_date
        )
    )
