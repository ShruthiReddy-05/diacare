from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from database import get_db
from models.follow_up import WeeklyUserMetric
from schemas.follow_up import WeeklyMetricResponse
from services.adherence_tracker import compute_weekly_adherence, update_weekly_metrics
from utils import ist_now
from datetime import timedelta

router = APIRouter(prefix="/api/adherence", tags=["Adherence"])

@router.get("/user/{user_id}/current", response_model=WeeklyMetricResponse)
async def get_current_adherence(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WeeklyUserMetric).where(
        WeeklyUserMetric.user_id == user_id,
    ).order_by(desc(WeeklyUserMetric.week_start_date)).limit(1)
    result = await db.execute(stmt)
    metric = result.scalar()

    if not metric:
        today = ist_now().date()
        monday = today - timedelta(days=today.weekday())
        adherent = await compute_weekly_adherence(user_id, monday, db)
        metric = await update_weekly_metrics(user_id, monday, adherent, db)

    return metric

@router.get("/user/{user_id}/history", response_model=list[WeeklyMetricResponse])
async def get_adherence_history(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WeeklyUserMetric).where(
        WeeklyUserMetric.user_id == user_id,
    ).order_by(desc(WeeklyUserMetric.week_start_date)).limit(12)
    result = await db.execute(stmt)
    return result.scalars().all()
