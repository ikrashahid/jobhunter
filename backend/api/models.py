from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MatchStatusUpdate(BaseModel):
    status: Optional[str] = None
    human_label: Optional[str] = None
    application_status: Optional[str] = None  # 'red' | 'yellow' | 'green'
    applied_at: Optional[datetime] = None


class JDAnalyzeRequest(BaseModel):
    jd_text: str


class TriggerDraftRequest(BaseModel):
    match_ids: Optional[list[str]] = None  # if None, drafts all pending