from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime


class SafetyEventResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    source_module: str
    trigger_code: str
    trigger_detail: Optional[str] = None
    triggered_at: datetime
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledgement_note: Optional[str] = None
    escalation_script_delivered: bool
    resolved: bool

    class Config:
        from_attributes = True


class SafetyEventAcknowledge(BaseModel):
    note: str = Field(min_length=1, max_length=1000)

    @field_validator("note")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Acknowledgement note must not be blank")
        return v.strip()


class SafetyLockStatus(BaseModel):
    """Body of both the 423 lock response (under "detail") and the
    /api/safety status endpoint. emergency_script is always the fixed
    safety_engine.EMERGENCY_SCRIPT string for the patient's language."""
    locked: bool
    event_code: Optional[str] = None
    event_id: Optional[str] = None
    open_event_codes: List[str] = []
    language: str
    emergency_script: Optional[str] = None
