import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean, Date, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class CheckInSchedule(Base):
    """The 12-week weekly check-in (module C) schedule for one user."""
    __tablename__ = "checkin_schedules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    program_start_date = Column(Date, nullable=False)
    preferred_time = Column(String(20), nullable=True)  # patient's chosen time-of-day from onboarding
    total_weeks = Column(Integer, default=12, nullable=False)
    next_due_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="checkin_schedule")
    sessions = relationship("CheckInSession", back_populates="schedule", cascade="all, delete-orphan")


class CheckInSession(Base):
    """One of the 8-item weekly check-ins (module C)."""
    __tablename__ = "checkin_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(String(36), ForeignKey("checkin_schedules.id", ondelete="SET NULL"), nullable=True)
    program_week = Column(Integer, nullable=False)  # 1-12
    due_date = Column(Date, nullable=False)
    status = Column(String(20), default="due", nullable=False)  # due/missed/completed/escalated

    q1_activity_days = Column(Integer, nullable=True)  # 0-7
    q2_food_goal_days = Column(Integer, nullable=True)  # 0-7
    q3_medication_days = Column(Integer, nullable=True)  # 0-7
    q4_foot_care_days = Column(Integer, nullable=True)  # 0-7
    q5_new_foot_problem = Column(Boolean, nullable=True)
    q6_stress_0_10 = Column(Integer, nullable=True)
    q7_sleep_0_10 = Column(Integer, nullable=True)
    q8_sugar_reading = Column(Float, nullable=True)
    q8b_hypo_episode = Column(Boolean, nullable=True)

    triggered_content = Column(JSON, nullable=True)  # {"sick_day": bool, "festival_fasting": bool}
    safety_flag = Column(Boolean, default=False, nullable=False)
    escalation_advice_given = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="checkin_sessions")
    schedule = relationship("CheckInSchedule", back_populates="sessions")


class WeeklyDomainMetric(Base):
    """Per-domain adherence + streak rollup for one program week, and the
    consecutive-poor-weeks counter that drives the full-reassessment trigger."""
    __tablename__ = "weekly_domain_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    program_week = Column(Integer, nullable=False)

    activity_streak_weeks = Column(Integer, default=0, nullable=False)
    food_goal_streak_weeks = Column(Integer, default=0, nullable=False)
    medication_streak_weeks = Column(Integer, default=0, nullable=False)
    foot_care_streak_weeks = Column(Integer, default=0, nullable=False)

    week_is_poor = Column(Boolean, default=False, nullable=False)  # any domain regressed this week
    consecutive_poor_weeks = Column(Integer, default=0, nullable=False)
    reassessment_triggered = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=ist_now, nullable=False)
    updated_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)

    user = relationship("User", back_populates="weekly_domain_metrics")
