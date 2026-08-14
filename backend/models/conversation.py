import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class ConversationSession(Base):
    """Tracks a participant's progress through the onboarding + baseline
    conversation (module A, then B1-B3), spread across up to 3 sittings."""
    __tablename__ = "conversation_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    script_id = Column(String(50), nullable=False)
    script_version = Column(String(20), nullable=False)
    sitting = Column(String(10), default="1", nullable=False)  # "1" (A+B1-B3), "2" (M1+M2), "3" (M3+M4)
    status = Column(String(20), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    resume_module_id = Column(String(20), nullable=True)
    resume_question_id = Column(String(100), nullable=True)
    preferred_checkin_time = Column(String(20), nullable=True)  # e.g. "evening", "18:00"
    started_at = Column(DateTime, default=ist_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="conversation_sessions")
    responses = relationship("ConversationResponse", back_populates="session", cascade="all, delete-orphan")


class ConversationResponse(Base):
    """A single answered question, keyed by module_id (A/B1/B2/B3/M1-M4/C/D)."""
    __tablename__ = "conversation_responses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(String(20), nullable=False)
    question_id = Column(String(100), nullable=False)
    question_text_en = Column(String(1000), nullable=True)
    question_text_ta = Column(String(1000), nullable=True)
    answer_value = Column(String(500), nullable=False)
    answer_display_label = Column(JSON, nullable=True)  # {"en": "...", "ta": "..."}
    language = Column(String(10), nullable=False)
    input_modality = Column(String(10), default="touch", nullable=False)  # "speech" or "touch"
    answered_at = Column(DateTime, default=ist_now, nullable=False)

    session = relationship("ConversationSession", back_populates="responses")
