from datetime import datetime, timezone, timedelta
from typing import Any

IST_OFFSET = timedelta(hours=5, minutes=30)

def ist_now() -> datetime:
    return (datetime.now(timezone.utc) + IST_OFFSET).replace(tzinfo=None)

def safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None and val != "" else default
    except (ValueError, TypeError):
        return default

def safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None and val != "" else default
    except (ValueError, TypeError):
        return default
