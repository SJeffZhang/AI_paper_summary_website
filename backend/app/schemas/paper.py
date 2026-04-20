from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr


class ResponseModel(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Optional[Any] = None


class AuthorModel(BaseModel):
    name: str
    affiliation: str = ""


class PaperListItem(BaseModel):
    id: int
    arxiv_id: str
    title_zh: str
    title_original: str
    score: int
    category: str
    candidate_reason: Optional[str] = None
    direction: str
    issue_date: date
    score_reasons: Optional[Dict[str, int]] = None
    one_line_summary: Optional[str] = None
    one_line_summary_en: Optional[str] = None


class PaperListPayload(BaseModel):
    total: int
    items: List[PaperListItem]


class PaperListResponseModel(ResponseModel):
    data: PaperListPayload


class PaperDetail(PaperListItem):
    authors: List[AuthorModel]
    affiliations: List[str] = []
    venue: Optional[str] = None
    abstract: str
    pdf_url: str
    arxiv_publish_date: date
    score_reasons: Optional[Dict[str, int]] = None
    core_highlights: Optional[List[str]] = None
    core_highlights_en: Optional[List[str]] = None
    application_scenarios: Optional[str] = None
    application_scenarios_en: Optional[str] = None


class PaperDetailResponseModel(ResponseModel):
    data: PaperDetail


class PaperCalendarDayItem(BaseModel):
    issue_date: date
    has_content: bool
    paper_count: int = 0


class PaperCalendarPayload(BaseModel):
    min_issue_date: Optional[date] = None
    max_issue_date: Optional[date] = None
    latest_with_content: Optional[date] = None
    days: List[PaperCalendarDayItem] = []


class PaperCalendarResponseModel(ResponseModel):
    data: PaperCalendarPayload


class SubscribeRequest(BaseModel):
    email: EmailStr


class UnsubscribeRequest(BaseModel):
    token: str
