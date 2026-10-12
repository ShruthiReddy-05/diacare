"""
Add the Module D acknowledgement columns to an existing safety_events table.

The app creates tables with Base.metadata.create_all on startup, which never
alters a table that already exists -- so databases created before the
server-side safety lock need this one-off migration. Safe to re-run.

Adds:  status (open | acknowledged), acknowledged_by, acknowledgement_note
Backfills status from the old `resolved` flag.

NOTE: every existing event with resolved = false becomes "open", which locks
that patient's coaching until a clinician acknowledges it on the dashboard.
Review those events before or straight after deploying.

Usage (from backend/):
  python scripts/migrate_add_safety_event_status.py              # uses DATABASE_URL from .env
  python scripts/migrate_add_safety_event_status.py <database_url>
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

NEW_COLUMNS = [
    ("status", "VARCHAR(20) NOT NULL DEFAULT 'open'"),
    ("acknowledged_by", "VARCHAR(36) REFERENCES admin_users(id) ON DELETE SET NULL"),
    ("acknowledgement_note", "VARCHAR(1000)"),
]


async def migrate(database_url: str):
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            existing = await conn.run_sync(
                lambda sync_conn: {c["name"] for c in inspect(sync_conn).get_columns("safety_events")}
            )
            added = []
            for name, ddl in NEW_COLUMNS:
                if name not in existing:
                    await conn.execute(text(f"ALTER TABLE safety_events ADD COLUMN {name} {ddl}"))
                    added.append(name)

            if "status" in added:
                await conn.execute(text(
                    "UPDATE safety_events SET status = CASE WHEN resolved THEN 'acknowledged' ELSE 'open' END"
                ))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_safety_events_status ON safety_events (status)"))

            open_count = (await conn.execute(text("SELECT COUNT(*) FROM safety_events WHERE status = 'open'"))).scalar()

        print(f"Added columns: {', '.join(added) if added else 'none (already migrated)'}")
        print(f"Open safety events (patients currently locked by these): {open_count}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        from config import settings
        url = settings.DATABASE_URL
    asyncio.run(migrate(url))
