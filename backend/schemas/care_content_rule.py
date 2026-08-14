from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CareContentRuleCreate(BaseModel):
    id: str
    module_id: str
    content_type: str
    condition_tags: List[str]
    release_tag: Optional[str] = None
    text_en: str
    text_ta: Optional[str] = None
    severity: str = "info"
    precedence: int = 100
    source_reference: str
    review_status: str = "draft"


class CareContentRuleResponse(BaseModel):
    id: str
    module_id: str
    content_type: str
    condition_tags: List[str]
    release_tag: Optional[str] = None
    text_en: str
    text_ta: Optional[str] = None
    severity: str
    precedence: int
    source_reference: str
    review_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
