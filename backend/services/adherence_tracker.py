"""Per-domain streak tracking for the weekly check-in (module C), replacing
the old single-metric services/adherence_tracker.py. Streaks reset to 0 on
any regression -- no grace week -- mirroring the original design."""
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from models.checkin import WeeklyDomainMetric
from utils import ist_now


async def get_latest_metric(user_id: str, db: AsyncSession) -> Optional[WeeklyDomainMetric]:
    stmt = select(WeeklyDomainMetric).where(
        WeeklyDomainMetric.user_id == user_id
    ).order_by(desc(WeeklyDomainMetric.program_week)).limit(1)
    result = await db.execute(stmt)
    return result.scalar()


async def update_weekly_domain_metric(user_id: str, program_week: int, evaluation: Dict[str, Any],
                                        db: AsyncSession) -> WeeklyDomainMetric:
    prev = await get_latest_metric(user_id, db)
    prev_activity = prev.activity_streak_weeks if prev else 0
    prev_food = prev.food_goal_streak_weeks if prev else 0
    prev_medication = prev.medication_streak_weeks if prev else 0
    prev_foot = prev.foot_care_streak_weeks if prev else 0

    activity_ok = evaluation["activity_progression"] == "increase_duration"
    food_ok = evaluation["food_progression"] == "release_next_stored_goal"
    medication_ok = not evaluation["medication"]["rerun_m3_barrier_assessment"]
    foot_ok = not evaluation["foot_care"]["reinforce"]

    existing_stmt = select(WeeklyDomainMetric).where(
        WeeklyDomainMetric.user_id == user_id,
        WeeklyDomainMetric.program_week == program_week,
    )
    existing_result = await db.execute(existing_stmt)
    metric = existing_result.scalar()

    values = dict(
        activity_streak_weeks=(prev_activity + 1) if activity_ok else 0,
        food_goal_streak_weeks=(prev_food + 1) if food_ok else 0,
        medication_streak_weeks=(prev_medication + 1) if medication_ok else 0,
        foot_care_streak_weeks=(prev_foot + 1) if foot_ok else 0,
        week_is_poor=evaluation["week_is_poor"],
        consecutive_poor_weeks=evaluation["consecutive_poor_weeks"],
        reassessment_triggered=evaluation["reassessment_triggered"],
        updated_at=ist_now(),
    )

    if metric:
        for key, val in values.items():
            setattr(metric, key, val)
    else:
        metric = WeeklyDomainMetric(user_id=user_id, program_week=program_week, **values)
        db.add(metric)

    await db.commit()
    await db.refresh(metric)
    return metric
