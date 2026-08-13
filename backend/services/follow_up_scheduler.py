import logging
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from models.user import User
from models.follow_up import FollowUpSchedule, FollowUpSession, Reminder, NotificationEvent
from services.push_notification_service import send_push_to_user
from services.adherence_tracker import run_weekly_adherence_check
from services.progression_service import check_and_progress_plan_a
from utils import ist_now

logger = logging.getLogger(__name__)

CRON_HOUR = 5

def _next_friday_at_cron_hour(today: date) -> datetime:
    days_until = (4 - today.weekday()) % 7
    if days_until == 0:
        days_until = 7
    next_friday = today + timedelta(days=days_until)
    return datetime(next_friday.year, next_friday.month, next_friday.day, CRON_HOUR, 0)

async def create_default_schedule(user_id: str, db: AsyncSession):
    now = ist_now()
    today = now.date()
    days_until_friday = (4 - today.weekday()) % 7
    next_friday = today + timedelta(days=days_until_friday or 7)

    existing = await db.execute(
        select(FollowUpSchedule).where(FollowUpSchedule.user_id == user_id)
    )
    if existing.scalar():
        return

    schedule = FollowUpSchedule(
        user_id=user_id,
        schedule_type="weekly",
        day_of_week=4,
        next_due_at=datetime(next_friday.year, next_friday.month, next_friday.day, CRON_HOUR, 0),
        is_active=True,
    )
    db.add(schedule)
    await db.commit()

async def check_due_follow_ups(db: AsyncSession):
    now = ist_now()
    today = now.date()
    stmt = select(FollowUpSchedule).where(
        FollowUpSchedule.is_active == True,
        FollowUpSchedule.next_due_at <= now,
    )
    result = await db.execute(stmt)
    schedules = result.scalars().all()

    for schedule in schedules:
        try:
            existing = await db.execute(
                select(FollowUpSession).where(
                    FollowUpSession.user_id == schedule.user_id,
                    FollowUpSession.due_date == schedule.next_due_at.date(),
                    FollowUpSession.status == "due",
                )
            )
            existing_session = existing.scalar()

            advance = False

            if existing_session:
                if existing_session.due_date >= today:
                    continue
                existing_session.status = "missed"
                advance = True
            elif schedule.next_due_at.date() < today:
                missed = FollowUpSession(
                    user_id=schedule.user_id,
                    schedule_id=schedule.id,
                    due_date=schedule.next_due_at.date(),
                    status="missed",
                )
                db.add(missed)
                advance = True

            if advance:
                schedule.next_due_at = _next_friday_at_cron_hour(today)
                await db.commit()

            session = FollowUpSession(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                due_date=schedule.next_due_at.date(),
                status="due",
            )
            db.add(session)
            await db.commit()

            await send_push_to_user(
                user_id=schedule.user_id,
                notif_type="follow_up",
                title="Weekly Check-In",
                body="How are you feeling this week? Take 2 minutes to check in.",
                url="/follow-up",
                db=db,
            )
            logger.info("Follow-up notification sent to user %s", schedule.user_id)
        except Exception as e:
            logger.error("Failed to process follow-up for user %s: %s", schedule.user_id, e)

async def check_due_reminders(db: AsyncSession):
    now = ist_now()
    today = now.date()
    day_of_week = today.weekday()

    stmt = select(Reminder).where(Reminder.is_enabled == True)
    result = await db.execute(stmt)
    reminders = result.scalars().all()

    for reminder in reminders:
        try:
            already_sent = await db.execute(
                select(NotificationEvent).where(
                    NotificationEvent.user_id == reminder.user_id,
                    NotificationEvent.type == reminder.type,
                    NotificationEvent.created_at >= today,
                ).limit(1)
            )

            if already_sent.scalar():
                continue

            if reminder.type == "sugar_test":
                if today.day == 1:
                    await send_push_to_user(
                        user_id=reminder.user_id,
                        notif_type="sugar_test_reminder",
                        title="Time to Check Your Sugar",
                        body="Please record your latest blood sugar or HbA1c reading.",
                        url="/sugar",
                        db=db,
                    )
                    logger.info("Sugar test reminder sent to user %s", reminder.user_id)
            elif reminder.type in ("exercise", "walk_break", "strength_day"):
                if reminder.days_of_week and day_of_week in reminder.days_of_week:
                    await send_push_to_user(
                        user_id=reminder.user_id,
                        notif_type=reminder.type,
                        title="Time to Exercise!",
                        body="Don't forget your planned activity today.",
                        url="/home",
                        db=db,
                    )
                    logger.info("%s reminder sent to user %s", reminder.type, reminder.user_id)
        except Exception as e:
            logger.error("Failed to process reminder %s for user %s: %s", reminder.id, reminder.user_id, e)

async def daily_tick(db: AsyncSession):
    logger.info("Daily tick started at %s", ist_now().isoformat())

    await check_due_follow_ups(db)

    today = ist_now().date()
    if today.weekday() == 6:
        try:
            await run_weekly_adherence_check(db)
            logger.info("Weekly adherence check completed")
        except Exception as e:
            logger.error("Weekly adherence check failed: %s", e)
        try:
            await check_and_progress_plan_a(db)
            logger.info("Plan A progression check completed")
        except Exception as e:
            logger.error("Plan A progression check failed: %s", e)

    await check_due_reminders(db)

    logger.info("Daily tick finished at %s", ist_now().isoformat())
