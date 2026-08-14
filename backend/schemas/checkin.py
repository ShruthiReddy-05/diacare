from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, date


class CheckInScheduleResponse(BaseModel):
    id: str
    user_id: str
    program_start_date: date
    preferred_time: Optional[str] = None
    total_weeks: int
    next_due_at: datetime
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CheckInSessionComplete(BaseModel):
    q1_activity_days: int
    q2_food_goal_days: int
    q3_medication_days: int
    q4_foot_care_days: int
    q5_new_foot_problem: bool
    q6_stress_0_10: int
    q7_sleep_0_10: int
    q8_sugar_reading: Optional[float] = None
    q8b_hypo_episode: bool = False
    fever_or_vomiting_reported: bool = False
    upcoming_function_or_fasting: bool = False


class CheckInSessionResponse(BaseModel):
    id: str
    user_id: str
    schedule_id: Optional[str] = None
    program_week: int
    due_date: date
    status: str
    q1_activity_days: Optional[int] = None
    q2_food_goal_days: Optional[int] = None
    q3_medication_days: Optional[int] = None
    q4_foot_care_days: Optional[int] = None
    q5_new_foot_problem: Optional[bool] = None
    q6_stress_0_10: Optional[int] = None
    q7_sleep_0_10: Optional[int] = None
    q8_sugar_reading: Optional[float] = None
    q8b_hypo_episode: Optional[bool] = None
    triggered_content: Optional[Dict[str, Any]] = None
    safety_flag: bool
    escalation_advice_given: bool
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NextCheckInResponse(BaseModel):
    status: str
    session: Optional[CheckInSessionResponse] = None


class WeeklyDomainMetricResponse(BaseModel):
    id: str
    user_id: str
    program_week: int
    activity_streak_weeks: int
    food_goal_streak_weeks: int
    medication_streak_weeks: int
    foot_care_streak_weeks: int
    week_is_poor: bool
    consecutive_poor_weeks: int
    reassessment_triggered: bool

    class Config:
        from_attributes = True
