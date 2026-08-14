import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class ModuleOutcome(Base):
    """Derived output of one AADE7 self-care module (M1-M4) for a user.
    One row per (user_id, module_id), updated in place on re-assessment.
    output_json holds the module's full structured result (e.g. for M1: all
    candidate goals ranked by gap size, plus which two are currently active --
    this is how the fortnight goal-rotation in the spec's design rule works)."""
    __tablename__ = "module_outcomes"
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_module_outcome_user_module"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="SET NULL"), nullable=True)
    module_id = Column(String(10), nullable=False)  # M1, M2, M3, M4
    output_json = Column(JSON, nullable=False)
    computed_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)

    user = relationship("User", back_populates="module_outcomes")
