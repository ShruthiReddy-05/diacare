"""Server-side enforcement of the Module D coaching halt.

While a patient has any open safety event, every coaching / care-plan /
check-in-progression endpoint answers HTTP 423 with the fixed emergency
script from services/safety_engine.py -- never generated or reworded text.
Only a clinician acknowledging the event (routers/admin.py) lifts the lock.

The engine itself stays pure; this module only reads its constant.
"""
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.care_plan import CarePlan
from models.safety_event import SafetyEvent, SAFETY_STATUS_OPEN
from models.temporary_audio import TemporaryAudio
from models.user import User
from schemas.safety_event import SafetyLockStatus
from services.safety_engine import EMERGENCY_SCRIPT

HTTP_423_LOCKED = 423
DEFAULT_SCRIPT_LANGUAGE = "en"


def emergency_script_language(preferred_language: Optional[str]) -> str:
    return preferred_language if preferred_language in EMERGENCY_SCRIPT else DEFAULT_SCRIPT_LANGUAGE


async def get_open_safety_events(user_id: str, db: AsyncSession) -> List[SafetyEvent]:
    stmt = (
        select(SafetyEvent)
        .where(SafetyEvent.user_id == user_id, SafetyEvent.status == SAFETY_STATUS_OPEN)
        .order_by(SafetyEvent.triggered_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def build_lock_status(user_id: str, db: AsyncSession, mark_delivered: bool = True) -> SafetyLockStatus:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    language = emergency_script_language(user.preferred_language if user else None)
    events = await get_open_safety_events(user_id, db)
    if not events:
        return SafetyLockStatus(locked=False, language=language)

    if mark_delivered and any(not e.escalation_script_delivered for e in events):
        for e in events:
            e.escalation_script_delivered = True
        await db.commit()

    codes: List[str] = []
    for e in events:
        if e.trigger_code not in codes:
            codes.append(e.trigger_code)
    return SafetyLockStatus(
        locked=True,
        event_code=events[0].trigger_code,
        event_id=events[0].id,
        open_event_codes=codes,
        language=language,
        emergency_script=EMERGENCY_SCRIPT[language],
    )


async def raise_if_locked(user_id: str, db: AsyncSession) -> None:
    lock = await build_lock_status(user_id, db)
    if lock.locked:
        raise HTTPException(status_code=HTTP_423_LOCKED, detail={"error": "safety_lock", **lock.model_dump()})


async def _resolve_patient_id(request: Request, db: AsyncSession) -> Optional[str]:
    """Find whose content a request is for, from whichever identifier the
    route carries. Unknown ids resolve to None and the route itself 404s."""
    params = {**request.query_params, **request.path_params}
    if params.get("user_id"):
        return params["user_id"]
    if params.get("care_plan_id"):
        return (await db.execute(select(CarePlan.user_id).where(CarePlan.id == params["care_plan_id"]))).scalar()
    if params.get("asset_id"):
        return (await db.execute(select(TemporaryAudio.user_id).where(TemporaryAudio.id == params["asset_id"]))).scalar()
    return None


async def require_no_open_safety_event(request: Request, db: AsyncSession = Depends(get_db)) -> None:
    """Attach to every route/router that delivers coaching or clinical content."""
    user_id = await _resolve_patient_id(request, db)
    if user_id:
        await raise_if_locked(user_id, db)
