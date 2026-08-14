import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class CarePlan(Base):
    """The assembled 'My Care Plan' -- produced entirely by
    services/care_plan_generator.py from stored BaselineProfile /
    ModuleOutcome rows. No network/LLM call is ever involved in producing
    plan_snapshot; the LLM layer only speaks and listens to this content."""
    __tablename__ = "care_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="SET NULL"), nullable=True)
    risk_tier = Column(String(10), nullable=True)  # red/amber/green, mirrors BaselineProfile.overall_risk_tier
    plan_snapshot = Column(JSON, nullable=False)  # sections a-f + conditional/escalation blocks
    traceability = Column(JSON, nullable=False)  # {"plan.dietaryGoals[0]": ["m1_rice_cups", "b1_..."], ...}
    created_at = Column(DateTime, default=ist_now, nullable=False)

    user = relationship("User", back_populates="care_plans")
