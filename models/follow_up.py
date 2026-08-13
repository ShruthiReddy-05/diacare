import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Date, Text, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now

class FollowUpSchedule(Base):
    __tablename__ = "follow_up_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_type = Column(String(20), default="weekly", nullable=False)
    day_of_week = Column(Integer, default=4, nullable=False)
    last_follow_up_at = Column(DateTime, nullable=True)
    next_due_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="follow_up_schedules")
    sessions = relationship("FollowUpSession", back_populates="schedule", cascade="all, delete-orphan")

class FollowUpSession(Base):
    __tablename__ = "follow_up_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(String(36), ForeignKey("follow_up_schedules.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), default="due", nullable=False)
    q1_walked = Column(Boolean, nullable=True)
    q2_difficulty = Column(Integer, nullable=True)
    q3_chest_pain_dizziness = Column(Boolean, nullable=True)
    q4_foot_wounds = Column(Boolean, nullable=True)
    safety_flag = Column(Boolean, default=False, nullable=False)
    escalation_advice_given = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="follow_up_sessions")
    schedule = relationship("FollowUpSchedule", back_populates="sessions")

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
    __tablename__ = "reminders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(30), nullable=False)
    days_of_week = Column(JSON, nullable=True)
    interval_days = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="reminders")

class WeeklyUserMetric(Base):
    __tablename__ = "weekly_user_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start_date = Column(Date, nullable=False)
    completed_activity_minutes = Column(Integer, default=0, nullable=False)
    completed_activity_days = Column(Integer, default=0, nullable=False)
    exercise_adherent = Column(Boolean, default=False, nullable=False)
    adherence_streak_weeks = Column(Integer, default=0, nullable=False)
    login_streak_weeks = Column(Integer, default=0, nullable=False)
    follow_up_completed = Column(Boolean, default=False, nullable=False)
    safety_flag = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)
    updated_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)

    user = relationship("User", back_populates="weekly_metrics")
