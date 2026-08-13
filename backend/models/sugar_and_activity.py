import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Boolean, Date
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now

class SugarReading(Base):
    __tablename__ = "sugar_readings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reading_type = Column(String(20), nullable=False) # "fasting", "post_meal", "hba1c"
    value = Column(Float, nullable=False) # mg/dL for glucose, % for HbA1c
    recorded_at = Column(DateTime, default=ist_now, nullable=False)
    notes = Column(String(200), nullable=True)
    
    user = relationship("User", back_populates="sugar_readings")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_date = Column(Date, nullable=False)
    completed_minutes = Column(Integer, default=0, nullable=False)
    completed_days = Column(Integer, default=0, nullable=False)
    strength_completed = Column(Boolean, default=False, nullable=False)
    fatigue_rating = Column(Integer, nullable=True) # 1-5 scale
    difficulty_rating = Column(Integer, nullable=True) # 1-5 scale
    safety_flag = Column(Boolean, default=False, nullable=False) # True if chest pain, dizziness etc.
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)
    
    user = relationship("User", back_populates="activity_logs")

# Also let's add ActivityLog relationship to User back in user.py
# Wait, we will modify backend/models/user.py to include this relationship.
