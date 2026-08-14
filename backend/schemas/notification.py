from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


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
    label: Optional[str] = None
    time_of_day: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    interval_days: Optional[int] = None
    is_enabled: bool = True


class ReminderResponse(BaseModel):
    id: str
    user_id: str
    type: str
    label: Optional[str] = None
    time_of_day: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    interval_days: Optional[int] = None
    is_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True
