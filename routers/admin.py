import asyncio
import logging
import os
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, case, or_, and_
from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime, timedelta, date
from utils import ist_now

from database import get_db
from models.admin_user import AdminUser, AdminSession, verify_password
from models.follow_up import FollowUpSession, FollowUpSchedule, NotificationEvent, Reminder, WeeklyUserMetric, NotificationSubscription
from models.audio_asset import AudioAsset
from models.temporary_audio import TemporaryAudio
from models.user import User, AppSession
from models.assessment import AssessmentSession, RiskResult, QuestionResponse
from models.prescription import Prescription
from models.sugar_and_activity import SugarReading, ActivityLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

# ── Simple in-memory cache ──
_metrics_cache: dict[str, Any] = {}
CACHE_TTL_SECS = 60

def _cache_key(days: int) -> str:
    return f"comprehensive:{days}"

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


async def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    token = authorization[7:]
    stmt = select(AdminSession).where(
        AdminSession.token == token,
        AdminSession.expires_at > ist_now()
    )
    result = await db.execute(stmt)
    session = result.scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    admin_stmt = select(AdminUser).where(AdminUser.id == session.admin_user_id)
    admin_res = await db.execute(admin_stmt)
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
    return LoginResponse(
        token=session.token,
        adminId=admin.id,
        displayName=admin.display_name,
        role=admin.role
    )


@router.post("/seed")
async def seed_admin(db: AsyncSession = Depends(get_db)):
    stmt = select(AdminUser).where(AdminUser.username == "admin")
    result = await db.execute(stmt)
    existing = result.scalar()
    if existing:
        return {"message": "Admin already exists"}
    from models.admin_user import hash_password
    admin = AdminUser(
        username="admin",
        password_hash=hash_password("diafit2024"),
        display_name="Admin",
        role="admin"
    )
    db.add(admin)
    await db.commit()
    return {"message": "Admin created successfully | username: admin | password: diafit2024"}


