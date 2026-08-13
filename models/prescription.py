import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Boolean
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now

class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    plan_type = Column(String(50), nullable=False) # e.g. plan_a, plan_b, medical_clearance, light_activity
    prescription_snapshot = Column(JSON, nullable=False) # Stores the complete AiExercisePrescription payload
    needs_progression = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)
    
    user = relationship("User", back_populates="prescriptions")
    session = relationship("AssessmentSession", back_populates="prescriptions")
    ai_outputs = relationship("AiPrescriptionOutput", back_populates="final_prescription")

class AiPrescriptionRequest(Base):
    __tablename__ = "ai_prescription_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    model_provider = Column(String(50), default="together", nullable=False)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.1, nullable=False)
    normalized_health_profile_json = Column(JSON, nullable=False)
    retrieved_rag_rule_ids = Column(JSON, nullable=False) # List of rule IDs
    created_at = Column(DateTime, default=ist_now, nullable=False)
    
    outputs = relationship("AiPrescriptionOutput", back_populates="request", cascade="all, delete-orphan")

class AiPrescriptionOutput(Base):
    __tablename__ = "ai_prescription_outputs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String(36), ForeignKey("ai_prescription_requests.id", ondelete="CASCADE"), nullable=False)
    raw_model_output_json = Column(JSON, nullable=False)
    validated_output_json = Column(JSON, nullable=True)
    validation_status = Column(String(50), nullable=False) # "passed", "failed", "fallback"
    rejection_reason = Column(String(500), nullable=True)
    final_prescription_id = Column(String(36), ForeignKey("prescriptions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)
    
    request = relationship("AiPrescriptionRequest", back_populates="outputs")
    final_prescription = relationship("Prescription", back_populates="ai_outputs")
