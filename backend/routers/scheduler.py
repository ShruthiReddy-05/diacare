from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.checkin_scheduler import daily_tick

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])

@router.post("/daily-tick")
async def run_daily_tick(db: AsyncSession = Depends(get_db)):
    await daily_tick(db)
    return {"status": "ok"}
