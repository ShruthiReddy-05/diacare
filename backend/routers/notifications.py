from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
from models.notification import NotificationSubscription, NotificationEvent
from schemas.notification import (
    NotificationSubscriptionCreate, NotificationSubscriptionResponse,
)
from config import settings
from utils import ist_now

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    return {"publicKey": settings.VAPID_PUBLIC_KEY}

@router.post("/subscribe", response_model=NotificationSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    user_id: str,
    body: NotificationSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(NotificationSubscription).where(
            NotificationSubscription.user_id == user_id,
            NotificationSubscription.endpoint == body.endpoint,
        )
    )
    if existing.scalar():
        sub = existing.scalar()
        sub.p256dh_key = body.p256dh_key
        sub.auth_key = body.auth_key
        await db.commit()
        await db.refresh(sub)
        return sub

    sub = NotificationSubscription(
        user_id=user_id,
        endpoint=body.endpoint,
        p256dh_key=body.p256dh_key,
        auth_key=body.auth_key,
        device_type=body.device_type,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub

@router.delete("/subscribe")
async def unsubscribe(
    user_id: str,
    endpoint: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.user_id == user_id,
        NotificationSubscription.endpoint == endpoint,
    )
    result = await db.execute(stmt)
    sub = result.scalar()
    if sub:
        await db.delete(sub)
        await db.commit()
    return {"status": "unsubscribed"}

@router.post("/events/{event_id}/delivered")
async def mark_event_delivered(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(NotificationEvent, event_id)
    if event and event.delivered_at is None:
        event.delivered_at = ist_now()
        await db.commit()
    return {"status": "ok"}

@router.post("/events/{event_id}/opened")
async def mark_event_opened(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(NotificationEvent, event_id)
    if event and event.opened_at is None:
        event.opened_at = ist_now()
        await db.commit()
    return {"status": "ok"}

@router.post("/events/{event_id}/action-completed")
async def mark_event_action_completed(event_id: str, db: AsyncSession = Depends(get_db)):
    event = await db.get(NotificationEvent, event_id)
    if event and event.action_completed_at is None:
        event.action_completed_at = ist_now()
        await db.commit()
    return {"status": "ok"}

@router.post("/events/mark-latest-action/{user_id}/{notif_type}")
async def mark_latest_action(user_id: str, notif_type: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(NotificationEvent)
        .where(
            NotificationEvent.user_id == user_id,
            NotificationEvent.type == notif_type,
            NotificationEvent.action_completed_at.is_(None),
        )
        .order_by(NotificationEvent.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    event = result.scalar()
    if event:
        event.action_completed_at = ist_now()
        await db.commit()
    return {"status": "ok"}
