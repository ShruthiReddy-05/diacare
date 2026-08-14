from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List

from database import get_db
from models.checkin import CheckInSession, CheckInSchedule
from models.baseline_profile import BaselineProfile
from models.safety_event import SafetyEvent
from schemas.checkin import (
    CheckInSessionComplete, CheckInSessionResponse, NextCheckInResponse, CheckInScheduleResponse,
)
from services import checkin_engine, safety_engine
from services.adherence_tracker import update_weekly_domain_metric, get_latest_metric
from services.checkin_scheduler import create_checkin_schedule
from utils import ist_now

router = APIRouter(prefix="/api/checkin", tags=["Check-In"])


@router.get("/user/{user_id}/next", response_model=NextCheckInResponse)
async def get_next_checkin(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CheckInSession).where(
        CheckInSession.user_id == user_id, CheckInSession.status.in_(["due", "missed"]),
    ).order_by(CheckInSession.due_date.asc()).limit(1)
    session = (await db.execute(stmt)).scalar()
    if session:
        return NextCheckInResponse(status=session.status, session=session)
    return NextCheckInResponse(status="none", session=None)


@router.post("/sessions/{session_id}/complete", response_model=CheckInSessionResponse)
async def complete_checkin(session_id: str, body: CheckInSessionComplete, db: AsyncSession = Depends(get_db)):
    session = (await db.execute(select(CheckInSession).where(CheckInSession.id == session_id))).scalar()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in session not found.")

    baseline = (await db.execute(select(BaselineProfile).where(BaselineProfile.user_id == session.user_id))).scalar()
    neuropathy_flag = bool((baseline.complication_profile or {}).get("neuropathy")) if baseline else False

    prev_metric = await get_latest_metric(session.user_id, db)
    prev_poor_weeks = prev_metric.consecutive_poor_weeks if prev_metric else 0

    answers = body.model_dump()
    evaluation = checkin_engine.evaluate_checkin(answers, neuropathy_flag=neuropathy_flag, previous_consecutive_poor_weeks=prev_poor_weeks)

    # Module D: new foot problem and out-of-range sugar route straight to safety, before any coaching content.
    safety_answers = {
        "sugarReading": body.q8_sugar_reading,
        "footBlackening": body.q5_new_foot_problem,
    }
    triggered = safety_engine.check_safety(safety_answers)
    escalate = evaluation["new_foot_problem_routes_to_safety"] or bool(triggered) or body.q8b_hypo_episode

    for code in (triggered or (["new_foot_problem"] if evaluation["new_foot_problem_routes_to_safety"] else [])):
        db.add(SafetyEvent(user_id=session.user_id, session_id=session_id, source_module="C", trigger_code=code))

    session.q1_activity_days = body.q1_activity_days
    session.q2_food_goal_days = body.q2_food_goal_days
    session.q3_medication_days = body.q3_medication_days
    session.q4_foot_care_days = body.q4_foot_care_days
    session.q5_new_foot_problem = body.q5_new_foot_problem
    session.q6_stress_0_10 = body.q6_stress_0_10
    session.q7_sleep_0_10 = body.q7_sleep_0_10
    session.q8_sugar_reading = body.q8_sugar_reading
    session.q8b_hypo_episode = body.q8b_hypo_episode
    session.triggered_content = evaluation["triggered_content"]
    session.safety_flag = escalate
    session.escalation_advice_given = escalate
    session.status = "escalated" if escalate else "completed"
    session.completed_at = ist_now()

    await db.commit()
    await update_weekly_domain_metric(session.user_id, session.program_week, evaluation, db)
    await db.refresh(session)
    return session


@router.get("/user/{user_id}/sessions", response_model=List[CheckInSessionResponse])
async def get_user_checkin_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(CheckInSession).where(CheckInSession.user_id == user_id).order_by(desc(CheckInSession.due_date))
    return (await db.execute(stmt)).scalars().all()


@router.get("/user/{user_id}/schedule", response_model=CheckInScheduleResponse)
async def get_user_schedule(user_id: str, db: AsyncSession = Depends(get_db)):
    schedule = (await db.execute(select(CheckInSchedule).where(CheckInSchedule.user_id == user_id))).scalar()
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No check-in schedule found.")
    return schedule


@router.post("/user/{user_id}/schedule", response_model=CheckInScheduleResponse)
async def create_user_schedule(user_id: str, preferred_time: str = "evening", db: AsyncSession = Depends(get_db)):
    await create_checkin_schedule(user_id, preferred_time, db)
    schedule = (await db.execute(select(CheckInSchedule).where(CheckInSchedule.user_id == user_id))).scalar()
    return schedule
