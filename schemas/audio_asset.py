from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AudioAssetCreate(BaseModel):
    questionnaire_id: str
    questionnaire_version: str
    question_id: str
    language: str
    provider: str
    voice_id: Optional[str] = None
    content_hash: str
    file_path: str
    mime_type: str = "audio/mpeg"
    duration_ms: Optional[int] = None

class AudioAssetResponse(BaseModel):
    id: str
    questionnaire_id: str
    questionnaire_version: str
    question_id: str
    language: str
    provider: str
    voice_id: Optional[str] = None
    content_hash: str
    file_path: str
    mime_type: str
    duration_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
