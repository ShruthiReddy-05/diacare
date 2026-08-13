from datetime import timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from models.follow_up import WeeklyUserMetric
from models.prescription import Prescription, AiPrescriptionOutput
from models.user import User

MIN_ADHERENT_STREAK_FOR_PROGRESSION = 2

async def check_and_progress_plan_a(db: AsyncSession):
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    user_stmt = select(User.id)
    user_result = await db.execute(user_stmt)
    user_ids = [row[0] for row in user_result.all()]

    for uid in user_ids:
        pres_stmt = select(Prescription).where(
            Prescription.user_id == uid,
        ).order_by(desc(Prescription.created_at)).limit(1)
        pres_result = await db.execute(pres_stmt)
        latest_pres = pres_result.scalar()

        if not latest_pres or latest_pres.plan_type != "plan_a_start_slowly":
            continue

        metric_stmt = select(WeeklyUserMetric).where(
            WeeklyUserMetric.user_id == uid,
        ).order_by(desc(WeeklyUserMetric.week_start_date)).limit(1)
        metric_result = await db.execute(metric_stmt)
        latest_metric = metric_result.scalar()

        if not latest_metric or latest_metric.adherence_streak_weeks < MIN_ADHERENT_STREAK_FOR_PROGRESSION:
            continue

        # TODO: In future, trigger AI prescription generation with progression prompt
        # For now, mark that progression is due
        latest_pres.needs_progression = True

    await db.commit()
