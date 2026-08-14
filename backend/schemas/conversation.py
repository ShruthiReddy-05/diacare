from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ConversationResponseCreate(BaseModel):
    module_id: str
    question_id: str
    question_text_en: Optional[str] = None
    question_text_ta: Optional[str] = None
    answer_value: str
    answer_display_label: Optional[Dict[str, str]] = None
    language: str
    input_modality: str = "touch"


class ConversationResponseOut(BaseModel):
    id: str
    session_id: str
    module_id: str
    question_id: str
    question_text_en: Optional[str] = None
    question_text_ta: Optional[str] = None
    answer_value: str
    answer_display_label: Optional[Dict[str, str]] = None
    language: str
    input_modality: str
    answered_at: datetime

    class Config:
        from_attributes = True


class ConversationSessionCreate(BaseModel):
    script_id: str
    script_version: str
    sitting: str = "1"
    preferred_checkin_time: Optional[str] = None


class ConversationSessionResponse(BaseModel):
    id: str
    user_id: str
    script_id: str
    script_version: str
    sitting: str
    status: str
    resume_module_id: Optional[str] = None
    resume_question_id: Optional[str] = None
    preferred_checkin_time: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    responses: List[ConversationResponseOut] = []

    class Config:
        from_attributes = True


class CompleteSittingRequest(BaseModel):
    sitting: str  # "1", "2", or "3" -- which sitting is being finalized
