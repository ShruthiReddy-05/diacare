from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class ExerciseRagRuleCreate(BaseModel):
    id: str
    source_type: str
    source_name: str
    source_sheet: Optional[str] = None
    condition_tags: List[str]
    contraindication_tags: List[str]
    allowed_exercise_tags: List[str]
    prohibited_exercise_tags: List[str]
    recommendation: str
    rationale: Optional[str] = None
    severity: str = "info"
    precedence: int = 100
    review_status: str = "draft"

class ExerciseRagRuleResponse(BaseModel):
    id: str
    source_type: str
    source_name: str
    source_sheet: Optional[str] = None
    condition_tags: List[str]
    contraindication_tags: List[str]
    allowed_exercise_tags: List[str]
    prohibited_exercise_tags: List[str]
    recommendation: str
    rationale: Optional[str] = None
    severity: str
    precedence: int
    review_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
