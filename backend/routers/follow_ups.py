from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List

from database import get_db
from models.user import User
from models.follow_up import FollowUpSession, FollowUpSchedule
from schemas.follow_up import (
    FollowUpSessionComplete, FollowUpSessionResponse,
    NextFollowUpResponse, FollowUpScheduleResponse,
)
from utils import ist_now
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/follow-ups", tags=["Follow-Ups"])

@router.get("/user/{user_id}/next", response_model=NextFollowUpResponse)
async def get_next_follow_up(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FollowUpSession).where(
        FollowUpSession.user_id == user_id,
        FollowUpSession.status.in_(["due", "overdue"]),
    ).order_by(FollowUpSession.due_date.asc()).limit(1)
    result = await db.execute(stmt)
    session = result.scalar()

    if session:
        return NextFollowUpResponse(status=session.status, session=session)
    return NextFollowUpResponse(status="none", session=None)

@router.post("/sessions/{session_id}/complete", response_model=FollowUpSessionResponse)
async def complete_follow_up(
    session_id: str,
    body: FollowUpSessionComplete,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FollowUpSession).where(FollowUpSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar()

    if not session:
        raise HTTPException(status_code=404, detail="Follow-up session not found.")

    now = ist_now()

    session.q1_walked = body.q1_walked
    session.q2_difficulty = body.q2_difficulty
    session.q3_chest_pain_dizziness = body.q3_chest_pain_dizziness
    session.q4_foot_wounds = body.q4_foot_wounds

    if body.q3_chest_pain_dizziness or body.q4_foot_wounds:
        session.safety_flag = True
        session.escalation_advice_given = True
        session.status = "escalated"
    else:
        session.status = "completed"

    session.completed_at = now

    if session.schedule_id:
        sched_stmt = select(FollowUpSchedule).where(FollowUpSchedule.id == session.schedule_id)
        sched_result = await db.execute(sched_stmt)
        schedule = sched_result.scalar()
        if schedule:
            schedule.last_follow_up_at = now
            next_friday = now + timedelta(days=(4 - now.weekday()) % 7 or 7)
            schedule.next_due_at = datetime(next_friday.year, next_friday.month, next_friday.day, 5, 0)

    await db.commit()
    await db.refresh(session)
    return session

@router.get("/user/{user_id}/sessions", response_model=List[FollowUpSessionResponse])
async def get_user_follow_up_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FollowUpSession).where(
        FollowUpSession.user_id == user_id
    ).order_by(desc(FollowUpSession.due_date))
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/user/{user_id}/schedule", response_model=FollowUpScheduleResponse)
async def get_user_schedule(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(FollowUpSchedule).where(FollowUpSchedule.user_id == user_id)
    result = await db.execute(stmt)
    schedule = result.scalar()
    if not schedule:
        raise HTTPException(status_code=404, detail="No schedule found. Register for follow-ups first.")
    return schedule

@router.post("/user/{user_id}/schedule", response_model=FollowUpScheduleResponse)
async def create_user_schedule(user_id: str, db: AsyncSession = Depends(get_db)):
    from services.follow_up_scheduler import create_default_schedule
    await create_default_schedule(user_id, db)
    stmt = select(FollowUpSchedule).where(FollowUpSchedule.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar()
