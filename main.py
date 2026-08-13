import logging
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import event, create_engine, text
from sqlalchemy.orm import Session

from database import engine, Base
from config import settings
from utils import ist_now
import models

from routers import users, assessments, prescriptions, sugar_and_activity, audio, admin, follow_ups, notifications, reminders, scheduler, adherence, speech
from routers.prescriptions import temp_audio_router

logger = logging.getLogger(__name__)
BACKUP_INTERVAL_SECS = 21600  # 6 hours


def _check_and_run_backup():
    if settings.DATABASE_URL.startswith("sqlite"):
        return

    sync_url = _to_sync_url(settings.DATABASE_URL)
    sync_engine = create_engine(sync_url)
    try:
        with sync_engine.connect() as conn:
            row = conn.execute(
                text("SELECT last_backup_at FROM backup_log ORDER BY last_backup_at DESC LIMIT 1")
            ).first()
            now = ist_now()
            if row and (now - row[0]).total_seconds() < BACKUP_INTERVAL_SECS:
                return

        threading.Thread(target=_run_backup_in_thread, daemon=True).start()
    finally:
        sync_engine.dispose()


def _run_backup_in_thread():
    from services.backup_service import do_backup
    do_backup(triggered_by="auto")


def _to_sync_url(async_url):
    if "+" in async_url and "://" in async_url:
        scheme, rest = async_url.split("://", 1)
        if "+" in scheme:
            return scheme.split("+")[0] + "://" + rest
    return async_url


@event.listens_for(Session, "after_commit")
def trigger_backup(session):
    _check_and_run_backup()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup on shutdown if needed
    pass

app = FastAPI(
    title="DiaFit API",
    description="Backend API for DiaFit PWA - Diabetes Physical Activity Coaching",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router)
app.include_router(assessments.router)
app.include_router(prescriptions.router)
app.include_router(sugar_and_activity.router)
app.include_router(audio.router)
app.include_router(admin.router)
app.include_router(follow_ups.router)
app.include_router(notifications.router)
app.include_router(reminders.router)
app.include_router(scheduler.router)
app.include_router(adherence.router)
app.include_router(speech.router)
app.include_router(temp_audio_router)

@app.get("/")
async def root():
    return {
        "app": "DiaFit API",
        "version": "2.0.0",
        "status": "healthy"
    }
