import json
import logging
from base64 import urlsafe_b64decode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.follow_up import NotificationSubscription, NotificationEvent
from config import settings
from utils import ist_now

logger = logging.getLogger(__name__)

try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None

def _get_vapid_claims():
    return {
        "sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}",
    }

def _get_private_key():
    key = settings.VAPID_PRIVATE_KEY
    if key.startswith("LS0t"):
        from py_vapid import Vapid
        pem_bytes = urlsafe_b64decode(key + "==")
        return Vapid.from_pem(pem_bytes)
    return key

async def send_push_notification(
    subscription: NotificationSubscription,
    title: str,
    body: str,
    url: str = "/home",
    event_id: str = "",
):
    if not webpush:
        return False
    try:
        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url,
            "eventId": event_id,
        })
        private_key = _get_private_key()
        sub_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh_key,
                "auth": subscription.auth_key,
            }
        }
        webpush(
            subscription_info=sub_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=_get_vapid_claims(),
            headers={"TTL": "86400"},
        )
        return True
    except WebPushException as e:
        logger.warning("WebPush failed for endpoint %s: %s", subscription.endpoint[:50], e)
        return False
    except Exception as e:
        logger.error("Unexpected push error for endpoint %s: %s", subscription.endpoint[:50], e)
        return False

async def send_push_to_user(
    user_id: str,
    notif_type: str,
    title: str,
    body: str,
    url: str,
    db: AsyncSession,
):
    stmt = select(NotificationSubscription).where(
        NotificationSubscription.user_id == user_id
    )
    result = await db.execute(stmt)
    subs = result.scalars().all()

    now = ist_now()
    event = NotificationEvent(
        user_id=user_id,
        type=notif_type,
        scheduled_for=now,
        sent_at=None,
        status="scheduled",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    sent = False
    for sub in subs:
        ok = await send_push_notification(sub, title, body, url, event_id=event.id)
        if ok:
            sent = True

    event.sent_at = ist_now()
    event.status = "sent" if sent else "failed"
    await db.commit()
    await db.refresh(event)
    return event
