from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class FollowUpScheduleCreate(BaseModel):
    schedule_type: str = "weekly"
    day_of_week: int = 4

class FollowUpScheduleResponse(BaseModel):
    id: str
    user_id: str
    schedule_type: str
    day_of_week: int
    last_follow_up_at: Optional[datetime] = None
    next_due_at: datetime
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FollowUpSessionComplete(BaseModel):
    schedule_id: Optional[str] = None
    q1_walked: Optional[bool] = None
    q2_difficulty: Optional[int] = None
    q3_chest_pain_dizziness: Optional[bool] = None
    q4_foot_wounds: Optional[bool] = None

class FollowUpSessionResponse(BaseModel):
    id: str
    user_id: str
    schedule_id: Optional[str] = None
    due_date: date
    status: str
    q1_walked: Optional[bool] = None
    q2_difficulty: Optional[int] = None
    q3_chest_pain_dizziness: Optional[bool] = None
    q4_foot_wounds: Optional[bool] = None
    safety_flag: bool
    escalation_advice_given: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class NextFollowUpResponse(BaseModel):
    status: str
    session: Optional[FollowUpSessionResponse] = None

class NotificationSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str
    device_type: Optional[str] = None

class NotificationSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    endpoint: str
    device_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationEventResponse(BaseModel):
    id: str
    user_id: str
    type: str
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReminderCreate(BaseModel):
    type: str
    days_of_week: Optional[List[int]] = None
    interval_days: Optional[int] = None
    is_enabled: bool = True

class ReminderResponse(BaseModel):
    id: str
    user_id: str
    type: str
    days_of_week: Optional[List[int]] = None
    interval_days: Optional[int] = None
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True

class WeeklyMetricResponse(BaseModel):
    id: str
    user_id: str
    week_start_date: date
    completed_activity_minutes: int
    completed_activity_days: int
    exercise_adherent: bool
    adherence_streak_weeks: int
    login_streak_weeks: int
    follow_up_completed: bool
    safety_flag: bool

    class Config:
        from_attributes = True
