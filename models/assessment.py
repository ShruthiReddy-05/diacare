import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now

class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    questionnaire_id = Column(String(50), nullable=False)
    questionnaire_version = Column(String(20), nullable=False)
    status = Column(String(20), default="in_progress", nullable=False) # "in_progress", "completed", "abandoned"
    started_at = Column(DateTime, default=ist_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="assessment_sessions")
    responses = relationship("QuestionResponse", back_populates="session", cascade="all, delete-orphan")
    risk_results = relationship("RiskResult", back_populates="session", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="session", cascade="all, delete-orphan")

class QuestionResponse(Base):
    __tablename__ = "question_responses"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(String(50), nullable=False)
    module_id = Column(String(50), nullable=False)
    question_text_en = Column(String(500), nullable=True)
    question_text_ta = Column(String(500), nullable=True)
    answer_value = Column(String(500), nullable=False) # Store answer as string representation
    answer_display_label = Column(JSON, nullable=True) # {"en": "...", "ta": "..."}
    language = Column(String(10), default="en", nullable=False)
    answered_at = Column(DateTime, default=ist_now, nullable=False)
    
    session = relationship("AssessmentSession", back_populates="responses")

class RiskResult(Base):
    __tablename__ = "risk_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    glycemic = Column(String(50), nullable=True) # good/moderate/high/red_flag
    physical_activity = Column(String(50), nullable=True) # adequate/moderate/low
    sedentary = Column(String(50), nullable=True) # low/moderate_to_high
    lifestyle = Column(String(50), nullable=True)
    bmi_category = Column(String(50), nullable=True) # underweight/normal/overweight/obese
    par_q_clearance_required = Column(Boolean, default=False, nullable=False)
    complication_flags = Column(JSON, nullable=True) # dict of flags
    overall = Column(String(50), nullable=True) # low/moderate/high
    computed_at = Column(DateTime, default=ist_now, nullable=False)
    
    session = relationship("AssessmentSession", back_populates="risk_results")
