from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SafetyEventResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    source_module: str
    trigger_code: str
    trigger_detail: Optional[str] = None
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    escalation_script_delivered: bool
    resolved: bool

    class Config:
        from_attributes = True


class SafetyEventAcknowledge(BaseModel):
    pass
