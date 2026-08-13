import uuid
import secrets
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from utils import ist_now


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, stored: str) -> bool:
    salt, pwd_hash = stored.split('$', 1)
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000).hex() == pwd_hash


def generate_token() -> str:
    return secrets.token_urlsafe(48)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=False)
    role = Column(String(20), default="admin", nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)

    sessions = relationship("AdminSession", back_populates="admin_user", cascade="all, delete-orphan")


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_user_id = Column(String(36), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=ist_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    admin_user = relationship("AdminUser", back_populates="sessions")

    @classmethod
    def create(cls, admin_user_id: str) -> "AdminSession":
        now = ist_now()
        return cls(
            admin_user_id=admin_user_id,
            token=generate_token(),
            created_at=now,
            expires_at=datetime(now.year + 1, now.month, now.day)
        )
