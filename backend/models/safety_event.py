import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class SafetyEvent(Base):
    """Audit trail for module D (continuous safety monitoring). Created by
    services/safety_engine.py whenever a red-flag value or keyword is
    detected in any module or check-in answer. The rule engine, not the
    language model, decides every escalation."""
    __tablename__ = "safety_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), nullable=True)  # conversation_session or checkin_session id (either table)
    source_module = Column(String(20), nullable=False)  # which module surfaced the trigger
    trigger_code = Column(String(50), nullable=False)  # e.g. "chest_pain", "sugar_below_70", "foot_blackening"
    trigger_detail = Column(String(500), nullable=True)
    triggered_at = Column(DateTime, default=ist_now, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    escalation_script_delivered = Column(Boolean, default=False, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="safety_events")
