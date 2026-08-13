from datetime import datetime, timezone, timedelta

IST_OFFSET = timedelta(hours=5, minutes=30)

def ist_now() -> datetime:
    return (datetime.now(timezone.utc) + IST_OFFSET).replace(tzinfo=None)
