import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False)
    p256dh_key = Column(String(200), nullable=False)
    auth_key = Column(String(200), nullable=False)
    device_type = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="notification_subscriptions")


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    action_completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="scheduled", nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="notification_events")


class Reminder(Base):
    """Medicine reminders are anchored to the actual dose times captured in
    B2 and built by services/m3_engine.py; this row is the delivery schedule."""
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)  # "medication", "sugar_test", "movement_break", ...
    label = Column(String(200), nullable=True)  # e.g. "Metformin 500mg - after dinner"
    time_of_day = Column(String(10), nullable=True)  # "HH:MM", for medication reminders anchored to dose times
    days_of_week = Column(JSON, nullable=True)
    interval_days = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="reminders")
