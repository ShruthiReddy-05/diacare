from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class ModuleOutcomeResponse(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str] = None
    module_id: str
    output_json: Dict[str, Any]
    computed_at: datetime

    class Config:
        from_attributes = True
