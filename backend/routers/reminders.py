from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
from models.notification import Reminder
from schemas.notification import ReminderCreate, ReminderResponse

router = APIRouter(prefix="/api/reminders", tags=["Reminders"])

@router.get("/user/{user_id}", response_model=List[ReminderResponse])
async def get_reminders(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Reminder).where(Reminder.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/user/{user_id}/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    user_id: str,
    reminder_id: str,
    body: ReminderCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Reminder).where(
        Reminder.id == reminder_id,
        Reminder.user_id == user_id,
    )
    result = await db.execute(stmt)
    reminder = result.scalar()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found.")

    reminder.type = body.type
    reminder.label = body.label
    reminder.time_of_day = body.time_of_day
    reminder.days_of_week = body.days_of_week
    reminder.interval_days = body.interval_days
    reminder.is_enabled = body.is_enabled
    await db.commit()
    await db.refresh(reminder)
    return reminder

@router.post("/user/{user_id}", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    user_id: str,
    body: ReminderCreate,
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        user_id=user_id,
        type=body.type,
        label=body.label,
        time_of_day=body.time_of_day,
        days_of_week=body.days_of_week,
        interval_days=body.interval_days,
        is_enabled=body.is_enabled,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder
