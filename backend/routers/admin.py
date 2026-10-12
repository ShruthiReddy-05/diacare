import logging
import os
import time
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import timedelta
from utils import ist_now

from database import get_db
from models.admin_user import AdminUser, AdminSession, verify_password, hash_password
from models.notification import NotificationEvent, NotificationSubscription
from models.checkin import CheckInSession, WeeklyDomainMetric
from models.audio_asset import AudioAsset
from models.temporary_audio import TemporaryAudio
from models.user import User, AppSession
from models.conversation import ConversationSession, ConversationResponse
from models.baseline_profile import BaselineProfile
from models.care_plan import CarePlan
from models.safety_event import SafetyEvent, SAFETY_STATUS_OPEN, SAFETY_STATUS_ACKNOWLEDGED
from schemas.safety_event import SafetyEventAcknowledge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

_metrics_cache: dict = {}
CACHE_TTL_SECS = 60


def _get_cached(key: str):
    entry = _metrics_cache.get(key)
    if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECS:
        return entry["data"]
    return None


def _set_cached(key: str, data: Any):
    _metrics_cache[key] = {"data": data, "ts": time.time()}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    adminId: str
    displayName: str
    role: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


async def get_current_admin(authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    token = authorization[7:]
    stmt = select(AdminSession).where(AdminSession.token == token, AdminSession.expires_at > ist_now())
    result = await db.execute(stmt)
    session = result.scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    admin_res = await db.execute(select(AdminUser).where(AdminUser.id == session.admin_user_id))
    admin = admin_res.scalar()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin


@router.post("/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(AdminUser).where(AdminUser.username == body.username)
    result = await db.execute(stmt)
    admin = result.scalar()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session = AdminSession.create(admin.id)
    db.add(session)
    await db.commit()
    return LoginResponse(token=session.token, adminId=admin.id, displayName=admin.display_name, role=admin.role)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    admin.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/seed")
async def seed_admin(db: AsyncSession = Depends(get_db)):
    stmt = select(AdminUser).where(AdminUser.username == "admin")
    result = await db.execute(stmt)
    if result.scalar():
        return {"message": "Admin already exists"}
    admin = AdminUser(username="admin", password_hash=hash_password("diafit2024"), display_name="Admin", role="admin")
    db.add(admin)
    await db.commit()
    return {"message": "Admin created successfully | username: admin | password: diafit2024"}


@router.get("/health")
async def admin_health(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    start = time.time()
    health_info = {"status": "ok", "timestamp": ist_now().isoformat(), "responseTimeMs": 0, "db": "unknown", "cacheEntries": len(_metrics_cache)}
    try:
        await db.execute(select(func.count(User.id)))
        health_info["db"] = "connected"
    except Exception as e:
        health_info["db"] = f"error: {e}"
        health_info["status"] = "degraded"
    health_info["responseTimeMs"] = round((time.time() - start) * 1000, 1)
    return health_info


@router.get("/metrics/overview")
async def get_overview_metrics(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    force_refresh: bool = Query(False, alias="force_refresh"),
):
    if not force_refresh:
        cached = _get_cached("overview")
        if cached:
            return cached

    now = ist_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_today = (await db.execute(
        select(func.count(func.distinct(AppSession.user_id))).where(AppSession.started_at >= today_start)
    )).scalar() or 0
    active_week = (await db.execute(
        select(func.count(func.distinct(AppSession.user_id))).where(AppSession.started_at >= today_start - timedelta(days=7))
    )).scalar() or 0

    baseline_completed = (await db.execute(select(func.count(BaselineProfile.id)))).scalar() or 0
    conv_completed = (await db.execute(
        select(func.count(ConversationSession.id)).where(ConversationSession.status == "completed")
    )).scalar() or 0
    conv_in_progress = (await db.execute(
        select(func.count(ConversationSession.id)).where(ConversationSession.status == "in_progress")
    )).scalar() or 0

    risk_tier_rows = (await db.execute(
        select(BaselineProfile.overall_risk_tier, func.count(BaselineProfile.id)).group_by(BaselineProfile.overall_risk_tier)
    )).all()
    risk_tier_distribution = [{"tier": r[0] or "unknown", "count": r[1]} for r in risk_tier_rows]

    checkins_completed = (await db.execute(
        select(func.count(CheckInSession.id)).where(CheckInSession.status == "completed")
    )).scalar() or 0
    checkins_missed = (await db.execute(
        select(func.count(CheckInSession.id)).where(CheckInSession.status == "missed")
    )).scalar() or 0
    checkins_escalated = (await db.execute(
        select(func.count(CheckInSession.id)).where(CheckInSession.status == "escalated")
    )).scalar() or 0

    open_safety_events = (await db.execute(
        select(func.count(SafetyEvent.id)).where(SafetyEvent.status == SAFETY_STATUS_OPEN)
    )).scalar() or 0

    reassessments_triggered = (await db.execute(
        select(func.count(WeeklyDomainMetric.id)).where(WeeklyDomainMetric.reassessment_triggered == True)
    )).scalar() or 0

    payload = {
        "totalUsers": total_users,
        "activeToday": active_today,
        "activeThisWeek": active_week,
        "baselineCompleted": baseline_completed,
        "conversationSessionsCompleted": conv_completed,
        "conversationSessionsInProgress": conv_in_progress,
        "riskTierDistribution": risk_tier_distribution,
        "checkinsCompleted": checkins_completed,
        "checkinsMissed": checkins_missed,
        "checkinsEscalated": checkins_escalated,
        "openSafetyEvents": open_safety_events,
        "reassessmentsTriggered": reassessments_triggered,
    }
    _set_cached("overview", payload)
    return payload


@router.get("/users")
async def get_users_list(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    search: str = "",
    page: int = 1,
    limit: int = 10,
):
    limit = min(max(limit, 1), 100)

    search_filter = True
    if search:
        pattern = f"%{search}%"
        search_filter = or_(
            User.display_user_id.ilike(pattern), User.first_name.ilike(pattern), User.last_name.ilike(pattern)
        )

    total = (await db.execute(select(func.count(User.id)).where(search_filter))).scalar() or 0

    risk_tier_subq = (
        select(BaselineProfile.overall_risk_tier).where(BaselineProfile.user_id == User.id).correlate(User).scalar_subquery()
    )
    checkins_due_subq = (
        select(func.count(CheckInSession.id))
        .where(CheckInSession.user_id == User.id, CheckInSession.status == "due")
        .correlate(User).scalar_subquery()
    )

    stmt = (
        select(User, risk_tier_subq.label("risk_tier"), checkins_due_subq.label("checkins_due"))
        .where(search_filter)
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    users = [
        {
            "id": r.User.id,
            "displayUserId": r.User.display_user_id,
            "firstName": r.User.first_name,
            "lastName": r.User.last_name,
            "preferredLanguage": r.User.preferred_language,
            "role": r.User.role,
            "createdAt": r.User.created_at,
            "riskTier": r.risk_tier or "not_assessed",
            "checkinsDue": r.checkins_due or 0,
        }
        for r in rows
    ]
    return {"users": users, "total": total, "page": page, "limit": limit, "totalPages": -(total // -limit)}


@router.get("/users/{user_id}/detail")
async def get_user_detail(user_id: str, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    baseline = (await db.execute(select(BaselineProfile).where(BaselineProfile.user_id == user_id))).scalar()
    care_plans = (await db.execute(
        select(CarePlan).where(CarePlan.user_id == user_id).order_by(CarePlan.created_at.desc())
    )).scalars().all()
    checkins = (await db.execute(
        select(CheckInSession).where(CheckInSession.user_id == user_id).order_by(CheckInSession.due_date.desc())
    )).scalars().all()
    safety_events = (await db.execute(
        select(SafetyEvent).where(SafetyEvent.user_id == user_id).order_by(SafetyEvent.triggered_at.desc())
    )).scalars().all()

    return {
        "user": {
            "id": user.id, "displayUserId": user.display_user_id, "firstName": user.first_name,
            "lastName": user.last_name, "preferredLanguage": user.preferred_language,
            "role": user.role, "createdAt": user.created_at,
        },
        "baselineProfile": {
            "overallRiskTier": baseline.overall_risk_tier, "bmiCategory": baseline.bmi_category,
            "glycemicCategory": baseline.glycemic_category, "computedAt": baseline.computed_at,
        } if baseline else None,
        "carePlans": [{"id": p.id, "riskTier": p.risk_tier, "createdAt": p.created_at} for p in care_plans],
        "checkinSessions": [{"id": c.id, "programWeek": c.program_week, "status": c.status, "dueDate": c.due_date} for c in checkins],
        "safetyEvents": [_safety_event_row(e) for e in safety_events],
    }


def _safety_event_row(e: SafetyEvent, user: Optional[User] = None, acknowledger: Optional[AdminUser] = None) -> dict:
    row = {
        "id": e.id, "userId": e.user_id, "triggerCode": e.trigger_code, "sourceModule": e.source_module,
        "status": e.status, "resolved": e.resolved, "triggeredAt": e.triggered_at,
        "acknowledgedAt": e.acknowledged_at, "acknowledgedBy": e.acknowledged_by,
        "acknowledgementNote": e.acknowledgement_note,
    }
    if user is not None:
        row.update({"displayUserId": user.display_user_id, "firstName": user.first_name, "lastName": user.last_name})
    if acknowledger is not None:
        row["acknowledgedByName"] = acknowledger.display_name
    return row


@router.get("/safety-events")
async def list_safety_events(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    status_filter: str = Query(SAFETY_STATUS_OPEN, alias="status"),
):
    """Dashboard queue of Module D events; default is the open (locking) ones."""
    stmt = select(SafetyEvent, User).join(User, User.id == SafetyEvent.user_id).order_by(SafetyEvent.triggered_at.desc())
    if status_filter != "all":
        stmt = stmt.where(SafetyEvent.status == status_filter)
    rows = (await db.execute(stmt.limit(200))).all()
    return [_safety_event_row(e, u) for e, u in rows]


@router.post("/safety-events/{event_id}/acknowledge")
async def acknowledge_safety_event(
    event_id: str,
    body: SafetyEventAcknowledge,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """The only way to lift a Module D coaching lock. Requires an admin
    (clinician) session token -- patients have no route to this."""
    event = (await db.execute(select(SafetyEvent).where(SafetyEvent.id == event_id))).scalar()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety event not found")
    if event.status != SAFETY_STATUS_OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Safety event already acknowledged")

    event.status = SAFETY_STATUS_ACKNOWLEDGED
    event.resolved = True
    event.acknowledged_at = ist_now()
    event.acknowledged_by = admin.id
    event.acknowledgement_note = body.note
    await db.commit()
    await db.refresh(event)
    _metrics_cache.pop("overview", None)

    remaining_open = (await db.execute(
        select(func.count(SafetyEvent.id)).where(SafetyEvent.user_id == event.user_id, SafetyEvent.status == SAFETY_STATUS_OPEN)
    )).scalar() or 0
    return {**_safety_event_row(event, acknowledger=admin), "patientStillLocked": remaining_open > 0}


@router.get("/export/responses")
async def export_responses(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """Every baseline/assessment answer ever given, one row per question, for
    download as CSV (opens directly in Excel)."""
    stmt = (
        select(ConversationResponse, User, ConversationSession)
        .join(ConversationSession, ConversationSession.id == ConversationResponse.session_id)
        .join(User, User.id == ConversationSession.user_id)
        .order_by(User.display_user_id, ConversationResponse.answered_at)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "displayUserId": u.display_user_id,
            "firstName": u.first_name,
            "lastName": u.last_name,
            "sitting": sess.sitting,
            "moduleId": r.module_id,
            "questionId": r.question_id,
            "questionTextEn": r.question_text_en,
            "answerValue": r.answer_value,
            "language": r.language,
            "inputModality": r.input_modality,
            "answeredAt": r.answered_at.isoformat() if r.answered_at else None,
        }
        for r, u, sess in rows
    ]


@router.get("/export/checkins")
async def export_checkins(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    """Every weekly check-in answer ever recorded, one row per check-in, for
    download as CSV (opens directly in Excel)."""
    stmt = (
        select(CheckInSession, User)
        .join(User, User.id == CheckInSession.user_id)
        .order_by(User.display_user_id, CheckInSession.due_date)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "displayUserId": u.display_user_id,
            "firstName": u.first_name,
            "lastName": u.last_name,
            "programWeek": c.program_week,
            "dueDate": c.due_date.isoformat() if c.due_date else None,
            "status": c.status,
            "activityDays": c.q1_activity_days,
            "foodGoalDays": c.q2_food_goal_days,
            "medicationDays": c.q3_medication_days,
            "footCareDays": c.q4_foot_care_days,
            "newFootProblem": c.q5_new_foot_problem,
            "stress0to10": c.q6_stress_0_10,
            "sleep0to10": c.q7_sleep_0_10,
            "sugarReading": c.q8_sugar_reading,
            "hypoEpisode": c.q8b_hypo_episode,
            "safetyFlag": c.safety_flag,
            "completedAt": c.completed_at.isoformat() if c.completed_at else None,
        }
        for c, u in rows
    ]


class AudioGenerateRequest(BaseModel):
    questionnaire_id: Optional[str] = None
    language: Optional[str] = None
    force_regen: bool = False


@router.post("/audio-assets/generate")
async def admin_generate_audio(body: AudioGenerateRequest, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    from services.audio_generation import load_questionnaires, run_generation
    all_qs = load_questionnaires()
    if not all_qs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No conversation script files found")
    summary = await run_generation(db, body.questionnaire_id, body.language, body.force_regen)
    if "error" in summary:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=summary["error"])
    return summary


@router.get("/audio-assets/missing")
async def admin_missing_audio(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    from services.audio_generation import load_questionnaires, resolve_prompt, content_hash, LANGUAGES
    all_qs = load_questionnaires()
    if not all_qs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No conversation script files found")

    existing_assets = (await db.execute(select(AudioAsset))).scalars().all()
    existing_set = {(a.questionnaire_id, a.question_id, a.language, a.content_hash) for a in existing_assets}

    missing = []
    for q in all_qs:
        q_id = q["id"]
        q_version = q.get("version", "1.0.0")
        for mod in q.get("modules", []):
            for question in mod.get("questions", []):
                qq_id = question["id"]
                for lang_key in LANGUAGES:
                    text = resolve_prompt(question, lang_key)
                    if not text:
                        continue
                    ch = content_hash(text)
                    if (q_id, qq_id, lang_key, ch) not in existing_set:
                        missing.append({"questionnaireId": q_id, "questionnaireVersion": q_version, "questionId": qq_id, "language": lang_key})
    return {"missing": missing, "total": len(missing)}


BROADCAST_TITLES = {"checkin": "Weekly Check-In", "medication_reminder": "Medicine Time", "sugar_test": "Time to Check Your Sugar"}
BROADCAST_BODIES = {
    "checkin": "Eight quick questions, about 5 minutes. Let's see how this week went.",
    "medication_reminder": "Time for your medicine.",
    "sugar_test": "Please record your latest blood sugar or HbA1c reading.",
}
BROADCAST_URLS = {"checkin": "/checkin", "medication_reminder": "/home", "sugar_test": "/sugar"}


class BroadcastRequest(BaseModel):
    type: str


@router.post("/backup/trigger")
async def trigger_backup(admin: AdminUser = Depends(get_current_admin)):
    import threading
    threading.Thread(target=_run_backup_manual, daemon=True).start()
    return {"message": "Backup started in background"}


def _run_backup_manual():
    from services.backup_service import do_backup
    do_backup(triggered_by="manual")


@router.post("/notifications/broadcast")
async def broadcast_notification(body: BroadcastRequest, db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    if body.type not in BROADCAST_TITLES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Choose from: {', '.join(BROADCAST_TITLES.keys())}")

    from services.push_notification_service import send_push_to_user
    user_ids = [row[0] for row in (await db.execute(select(func.distinct(NotificationSubscription.user_id)))).all()]

    sent_count, failed_count = 0, 0
    for uid in user_ids:
        try:
            await send_push_to_user(user_id=uid, notif_type=body.type, title=BROADCAST_TITLES[body.type],
                                     body=BROADCAST_BODIES[body.type], url=BROADCAST_URLS[body.type], db=db)
            sent_count += 1
        except Exception as e:
            logger.warning("Broadcast failed for user %s: %s", uid, e)
            failed_count += 1

    return {"type": body.type, "totalUsersWithSubscriptions": len(user_ids), "sent": sent_count, "failed": failed_count}


@router.post("/temporary-audio/cleanup")
async def cleanup_temporary_audio(db: AsyncSession = Depends(get_db), admin: AdminUser = Depends(get_current_admin)):
    now = ist_now()
    expired = (await db.execute(select(TemporaryAudio).where(TemporaryAudio.expires_at < now))).scalars().all()
    deleted_count = 0
    for asset in expired:
        try:
            if os.path.isfile(asset.file_path):
                os.remove(asset.file_path)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", asset.file_path, e)
        await db.delete(asset)
        deleted_count += 1
    await db.commit()
    return {"deleted": deleted_count, "message": f"Cleaned up {deleted_count} expired audio asset(s)"}
