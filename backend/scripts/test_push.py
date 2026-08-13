import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from config import settings
from services.push_notification_service import send_push_to_user

USER_ID = "pwate30"

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as db:
        await send_push_to_user(
            user_id=USER_ID,
            notif_type="follow_up",
            title="Weekly Check-In Reminder",
            body="How are you feeling this week? Tap to complete your check-in.",
            url="/follow-up",
            db=db,
        )
    print(f"Push notification sent to user {USER_ID}")

if __name__ == "__main__":
    asyncio.run(main())
