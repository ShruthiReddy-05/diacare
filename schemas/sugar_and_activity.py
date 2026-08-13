from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date

class SugarReadingCreate(BaseModel):
    reading_type: str = Field(..., description="fasting, post_meal, or hba1c")
    value: float = Field(..., description="mg/dL for glucose, % for HbA1c")
    recorded_at: Optional[datetime] = None
    notes: Optional[str] = None

class SugarReadingResponse(BaseModel):
    id: str
    user_id: str
    reading_type: str
    value: float
    recorded_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class ActivityLogCreate(BaseModel):
    activity_date: date
    completed_minutes: int = 0
    completed_days: int = 0
    strength_completed: bool = False
    fatigue_rating: Optional[int] = None
    difficulty_rating: Optional[int] = None
    safety_flag: bool = False
    notes: Optional[str] = None

class ActivityLogResponse(BaseModel):
    id: str
    user_id: str
    activity_date: date
    completed_minutes: int
    completed_days: int
    strength_completed: bool
    fatigue_rating: Optional[int] = None
    difficulty_rating: Optional[int] = None
    safety_flag: bool
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
