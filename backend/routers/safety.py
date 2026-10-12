from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.user import User
from schemas.safety_event import SafetyLockStatus
from services.safety_engine import EMERGENCY_SCRIPT
from services.safety_lock import build_lock_status, emergency_script_language

# Deliberately NOT guarded by require_no_open_safety_event: a locked patient
# must always be able to fetch the emergency script and their lock status.
# There is no patient-facing way to unlock -- see POST /api/admin/safety-events/{id}/acknowledge.
router = APIRouter(prefix="/api/safety", tags=["Safety"])


@router.get("/emergency-script")
async def get_emergency_script(language: str = "en"):
    lang = emergency_script_language(language)
    return {"language": lang, "emergency_script": EMERGENCY_SCRIPT[lang]}


@router.get("/user/{user_id}/status", response_model=SafetyLockStatus)
async def get_lock_status(user_id: str, db: AsyncSession = Depends(get_db)):
    if not (await db.execute(select(User.id).where(User.id == user_id))).scalar():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return await build_lock_status(user_id, db)
