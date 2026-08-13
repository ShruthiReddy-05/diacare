import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_user_id = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    preferred_language = Column(String(10), default="en", nullable=False) # "en" or "ta"
    role = Column(String(20), default="participant", nullable=False) # "participant" or "admin"
    created_at = Column(DateTime, default=ist_now, nullable=False)
    last_seen_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)
    
    recovery_events = relationship("ParticipantRecoveryEvent", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("AppSession", back_populates="user", cascade="all, delete-orphan")
    assessment_sessions = relationship("AssessmentSession", back_populates="user", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="user", cascade="all, delete-orphan")
    sugar_readings = relationship("SugarReading", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    follow_up_schedules = relationship("FollowUpSchedule", back_populates="user", cascade="all, delete-orphan")
    follow_up_sessions = relationship("FollowUpSession", back_populates="user", cascade="all, delete-orphan")
    notification_subscriptions = relationship("NotificationSubscription", back_populates="user", cascade="all, delete-orphan")
    notification_events = relationship("NotificationEvent", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    weekly_metrics = relationship("WeeklyUserMetric", back_populates="user", cascade="all, delete-orphan")

class ParticipantRecoveryEvent(Base):
    __tablename__ = "participant_recovery_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_user_id_entered = Column(String(50), nullable=False)
    first_name_entered = Column(String(100), nullable=False)
    last_name_entered = Column(String(100), nullable=False)
    result = Column(String(50), nullable=False) # "matched", "not_matched", etc.
    created_at = Column(DateTime, default=ist_now, nullable=False)
    
    user = relationship("User", back_populates="recovery_events")

class AppSession(Base):
    __tablename__ = "app_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, default=ist_now, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    entry_source = Column(String(50), nullable=True) # "direct", "notification", etc.
    language = Column(String(10), nullable=True)
    
    user = relationship("User", back_populates="sessions")
