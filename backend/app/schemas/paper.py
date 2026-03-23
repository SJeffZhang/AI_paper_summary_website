from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import date

# Base Response format
class ResponseModel(BaseModel):
    code: int = 200
    msg: str = "success"

# Paper Schemas
class PaperSummaryBase(BaseModel):
    id: int
    arxiv_id: str
    title: str
    title_en: Optional[str] = None # PRD v2.0
    
    # CN fields
    one_line_summary: str
    core_highlights: List[str]
    
    # EN fields (PRD v2.0)
    one_line_summary_en: Optional[str] = None
    core_highlights_en: Optional[List[str]] = None
    
    # Metadata (PRD v2.0)
    category: Optional[str] = None # focus, watching
    score: int = 0
    score_reasons: Optional[dict] = None
    direction: Optional[str] = None
    
    issue_date: date

class PaperListResponse(BaseModel):
    total: int
    items: List[PaperSummaryBase]

class PaperListResponseModel(ResponseModel):
    data: PaperListResponse

class PaperDetail(PaperSummaryBase):
    authors: List[str]
    abstract: str
    pdf_url: str
    application_scenarios: str
    application_scenarios_en: Optional[str] = None
    arxiv_publish_date: date

class PaperDetailResponseModel(ResponseModel):
    data: PaperDetail

# Subscribe Schemas
class SubscribeRequest(BaseModel):
    email: EmailStr

class UnsubscribeRequest(BaseModel):
    token: str