@router.get("/metrics/comprehensive")
async def get_comprehensive_metrics(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    days: int = Query(30, alias="days", ge=1, le=365, description="Lookback window for active-user metrics"),
    force_refresh: bool = Query(False, alias="force_refresh"),
):
    now = ist_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    lookback = today_start - timedelta(days=days)

    ckey = _cache_key(days)
    if not force_refresh:
        cached = _get_cached(ckey)
        if cached:
            return cached

    # ── Execute all independent queries in parallel ──
    results = {}

    async def run(key, stmt):
        results[key] = await db.execute(stmt)

    batch = [
        run("total_users", select(func.count(User.id))),
        run("active_today", select(func.count(func.distinct(AppSession.user_id))).where(AppSession.started_at >= today_start)),
        run("active_lookback", select(func.count(func.distinct(AppSession.user_id))).where(AppSession.started_at >= lookback)),
        run("active_week", select(func.count(func.distinct(AppSession.user_id))).where(AppSession.started_at >= (today_start - timedelta(days=7)))),
        run("lang_rows", select(User.preferred_language, func.count(User.id).label("cnt")).group_by(User.preferred_language)),
        run("streak_rows", select(WeeklyUserMetric, User.display_user_id, User.first_name, User.last_name).join(User, User.id == WeeklyUserMetric.user_id)),
        run("completed_assess", select(func.count(AssessmentSession.id)).where(AssessmentSession.status == "completed")),
        run("abandoned_assess", select(func.count(AssessmentSession.id)).where(AssessmentSession.status == "abandoned")),
        run("in_progress_assess", select(func.count(AssessmentSession.id)).where(AssessmentSession.status == "in_progress")),
        run("per_user_assess", select(
            AssessmentSession.user_id, User.display_user_id, User.first_name, User.last_name,
            func.count(AssessmentSession.id).label("cnt"),
        ).join(User, User.id == AssessmentSession.user_id)
          .group_by(AssessmentSession.user_id, User.display_user_id, User.first_name, User.last_name)
          .order_by(func.count(AssessmentSession.id).desc())),
        run("avg_time", select(func.avg(
            (func.extract('epoch', AssessmentSession.completed_at) - func.extract('epoch', AssessmentSession.started_at)) / 60
        )).where(AssessmentSession.status == "completed", AssessmentSession.completed_at.isnot(None),
            (func.extract('epoch', AssessmentSession.completed_at) - func.extract('epoch', AssessmentSession.started_at)) / 60 < 180)),
        run("drop_rows", select(
            QuestionResponse.question_id, QuestionResponse.module_id,
            func.count(func.distinct(QuestionResponse.session_id)).label("response_count"),
        ).group_by(QuestionResponse.question_id, QuestionResponse.module_id)
          .order_by(QuestionResponse.module_id, QuestionResponse.question_id)),
        run("total_fu", select(func.count(FollowUpSession.id))),
        run("fu_due", select(func.count(FollowUpSession.id)).where(FollowUpSession.status == "due")),
        run("fu_completed", select(func.count(FollowUpSession.id)).where(FollowUpSession.status == "completed")),
        run("fu_missed", select(func.count(FollowUpSession.id)).where(FollowUpSession.status == "missed")),
        run("fu_overdue", select(func.count(FollowUpSession.id)).where(FollowUpSession.status == "due", FollowUpSession.due_date < date.today())),
        run("per_user_fu", select(
            FollowUpSession.user_id, User.display_user_id, User.first_name, User.last_name,
            func.count(FollowUpSession.id).label("total"),
            func.sum(case((FollowUpSession.status == "due", 1), else_=0)).label("due_count"),
            func.sum(case((FollowUpSession.status == "completed", 1), else_=0)).label("completed_count"),
        ).join(User, User.id == FollowUpSession.user_id)
          .group_by(FollowUpSession.user_id, User.display_user_id, User.first_name, User.last_name)
          .order_by(func.count(FollowUpSession.id).desc())),
        run("pres_snapshots", select(Prescription.plan_type, Prescription.prescription_snapshot)),
        run("plan_rows", select(Prescription.plan_type, func.count(Prescription.id).label("cnt")).group_by(Prescription.plan_type)),
        run("glycemic_rows", select(RiskResult.glycemic, func.count(RiskResult.id).label("cnt")).group_by(RiskResult.glycemic)),
        run("pa_rows", select(RiskResult.physical_activity, func.count(RiskResult.id).label("cnt")).group_by(RiskResult.physical_activity)),
        run("sed_rows", select(RiskResult.sedentary, func.count(RiskResult.id).label("cnt")).group_by(RiskResult.sedentary)),
        run("overall_rows", select(RiskResult.overall, func.count(RiskResult.id).label("cnt")).group_by(RiskResult.overall)),
        run("par_q", select(func.count(RiskResult.id)).where(RiskResult.par_q_clearance_required == True)),
        run("comp_rows", select(RiskResult.complication_flags).where(RiskResult.complication_flags.isnot(None))),
        run("bmi_rows", select(RiskResult.bmi_category, func.count(RiskResult.id).label("cnt")).group_by(RiskResult.bmi_category)),
        run("avg_minutes", select(func.avg(ActivityLog.completed_minutes))),
        run("avg_days", select(func.avg(ActivityLog.completed_days))),
        run("total_strength", select(func.count(ActivityLog.id))),
        run("strength_completed", select(func.count(ActivityLog.id)).where(ActivityLog.strength_completed == True)),
        run("total_sugar", select(func.count(SugarReading.id))),
        run("fasting", select(func.count(SugarReading.id)).where(SugarReading.reading_type == "fasting")),
        run("post_meal", select(func.count(SugarReading.id)).where(SugarReading.reading_type == "post_meal")),
        run("hba1c", select(func.count(SugarReading.id)).where(SugarReading.reading_type == "hba1c")),
        run("hba1c_users", select(func.count(func.distinct(SugarReading.user_id))).where(SugarReading.reading_type == "hba1c", SugarReading.recorded_at >= (now - timedelta(days=90)))),
        run("fasting_ranges", select(
            func.sum(case((SugarReading.value < 100, 1), else_=0)).label("range_below_100"),
            func.sum(case((and_(SugarReading.value >= 100, SugarReading.value < 126), 1), else_=0)).label("range_100_125"),
            func.sum(case((SugarReading.value >= 126, 1), else_=0)).label("range_126_plus"),
        ).where(SugarReading.reading_type == "fasting")),
        run("postmeal_ranges", select(
            func.sum(case((SugarReading.value < 140, 1), else_=0)).label("range_below_140"),
            func.sum(case((and_(SugarReading.value >= 140, SugarReading.value < 200), 1), else_=0)).label("range_140_199"),
            func.sum(case((SugarReading.value >= 200, 1), else_=0)).label("range_200_plus"),
        ).where(SugarReading.reading_type == "post_meal")),
        run("reminder_users", select(func.count(func.distinct(Reminder.user_id)))),
        run("push_sent", select(func.count(NotificationEvent.id)).where(NotificationEvent.sent_at.isnot(None))),
        run("push_delivered", select(func.count(NotificationEvent.id)).where(NotificationEvent.delivered_at.isnot(None))),
        run("push_opened", select(func.count(NotificationEvent.id)).where(NotificationEvent.opened_at.isnot(None))),
        run("push_action", select(func.count(NotificationEvent.id)).where(NotificationEvent.action_completed_at.isnot(None))),
        run("act_safety", select(func.count(ActivityLog.id)).where(ActivityLog.safety_flag == True)),
        run("fu_safety", select(func.count(FollowUpSession.id)).where(FollowUpSession.safety_flag == True)),
        run("escalation", select(func.count(FollowUpSession.id)).where(FollowUpSession.escalation_advice_given == True)),
    ]

    await asyncio.gather(*batch)

    def s(key):
        return results[key].scalar() or 0

    # ── User Overview ──
    total_users = s("total_users")
    active_today = s("active_today")
    active_week = s("active_week")
    active_lookback = s("active_lookback")  # for the custom date-range

    lang_rows = results["lang_rows"].all()
    language_distribution = [{"language": r.preferred_language, "count": r.cnt} for r in lang_rows]

    # Streaks: per-user MAX values then average (avoids misleading raw average)
    login_subq = (
        select(WeeklyUserMetric.user_id, func.max(WeeklyUserMetric.login_streak_weeks).label("streak"))
        .group_by(WeeklyUserMetric.user_id)
    ).subquery()
    adhere_subq = (
        select(WeeklyUserMetric.user_id, func.max(WeeklyUserMetric.adherence_streak_weeks).label("streak"))
        .group_by(WeeklyUserMetric.user_id)
    ).subquery()

    login_max_per_user_res = await db.execute(select(login_subq.c.streak))
    login_per_user_vals = [r.streak or 0 for r in login_max_per_user_res.all()]

    adhere_max_per_user_res = await db.execute(select(adhere_subq.c.streak))
    adhere_per_user_vals = [r.streak or 0 for r in adhere_max_per_user_res.all()]

    avg_login_streak = round(sum(login_per_user_vals) / len(login_per_user_vals), 1) if login_per_user_vals else 0
    max_login_streak = max(login_per_user_vals) if login_per_user_vals else 0
    avg_adherence_streak = round(sum(adhere_per_user_vals) / len(adhere_per_user_vals), 1) if adhere_per_user_vals else 0
    max_adherence_streak = max(adhere_per_user_vals) if adhere_per_user_vals else 0

    # Per-user display names for streaks
    login_streak_rows = (await db.execute(
        select(User.display_user_id, User.first_name, User.last_name, login_subq.c.streak)
        .join(User, User.id == login_subq.c.user_id)
        .order_by(login_subq.c.streak.desc())
    )).all()
    per_user_login_streaks = [
        {"displayUserId": r.display_user_id, "name": f"{r.first_name} {r.last_name}", "streakWeeks": r.streak or 0}
        for r in login_streak_rows
    ]

    adhere_streak_rows = (await db.execute(
        select(User.display_user_id, User.first_name, User.last_name, adhere_subq.c.streak)
        .join(User, User.id == adhere_subq.c.user_id)
        .order_by(adhere_subq.c.streak.desc())
    )).all()
    per_user_adherence_streaks = [
        {"displayUserId": r.display_user_id, "name": f"{r.first_name} {r.last_name}", "streakWeeks": r.streak or 0}
        for r in adhere_streak_rows
    ]

    user_overview = {
        "totalUsers": total_users,
        "activeToday": active_today,
        "activeThisWeek": active_week,
        "activeThisMonth": active_lookback,
        "languageDistribution": language_distribution,
        "avgLoginStreakWeeks": avg_login_streak,
        "maxLoginStreakWeeks": max_login_streak,
        "avgAdherenceStreakWeeks": avg_adherence_streak,
        "maxAdherenceStreakWeeks": max_adherence_streak,
        "perUserLoginStreaks": per_user_login_streaks,
        "perUserAdherenceStreaks": per_user_adherence_streaks,
    }

    # ── Assessment Metrics ──
    completed_assessments = s("completed_assess")
    abandoned_assessments = s("abandoned_assess")
    in_progress_assessments = s("in_progress_assess")
    total_assessment_sessions = completed_assessments + abandoned_assessments + in_progress_assessments

    # Fix completion rate: exclude in-progress
    completed_or_abandoned = completed_assessments + abandoned_assessments
    first_assessment_completion_rate = round(
        (completed_assessments / completed_or_abandoned * 100), 1
    ) if completed_or_abandoned > 0 else 0.0

    per_user_assess = results["per_user_assess"].all()
    per_user_assessment_sessions = [
        {"userId": r.user_id, "displayUserId": r.display_user_id, "name": f"{r.first_name} {r.last_name}", "count": r.cnt}
        for r in per_user_assess
    ]

    avg_time_row = results["avg_time"].scalar()
    avg_completion_time_minutes = round(float(avg_time_row), 1) if avg_time_row else 0.0

    # Drop-off: calculate true funnel decline
    drop_rows = results["drop_rows"].all()
    # Group by module, order question by response count descending (first question has most)
    # Calculate funnel: first question = 100%, subsequent show % drop from first
    module_questions = defaultdict(list)
    for r in drop_rows:
        module_questions[r.module_id].append({
            "questionId": r.question_id,
            "moduleId": r.module_id,
            "responseCount": r.response_count,
        })

    drop_off_by_question = []
    for mod_id, qs in module_questions.items():
        # Sort questions by module order (they come ordered from DB)
        if not qs:
            continue
        first_count = qs[0]["responseCount"]
        for q in qs:
            funnel_pct = round((q["responseCount"] / first_count * 100), 1) if first_count > 0 else 0
            drop_off_by_question.append({
                "questionId": q["questionId"],
                "moduleId": q["moduleId"],
                "responseCount": q["responseCount"],
                "funnelPercent": funnel_pct,
                "dropFromFirst": round(100 - funnel_pct, 1),
            })

    assessments_metrics = {
        "totalSessions": total_assessment_sessions,
        "completed": completed_assessments,
        "abandoned": abandoned_assessments,
        "inProgress": in_progress_assessments,
        "firstAssessmentCompletionRate": first_assessment_completion_rate,
        "avgCompletionTimeMinutes": avg_completion_time_minutes,
        "perUserSessions": per_user_assessment_sessions,
        "dropOffByQuestion": drop_off_by_question,
    }

    # ── Follow-up Metrics ──
    total_fu_sessions = s("total_fu")
    fu_due = s("fu_due")
    fu_completed = s("fu_completed")
    fu_missed = s("fu_missed")
    fu_overdue = s("fu_overdue")
    fu_completion_rate = round(
        (fu_completed / total_fu_sessions * 100), 1
    ) if total_fu_sessions > 0 else 0.0

    per_user_fu = results["per_user_fu"].all()
    follow_up_metrics = {
        "totalSessions": total_fu_sessions,
        "due": fu_due,
        "completed": fu_completed,
        "missed": fu_missed,
        "overdue": fu_overdue,
        "completionRate": fu_completion_rate,
        "perUserSessions": [
            {"displayUserId": r.display_user_id, "name": f"{r.first_name} {r.last_name}",
             "total": r.total, "due": r.due_count or 0, "completed": r.completed_count or 0}
            for r in per_user_fu
        ],
    }

    # ── Prescription / Risk Distribution ──
    plan_rows = results["plan_rows"].all()
    plan_distribution = [{"planType": r.plan_type, "count": r.cnt} for r in plan_rows]

    glycemic_rows_r = results["glycemic_rows"].all()
    glycemic_dist = [{"category": r.glycemic or "unknown", "count": r.cnt} for r in glycemic_rows_r]

    pa_rows_r = results["pa_rows"].all()
    pa_dist = [{"category": r.physical_activity or "unknown", "count": r.cnt} for r in pa_rows_r]

    sed_rows_r = results["sed_rows"].all()
    sed_dist = [{"category": r.sedentary or "unknown", "count": r.cnt} for r in sed_rows_r]

    overall_rows_r = results["overall_rows"].all()
    overall_risk_dist = [{"category": r.overall or "unknown", "count": r.cnt} for r in overall_rows_r]

    par_q_count = s("par_q")

    comp_rows = results["comp_rows"].scalars().all()
    complication_breakdown: dict[str, int] = {}
    for flags in comp_rows:
        if isinstance(flags, dict):
            for k, v in flags.items():
                if v:
                    complication_breakdown[k] = complication_breakdown.get(k, 0) + 1
    users_with_complications = len(comp_rows)

    bmi_rows_r = results["bmi_rows"].all()
    bmi_dist = [{"category": r.bmi_category or "unknown", "count": r.cnt} for r in bmi_rows_r]

    prescription_risk = {
        "planDistribution": plan_distribution,
        "glycemicRisk": glycemic_dist,
        "physicalActivityRisk": pa_dist,
        "sedentaryRisk": sed_dist,
        "overallRisk": overall_risk_dist,
        "bmiDistribution": bmi_dist,
        "parQClearanceRequired": par_q_count,
        "complicationFlags": {"totalUsersWithFlags": users_with_complications, "breakdown": complication_breakdown},
    }

    # ── Activity & Adherence ──
    avg_minutes = results["avg_minutes"].scalar() or 0
    avg_days = results["avg_days"].scalar() or 0

    total_strength_logs = s("total_strength")
    strength_completed = s("strength_completed")
    strength_rate = round(
        (strength_completed / total_strength_logs * 100), 1
    ) if total_strength_logs > 0 else 0.0

    # Exercise adherence from streak_rows
    streak_rows_all = results["streak_rows"].all()
    total_weeks = len(streak_rows_all)
    adherent_weeks = sum(1 for row in streak_rows_all if row[0].exercise_adherent)
    adherence_rate = round(
        (adherent_weeks / total_weeks * 100), 1
    ) if total_weeks > 0 else 0.0

    pres_rows = results["pres_snapshots"].all()
    total_prescribed = 0
    pres_count = 0
    PLAN_WEEKLY_DEFAULTS = {
        "plan_a_start_slowly": 75,
        "plan_b_fitt": 150,
        "medical_clearance_required": 0,
        "light_activity_only": 60,
    }
    for row in pres_rows:
        plan_type = row.plan_type
        snap = row.prescription_snapshot
        mins = 0
        if isinstance(snap, dict):
            mins = snap.get("weekly_activity_minutes") or snap.get("prescribed_minutes_per_week") or 0
        if not mins:
            mins = PLAN_WEEKLY_DEFAULTS.get(plan_type, 0)
        try:
            total_prescribed += int(mins)
            pres_count += 1
        except (ValueError, TypeError):
            pass
    avg_prescribed_minutes = round(total_prescribed / pres_count, 1) if pres_count > 0 else 0

    activity_metrics = {
        "avgMinutesCompleted": round(float(avg_minutes), 1),
        "avgDaysCompleted": round(float(avg_days), 1),
        "strengthAdherence": {"totalLogs": total_strength_logs, "completedSessions": strength_completed, "rate": strength_rate},
        "exerciseAdherenceRate": adherence_rate,
        "avgPrescribedMinutesPerWeek": avg_prescribed_minutes,
        "avgCompletedVsPrescribed": {
            "prescribedMinutes": avg_prescribed_minutes,
            "completedMinutes": round(float(avg_minutes), 1),
        },
    }

    # ── Sugar Readings ──
    sugar_metrics = {
        "totalEntries": s("total_sugar"),
        "fastingCount": s("fasting"),
        "postMealCount": s("post_meal"),
        "hba1cCount": s("hba1c"),
        "usersWithRecentHba1c": s("hba1c_users"),
    }

    # Sugar distributions by value range
    fasting_ranges_row = results["fasting_ranges"].one_or_none()
    postmeal_ranges_row = results["postmeal_ranges"].one_or_none()

    sugar_distributions = {
        "fasting": {
            "below100": getattr(fasting_ranges_row, "range_below_100", 0) or 0,
            "range100_125": getattr(fasting_ranges_row, "range_100_125", 0) or 0,
            "above126": getattr(fasting_ranges_row, "range_126_plus", 0) or 0,
        },
        "postMeal": {
            "below140": getattr(postmeal_ranges_row, "range_below_140", 0) or 0,
            "range140_199": getattr(postmeal_ranges_row, "range_140_199", 0) or 0,
            "above200": getattr(postmeal_ranges_row, "range_200_plus", 0) or 0,
        },
    }

    # ── Notifications ──
    total_users_with_reminders = s("reminder_users")
    reminder_opt_in_rate = round(
        (total_users_with_reminders / total_users * 100), 1
    ) if total_users > 0 else 0.0

    notification_metrics = {
        "reminderOptInRate": reminder_opt_in_rate,
        "totalUsersWithReminders": total_users_with_reminders,
        "pushSent": s("push_sent"),
        "pushDelivered": s("push_delivered"),
        "pushOpened": s("push_opened"),
        "pushActionCompleted": s("push_action"),
    }

    # ── Safety ──
    safety_metrics = {
        "activitySafetyFlags": s("act_safety"),
        "followUpSafetyFlags": s("fu_safety"),
        "escalationAdviceCount": s("escalation"),
    }

    # ── Weekly exercise adherence breakdown ──
    weekly_adherence_breakdown = sorted([
        {
            "weekStart": str(row[0].week_start_date),
            "userId": row[0].user_id,
            "displayUserId": row[1],
            "name": f"{row[2]} {row[3]}",
            "exerciseAdherent": row[0].exercise_adherent,
            "loginStreakWeeks": row[0].login_streak_weeks,
            "adherenceStreakWeeks": row[0].adherence_streak_weeks,
        }
        for row in streak_rows_all
    ], key=lambda x: x["weekStart"], reverse=True)[:500]

    payload = {
        "userOverview": user_overview,
        "assessments": assessments_metrics,
        "followUps": follow_up_metrics,
        "prescriptions": prescription_risk,
        "activity": activity_metrics,
        "sugarReadings": sugar_metrics,
        "sugarDistributions": sugar_distributions,
        "notifications": notification_metrics,
        "safety": safety_metrics,
        "weeklyAdherence": weekly_adherence_breakdown,
    }

    _set_cached(ckey, payload)
    return payload


