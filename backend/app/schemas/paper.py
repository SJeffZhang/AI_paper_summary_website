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
    one_line_summary: str
    core_highlights: List[str]
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
    arxiv_publish_date: date

class PaperDetailResponseModel(ResponseModel):
    data: PaperDetail

# Subscribe Schemas
class SubscribeRequest(BaseModel):
    email: EmailStr

class UnsubscribeRequest(BaseModel):
    token: str
