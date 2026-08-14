"""Schedules the 12-week weekly check-in (module C) and daily medicine /
sugar-test reminders. Replaces services/follow_up_scheduler.py; adds the
program-week counter the old app never had."""
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.checkin import CheckInSchedule, CheckInSession
from models.notification import Reminder, NotificationEvent
from services.push_notification_service import send_push_to_user
from utils import ist_now

logger = logging.getLogger(__name__)

CRON_HOUR = 5


def _next_week_at_cron_hour(today: date) -> datetime:
    next_day = today + timedelta(days=7)
    return datetime(next_day.year, next_day.month, next_day.day, CRON_HOUR, 0)


def program_week_for_date(program_start_date: date, on_date: date) -> int:
    return max(1, ((on_date - program_start_date).days // 7) + 1)


async def create_checkin_schedule(user_id: str, preferred_time: str, db: AsyncSession):
    existing = await db.execute(select(CheckInSchedule).where(CheckInSchedule.user_id == user_id))
    if existing.scalar():
        return

    today = ist_now().date()
    schedule = CheckInSchedule(
        user_id=user_id,
        program_start_date=today,
        preferred_time=preferred_time,
        total_weeks=12,
        next_due_at=_next_week_at_cron_hour(today),
        is_active=True,
    )
    db.add(schedule)
    await db.commit()


async def check_due_checkins(db: AsyncSession):
    now = ist_now()
    today = now.date()
    stmt = select(CheckInSchedule).where(
        CheckInSchedule.is_active == True,
        CheckInSchedule.next_due_at <= now,
    )
    result = await db.execute(stmt)
    schedules = result.scalars().all()

    for schedule in schedules:
        try:
            program_week = program_week_for_date(schedule.program_start_date, schedule.next_due_at.date())

            if program_week > schedule.total_weeks:
                schedule.is_active = False
                await db.commit()
                continue

            existing = await db.execute(
                select(CheckInSession).where(
                    CheckInSession.user_id == schedule.user_id,
                    CheckInSession.due_date == schedule.next_due_at.date(),
                    CheckInSession.status == "due",
                )
            )
            existing_session = existing.scalar()

            if existing_session:
                if existing_session.due_date >= today:
                    continue
                existing_session.status = "missed"

            schedule.next_due_at = _next_week_at_cron_hour(today)
            await db.commit()

            next_program_week = program_week_for_date(schedule.program_start_date, schedule.next_due_at.date())
            if next_program_week > schedule.total_weeks:
                schedule.is_active = False
                await db.commit()
                continue

            session = CheckInSession(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                program_week=next_program_week,
                due_date=schedule.next_due_at.date(),
                status="due",
            )
            db.add(session)
            await db.commit()

            await send_push_to_user(
                user_id=schedule.user_id,
                notif_type="checkin",
                title="Weekly Check-In",
                body="Eight quick questions, about 5 minutes. Let's see how this week went.",
                url="/checkin",
                db=db,
            )
            logger.info("Check-in notification sent to user %s (week %s)", schedule.user_id, next_program_week)
        except Exception as e:
            logger.error("Failed to process check-in for user %s: %s", schedule.user_id, e)


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
                        user_id=reminder.user_id, notif_type="sugar_test_reminder",
                        title="Time to Check Your Sugar",
                        body="Please record your latest blood sugar or HbA1c reading.",
                        url="/sugar", db=db,
                    )
            elif reminder.type == "medication":
                await send_push_to_user(
                    user_id=reminder.user_id, notif_type="medication_reminder",
                    title=reminder.label or "Medicine Time",
                    body="Time for your medicine.",
                    url="/home", db=db,
                )
            elif reminder.type == "movement_break":
                if reminder.days_of_week and day_of_week in reminder.days_of_week:
                    await send_push_to_user(
                        user_id=reminder.user_id, notif_type="movement_break",
                        title="Time to Move",
                        body="Stand and move for 3 minutes.",
                        url="/home", db=db,
                    )
        except Exception as e:
            logger.error("Failed to process reminder %s for user %s: %s", reminder.id, reminder.user_id, e)


async def daily_tick(db: AsyncSession):
    logger.info("Daily tick started at %s", ist_now().isoformat())
    await check_due_checkins(db)
    await check_due_reminders(db)
    logger.info("Daily tick finished at %s", ist_now().isoformat())
