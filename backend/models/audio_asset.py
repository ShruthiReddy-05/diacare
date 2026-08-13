import uuid
from sqlalchemy import Column, String, DateTime, Integer
from database import Base
from utils import ist_now

class AudioAsset(Base):
    __tablename__ = "audio_assets"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    questionnaire_id = Column(String(50), nullable=False)
    questionnaire_version = Column(String(20), nullable=False)
    question_id = Column(String(50), nullable=False)
    language = Column(String(10), nullable=False) # "en", "ta"
    provider = Column(String(50), nullable=False) # "sarvam", "web_speech", "manual"
    voice_id = Column(String(50), nullable=True)
    content_hash = Column(String(64), nullable=False) # sha256 hash of text prompt + options
    file_path = Column(String(500), nullable=False)
    mime_type = Column(String(50), default="audio/mpeg", nullable=False)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=ist_now, nullable=False)
