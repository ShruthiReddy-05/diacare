import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


class BaselineProfile(Base):
    """The single source of truth for a user's derived B1-B3 clinical status.
    Recomputed (in place) whenever the baseline conversation (A + B1-B3) is
    completed or corrected. Every field here must trace back to an answered
    question -- see services/b1_engine.py, b2_engine.py, b3_engine.py."""
    __tablename__ = "baseline_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    session_id = Column(String(36), ForeignKey("conversation_sessions.id", ondelete="SET NULL"), nullable=True)

    # --- B1: basic profile ---
    age_band = Column(String(20), nullable=True)  # "under_60" / "60_and_above"
    bmi = Column(Float, nullable=True)
    bmi_category = Column(String(20), nullable=True)  # underweight/normal/overweight/obese (Asian cutoffs 23/25)
    waist_risk = Column(Boolean, default=False, nullable=False)  # M>90cm, F>80cm
    ideal_body_weight_kg = Column(Float, nullable=True)
    daily_energy_kcal = Column(Float, nullable=True)  # 25 kcal/kg IBW
    occupational_activity_level = Column(String(20), nullable=True)  # sitting/standing/heavy
    sedentary_work_flag = Column(Boolean, default=False, nullable=False)

    # --- B2: diabetes profile ---
    glycemic_category = Column(String(20), nullable=True)  # target/satisfactory/unsatisfactory
    duration_risk_flag = Column(Boolean, default=False, nullable=False)  # duration > 5 years
    bp_category = Column(String(20), nullable=True)  # target/elevated/high
    salt_target_g = Column(Float, nullable=True)  # 5 default, 3 if hypertensive
    regimen_class = Column(String(30), nullable=True)  # metformin_only/sulfonylurea/insulin
    hypoglycemia_risk_flag = Column(Boolean, default=False, nullable=False)
    herbal_use_flag = Column(Boolean, default=False, nullable=False)
    follow_up_gap_flag = Column(Boolean, default=False, nullable=False)  # last visit > 3 months
    screening_overdue = Column(JSON, nullable=True)  # {"eye": bool, "foot": bool, "renal": bool}

    # --- B3: risk & complication screening ---
    complication_profile = Column(JSON, nullable=True)  # {"neuropathy":bool,"retinopathy":bool,"nephropathy":bool,"cad":bool}
    foot_risk_category = Column(String(20), nullable=True)  # low/moderate/high/active_foot_disease
    exercise_clearance_required = Column(Boolean, default=False, nullable=False)
    tobacco_flag = Column(Boolean, default=False, nullable=False)
    alcohol_flag = Column(Boolean, default=False, nullable=False)
    overall_risk_tier = Column(String(10), nullable=True)  # red/amber/green

    computed_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)

    user = relationship("User", back_populates="baseline_profile")
