import uuid
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Boolean
from database import Base
from utils import ist_now

class TemporaryAudio(Base):
    __tablename__ = "temporary_audio"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    care_plan_id = Column(String(36), ForeignKey("care_plans.id", ondelete="CASCADE"), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    language = Column(String(10), nullable=False)
    provider = Column(String(50), nullable=False)
    voice_id = Column(String(50), nullable=True)
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(50), default="audio/wav", nullable=False)
    generation_attempts = Column(Integer, default=1, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)
