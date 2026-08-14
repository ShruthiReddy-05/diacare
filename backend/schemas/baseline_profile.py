from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class BaselineProfileResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None

    age_band: Optional[str] = None
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    waist_risk: bool
    ideal_body_weight_kg: Optional[float] = None
    daily_energy_kcal: Optional[float] = None
    occupational_activity_level: Optional[str] = None
    sedentary_work_flag: bool

    glycemic_category: Optional[str] = None
    duration_risk_flag: bool
    bp_category: Optional[str] = None
    salt_target_g: Optional[float] = None
    regimen_class: Optional[str] = None
    hypoglycemia_risk_flag: bool
    herbal_use_flag: bool
    follow_up_gap_flag: bool
    screening_overdue: Optional[Dict[str, Any]] = None

    complication_profile: Optional[Dict[str, Any]] = None
    foot_risk_category: Optional[str] = None
    exercise_clearance_required: bool
    tobacco_flag: bool
    alcohol_flag: bool
    overall_risk_tier: Optional[str] = None

    computed_at: datetime

    class Config:
        from_attributes = True
