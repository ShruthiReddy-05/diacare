import uuid
from sqlalchemy import Column, String, DateTime, JSON, Integer
from database import Base
from utils import ist_now


class CareContentRule(Base):
    """The content library referenced by the spec's design rule: 'every line
    in the plan must trace back to something the patient was actually asked'.
    Content whose release_tag is held (e.g. sick_day, festival_fasting) is
    retrieved only when the weekly check-in reports the matching trigger --
    see services/checkin_engine.py."""
    __tablename__ = "care_content_rules"

    id = Column(String(50), primary_key=True)  # manual ids, e.g. "CONTENT_001"
    module_id = Column(String(10), nullable=False)  # B1/B2/B3/M1/M2/M3/M4/C/D
    content_type = Column(String(20), nullable=False)  # goal/tip/warning/reminder/script
    condition_tags = Column(JSON, nullable=False)  # list of tags this content applies to
    release_tag = Column(String(30), nullable=True)  # null = always eligible; else held until triggered (e.g. "sick_day")
    text_en = Column(String(2000), nullable=False)
    text_ta = Column(String(2000), nullable=True)
    severity = Column(String(20), default="info", nullable=False)  # info/caution/medical_clearance/emergency
    precedence = Column(Integer, default=100, nullable=False)  # lower = higher priority
    source_reference = Column(String(200), nullable=False)  # ICMR section / AADE7 domain, for traceability
    review_status = Column(String(20), default="draft", nullable=False)  # draft/approved/retired
    created_at = Column(DateTime, default=ist_now, nullable=False)
    updated_at = Column(DateTime, default=ist_now, onupdate=ist_now, nullable=False)
