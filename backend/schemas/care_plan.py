from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class CarePlanResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    risk_tier: Optional[str] = None
    plan_snapshot: Dict[str, Any]
    traceability: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
