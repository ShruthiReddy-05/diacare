import uuid
from sqlalchemy import Column, String, DateTime, JSON, Integer
from database import Base
from utils import ist_now

class ExerciseRagRule(Base):
    __tablename__ = "exercise_rag_rules"
    
    id = Column(String(50), primary_key=True) # Let's allow manual string IDs like "RAG_001"
    source_type = Column(String(50), nullable=False) # "at4_logic", "expert_interview", "patient_interview", "clinical_review"
    source_name = Column(String(100), nullable=False)
    source_sheet = Column(String(100), nullable=True)
    condition_tags = Column(JSON, nullable=False) # list of tags like ["obesity", "hypoglycemia_risk"]
    contraindication_tags = Column(JSON, nullable=False) # list of tags
    allowed_exercise_tags = Column(JSON, nullable=False) # list of allowed tags
    prohibited_exercise_tags = Column(JSON, nullable=False) # list of prohibited tags
    recommendation = Column(String(2000), nullable=False)
    rationale = Column(String(2000), nullable=True)
    severity = Column(String(50), default="info", nullable=False) # "info", "caution", "medical_clearance", "stop_exercise"
    precedence = Column(Integer, default=100, nullable=False)
    review_status = Column(String(20), default="draft", nullable=False) # "draft", "approved", "retired"
    created_at = Column(DateTime, default=ist_now, nullable=False)
    updated_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)
