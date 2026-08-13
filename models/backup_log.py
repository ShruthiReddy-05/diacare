import uuid
from sqlalchemy import Column, String, DateTime
from database import Base
from utils import ist_now


class BackupLog(Base):
    __tablename__ = "backup_log"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    last_backup_at = Column(DateTime, nullable=False, default=ist_now)
    triggered_by = Column(String(20), nullable=False, default="auto")  # "auto" | "manual"
