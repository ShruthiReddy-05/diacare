from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
from models.user import User
from models.sugar_and_activity import SugarReading, ActivityLog
from schemas.sugar_and_activity import (
    SugarReadingCreate, SugarReadingResponse,
    ActivityLogCreate, ActivityLogResponse
)

router = APIRouter(prefix="/api/tracking", tags=["Tracking"])

@router.post("/sugar", response_model=SugarReadingResponse, status_code=status.HTTP_201_CREATED)
async def add_sugar_reading(user_id: str, reading_in: SugarReadingCreate, db: AsyncSession = Depends(get_db)):
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    if not user_res.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
        
    db_reading = SugarReading(
        user_id=user_id,
        reading_type=reading_in.reading_type,
        value=reading_in.value,
        notes=reading_in.notes
    )
    if reading_in.recorded_at:
        db_reading.recorded_at = reading_in.recorded_at
        
    db.add(db_reading)
    await db.commit()
    await db.refresh(db_reading)
    return db_reading

@router.get("/sugar/user/{user_id}", response_model=List[SugarReadingResponse])
async def get_user_sugar_readings(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(SugarReading).where(SugarReading.user_id == user_id).order_by(SugarReading.recorded_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/activity", response_model=ActivityLogResponse, status_code=status.HTTP_201_CREATED)
async def log_activity(user_id: str, log_in: ActivityLogCreate, db: AsyncSession = Depends(get_db)):
    # Verify user exists
    user_stmt = select(User).where(User.id == user_id)
    user_res = await db.execute(user_stmt)
    if not user_res.scalar():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Check if a log already exists for this user + week
    existing_stmt = select(ActivityLog).where(
        ActivityLog.user_id == user_id,
        ActivityLog.activity_date == log_in.activity_date
    )
    existing_res = await db.execute(existing_stmt)
    db_log = existing_res.scalar()

    if db_log:
        db_log.completed_minutes = log_in.completed_minutes
        db_log.completed_days = log_in.completed_days
        db_log.strength_completed = log_in.strength_completed
        db_log.fatigue_rating = log_in.fatigue_rating
        db_log.difficulty_rating = log_in.difficulty_rating
        db_log.safety_flag = log_in.safety_flag
        db_log.notes = log_in.notes
    else:
        db_log = ActivityLog(
            user_id=user_id,
            activity_date=log_in.activity_date,
            completed_minutes=log_in.completed_minutes,
            completed_days=log_in.completed_days,
            strength_completed=log_in.strength_completed,
            fatigue_rating=log_in.fatigue_rating,
            difficulty_rating=log_in.difficulty_rating,
            safety_flag=log_in.safety_flag,
            notes=log_in.notes
        )
        db.add(db_log)

    await db.commit()
    await db.refresh(db_log)
    return db_log

@router.get("/activity/user/{user_id}", response_model=List[ActivityLogResponse])
async def get_user_activity_logs(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ActivityLog).where(ActivityLog.user_id == user_id).order_by(ActivityLog.activity_date.desc())
    result = await db.execute(stmt)
    return result.scalars().all()
