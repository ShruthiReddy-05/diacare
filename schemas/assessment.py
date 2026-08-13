from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

class QuestionResponseCreate(BaseModel):
    question_id: str
    module_id: str
    question_text_en: Optional[str] = None
    question_text_ta: Optional[str] = None
    answer_value: str
    answer_display_label: Optional[Dict[str, str]] = None # {"en": "...", "ta": "..."}
    language: str

class QuestionResponseResponse(BaseModel):
    id: str
    session_id: str
    question_id: str
    module_id: str
    question_text_en: Optional[str] = None
    question_text_ta: Optional[str] = None
    answer_value: str
    answer_display_label: Optional[Dict[str, str]] = None
    language: str
    answered_at: datetime

    class Config:
        from_attributes = True

class RiskResultResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    glycemic: Optional[str] = None
    physical_activity: Optional[str] = None
    sedentary: Optional[str] = None
    lifestyle: Optional[str] = None
    bmi_category: Optional[str] = None
    par_q_clearance_required: bool
    complication_flags: Optional[Dict[str, Any]] = None
    overall: Optional[str] = None
    computed_at: datetime

    class Config:
        from_attributes = True

class AssessmentSessionCreate(BaseModel):
    questionnaire_id: str
    questionnaire_version: str

class AssessmentSessionResponse(BaseModel):
    id: str
    user_id: str
    questionnaire_id: str
    questionnaire_version: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    responses: List[QuestionResponseResponse] = []
    risk_results: List[RiskResultResponse] = []

    class Config:
        from_attributes = True
