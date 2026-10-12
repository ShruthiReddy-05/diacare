from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List

from database import get_db
from models.checkin import WeeklyDomainMetric
from schemas.checkin import WeeklyDomainMetricResponse
from services.safety_lock import require_no_open_safety_event

# Check-in progression (streaks, poor weeks, reassessment) -- locked by Module D.
router = APIRouter(prefix="/api/adherence", tags=["Adherence"], dependencies=[Depends(require_no_open_safety_event)])

@router.get("/user/{user_id}/current", response_model=WeeklyDomainMetricResponse)
async def get_current_adherence(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WeeklyDomainMetric).where(
        WeeklyDomainMetric.user_id == user_id,
    ).order_by(desc(WeeklyDomainMetric.program_week)).limit(1)
    result = await db.execute(stmt)
    metric = result.scalar()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No adherence data yet -- complete a weekly check-in first.")
    return metric

@router.get("/user/{user_id}/history", response_model=List[WeeklyDomainMetricResponse])
async def get_adherence_history(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(WeeklyDomainMetric).where(
        WeeklyDomainMetric.user_id == user_id,
    ).order_by(desc(WeeklyDomainMetric.program_week)).limit(12)
    result = await db.execute(stmt)
    return result.scalars().all()
