from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    preferred_language: str = Field(default="en", max_length=10)

class UserRecovery(BaseModel):
    display_user_id: str = Field(..., min_length=1, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

class LanguageUpdate(BaseModel):
    preferred_language: str = Field(..., max_length=10)

class UserResponse(BaseModel):
    id: str
    display_user_id: str
    first_name: str
    last_name: str
    preferred_language: str
    role: str
    created_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True

class AppSessionCreate(BaseModel):
    entry_source: Optional[str] = None
    language: Optional[str] = None

class AppSessionResponse(BaseModel):
    id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    entry_source: Optional[str] = None
    language: Optional[str] = None

    class Config:
        from_attributes = True