# ── Health endpoint ──
@router.get("/health")
async def admin_health(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    start = time.time()
    health_info = {
        "status": "ok",
        "timestamp": ist_now().isoformat(),
        "responseTimeMs": 0,
        "db": "unknown",
        "uptime": None,
        "cacheEntries": len(_metrics_cache),
    }
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
    admin: AdminUser = Depends(get_current_admin)
):
    users_count_stmt = select(func.count(User.id))
    users_count_res = await db.execute(users_count_stmt)
    total_users = users_count_res.scalar() or 0

    sessions_count_stmt = select(func.count(AssessmentSession.id))
    sessions_count_res = await db.execute(sessions_count_stmt)
    total_assessments = sessions_count_res.scalar() or 0

    active_users_stmt = select(func.count(func.distinct(AppSession.user_id)))
    active_users_res = await db.execute(active_users_stmt)
    active_users = active_users_res.scalar() or 0

    completed_assessments_stmt = select(func.count(AssessmentSession.id)).where(AssessmentSession.status == "completed")
    completed_assessments_res = await db.execute(completed_assessments_stmt)
    completed_assessments = completed_assessments_res.scalar() or 0

    completion_rate = round((completed_assessments / total_assessments * 100), 2) if total_assessments > 0 else 0.0

    avg_mins_stmt = select(func.avg(ActivityLog.completed_minutes))
    avg_mins_res = await db.execute(avg_mins_stmt)
    avg_mins = float(avg_mins_res.scalar() or 0.0)

    safety_flags_stmt = select(func.count(ActivityLog.id)).where(ActivityLog.safety_flag == True)
    safety_flags_res = await db.execute(safety_flags_stmt)
    safety_flags = safety_flags_res.scalar() or 0

    return {
        "totalUsers": total_users,
        "activeUsers": active_users,
        "totalAssessments": total_assessments,
        "completedAssessments": completed_assessments,
        "completionRate": completion_rate,
        "averageActivityMinutes": round(avg_mins, 2),
        "safetyFlagsTriggered": safety_flags
    }


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
            User.display_user_id.ilike(pattern),
            User.first_name.ilike(pattern),
            User.last_name.ilike(pattern),
        )

    total_stmt = select(func.count(User.id)).where(search_filter)
    total = (await db.execute(total_stmt)).scalar() or 0

    assess_count_subq = (
        select(func.count(AssessmentSession.id))
        .where(AssessmentSession.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    latest_plan_subq = (
        select(Prescription.plan_type)
        .where(Prescription.user_id == User.id)
        .order_by(Prescription.created_at.desc())
        .limit(1)
        .correlate(User)
        .scalar_subquery()
    )

    follow_due_subq = (
        select(func.count(FollowUpSession.id))
        .where(FollowUpSession.user_id == User.id, FollowUpSession.status == "due")
        .correlate(User)
        .scalar_subquery()
    )

    stmt = (
        select(
            User,
            assess_count_subq.label("assessments_count"),
            latest_plan_subq.label("current_plan"),
            follow_due_subq.label("follow_ups_due"),
        )
        .where(search_filter)
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    user_list = [
        {
            "id": r.User.id,
            "displayUserId": r.User.display_user_id,
            "firstName": r.User.first_name,
            "lastName": r.User.last_name,
            "preferredLanguage": r.User.preferred_language,
            "role": r.User.role,
            "createdAt": r.User.created_at,
            "assessmentsCount": r.assessments_count or 0,
            "currentPlan": r.current_plan or "none",
            "followUpsDue": r.follow_ups_due or 0,
        }
        for r in rows
    ]

    return {
        "users": user_list,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": -(total // -limit),
    }


@router.get("/users/{user_id}/detail")
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    sessions_stmt = select(AssessmentSession).where(AssessmentSession.user_id == user_id).order_by(AssessmentSession.started_at.desc())
    sessions_res = await db.execute(sessions_stmt)
    sessions = sessions_res.scalars().all()

    pres_stmt = select(Prescription).where(Prescription.user_id == user_id).order_by(Prescription.created_at.desc())
    pres_res = await db.execute(pres_stmt)
    prescriptions = pres_res.scalars().all()

    sugar_stmt = select(SugarReading).where(SugarReading.user_id == user_id).order_by(SugarReading.recorded_at.desc())
    sugar_res = await db.execute(sugar_stmt)
    sugar_readings = sugar_res.scalars().all()

    activity_stmt = select(ActivityLog).where(ActivityLog.user_id == user_id).order_by(ActivityLog.activity_date.desc())
    activity_res = await db.execute(activity_stmt)
    activity_logs = activity_res.scalars().all()

    return {
        "user": {
            "id": user.id,
            "displayUserId": user.display_user_id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "preferredLanguage": user.preferred_language,
            "role": user.role,
            "createdAt": user.created_at
        },
        "assessments": [{
            "id": s.id,
            "status": s.status,
            "startedAt": s.started_at,
            "completedAt": s.completed_at
        } for s in sessions],
        "prescriptions": [{
            "id": p.id,
            "planType": p.plan_type,
            "createdAt": p.created_at
        } for p in prescriptions],
        "sugarReadings": [{
            "id": r.id,
            "readingType": r.reading_type,
            "value": r.value,
            "recordedAt": r.recorded_at
        } for r in sugar_readings],
        "activityLogs": [{
            "id": l.id,
            "activityDate": l.activity_date,
            "completedMinutes": l.completed_minutes,
            "strengthCompleted": l.strength_completed,
            "safetyFlag": l.safety_flag
        } for l in activity_logs]
    }


class AudioGenerateRequest(BaseModel):
    questionnaire_id: Optional[str] = None
    language: Optional[str] = None
    force_regen: bool = False


@router.post("/audio-assets/generate")
async def admin_generate_audio(
    body: AudioGenerateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    from services.audio_generation import load_questionnaires, run_generation
    all_qs = load_questionnaires()
    if not all_qs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questionnaire data files found")
    summary = await run_generation(db, body.questionnaire_id, body.language, body.force_regen)
    if "error" in summary:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=summary["error"])
    return summary


@router.get("/audio-assets/missing")
async def admin_missing_audio(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    from services.audio_generation import load_questionnaires, resolve_prompt, content_hash, LANGUAGES
    all_qs = load_questionnaires()
    if not all_qs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No questionnaire data files found")

    stmt = select(AudioAsset)
    result = await db.execute(stmt)
    existing_assets = result.scalars().all()

    existing_set = set()
    for a in existing_assets:
        existing_set.add((a.questionnaire_id, a.question_id, a.language, a.content_hash))

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
                        missing.append({
                            "questionnaireId": q_id,
                            "questionnaireVersion": q_version,
                            "questionId": qq_id,
                            "language": lang_key,
                        })
    return {"missing": missing, "total": len(missing)}


class BroadcastRequest(BaseModel):
    type: str


BROADCAST_TITLES = {
    "follow_up": "Weekly Check-In",
    "exercise_reminder": "Time to Exercise!",
    "sugar_test": "Time to Check Your Sugar",
}

BROADCAST_BODIES = {
    "follow_up": "How are you feeling this week? Take 2 minutes to check in.",
    "exercise_reminder": "Don't forget your planned activity today.",
    "sugar_test": "Please record your latest blood sugar or HbA1c reading.",
}

BROADCAST_URLS = {
    "follow_up": "/follow-up",
    "exercise_reminder": "/home",
    "sugar_test": "/sugar",
}


@router.post("/backup/trigger")
async def trigger_backup(
    admin: AdminUser = Depends(get_current_admin),
):
    import threading
    threading.Thread(target=_run_backup_manual, daemon=True).start()
    return {"message": "Backup started in background"}


def _run_backup_manual():
    from services.backup_service import do_backup
    do_backup(triggered_by="manual")


@router.post("/notifications/broadcast")
async def broadcast_notification(
    body: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    if body.type not in BROADCAST_TITLES:
        raise HTTPException(status_code=400, detail=f"Invalid type. Choose from: {', '.join(BROADCAST_TITLES.keys())}")

    from services.push_notification_service import send_push_to_user

    user_ids_stmt = select(func.distinct(NotificationSubscription.user_id))
    user_ids_res = await db.execute(user_ids_stmt)
    user_ids = [row[0] for row in user_ids_res.all()]

    sent_count = 0
    failed_count = 0

    for uid in user_ids:
        try:
            await send_push_to_user(
                user_id=uid,
                notif_type=body.type,
                title=BROADCAST_TITLES[body.type],
                body=BROADCAST_BODIES[body.type],
                url=BROADCAST_URLS[body.type],
                db=db,
            )
            sent_count += 1
        except Exception as e:
            logger.warning("Broadcast failed for user %s: %s", uid, e)
            failed_count += 1

    return {
        "type": body.type,
        "totalUsersWithSubscriptions": len(user_ids),
        "sent": sent_count,
        "failed": failed_count,
    }


@router.post("/temporary-audio/cleanup")
async def cleanup_temporary_audio(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    now = ist_now()
    stmt = select(TemporaryAudio).where(TemporaryAudio.expires_at < now)
    result = await db.execute(stmt)
    expired = result.scalars().all()

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
