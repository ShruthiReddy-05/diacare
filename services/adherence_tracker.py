from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from models.sugar_and_activity import ActivityLog
from models.follow_up import WeeklyUserMetric
from models.user import User, AppSession
from utils import ist_now

MIN_ADHERENT_MINUTES = 30
MIN_ADHERENT_DAYS = 3

async def compute_weekly_adherence(user_id: str, week_start: date, db: AsyncSession) -> bool:
    week_end = week_start + timedelta(days=6)
    stmt = select(
        func.coalesce(func.sum(ActivityLog.completed_minutes), 0),
        func.coalesce(func.sum(ActivityLog.completed_days), 0),
    ).where(
        ActivityLog.user_id == user_id,
        ActivityLog.activity_date >= week_start,
        ActivityLog.activity_date <= week_end,
    )
    result = await db.execute(stmt)
    row = result.one()
    total_minutes = row[0] or 0
    total_days = row[1] or 0
    return total_minutes >= MIN_ADHERENT_MINUTES and total_days >= MIN_ADHERENT_DAYS

async def was_user_active_week(user_id: str, week_start: date, db: AsyncSession) -> bool:
    week_end = week_start + timedelta(days=6)
    stmt = select(func.count(AppSession.id)).where(
        AppSession.user_id == user_id,
        AppSession.started_at >= datetime(week_start.year, week_start.month, week_start.day),
        AppSession.started_at < datetime(week_end.year, week_end.month, week_end.day) + timedelta(days=1),
    )
    result = await db.execute(stmt)
    return result.scalar() > 0

async def update_weekly_metrics(user_id: str, week_start: date, adherent: bool, was_active: bool, db: AsyncSession):
    now = ist_now()
    stmt = select(WeeklyUserMetric).where(
        WeeklyUserMetric.user_id == user_id,
        WeeklyUserMetric.week_start_date == week_start,
    )
    result = await db.execute(stmt)
    metric = result.scalar()

    if not metric:
        prev_week = week_start - timedelta(days=7)
        prev_stmt = select(WeeklyUserMetric).where(
            WeeklyUserMetric.user_id == user_id,
            WeeklyUserMetric.week_start_date == prev_week,
        )
        prev_result = await db.execute(prev_stmt)
        prev_metric = prev_result.scalar()
        prev_adherence_streak = prev_metric.adherence_streak_weeks if prev_metric else 0
        prev_login_streak = prev_metric.login_streak_weeks if prev_metric else 0

        metric = WeeklyUserMetric(
            user_id=user_id,
            week_start_date=week_start,
            exercise_adherent=adherent,
            adherence_streak_weeks=(prev_adherence_streak + 1) if adherent else 0,
            login_streak_weeks=(prev_login_streak + 1) if was_active else 0,
            updated_at=now,
        )
        db.add(metric)
    else:
        prev_week = week_start - timedelta(days=7)
        prev_result = await db.execute(
            select(WeeklyUserMetric).where(
                WeeklyUserMetric.user_id == user_id,
                WeeklyUserMetric.week_start_date == prev_week,
            )
        )
        prev_metric = prev_result.scalar()
        prev_adherence_streak = prev_metric.adherence_streak_weeks if prev_metric else 0
        prev_login_streak = prev_metric.login_streak_weeks if prev_metric else 0

        metric.exercise_adherent = adherent
        metric.adherence_streak_weeks = (prev_adherence_streak + 1) if adherent else 0
        metric.login_streak_weeks = (prev_login_streak + 1) if was_active else 0
        metric.updated_at = now

    await db.commit()
    return metric

async def run_weekly_adherence_check(db: AsyncSession):
    now = ist_now()
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    week_start = monday - timedelta(days=7)

    user_stmt = select(User.id)
    user_result = await db.execute(user_stmt)
    user_ids = [row[0] for row in user_result.all()]

    for uid in user_ids:
        adherent = await compute_weekly_adherence(uid, week_start, db)
        was_active = await was_user_active_week(uid, week_start, db)
        await update_weekly_metrics(uid, week_start, adherent, was_active, db)
