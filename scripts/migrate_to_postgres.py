"""
Migrate from SQLite to PostgreSQL.
Run this on the VPS after setting up PostgreSQL and updating .env.

Usage:
  1. Update .env with PostgreSQL URL (temporarily keep SQLite as DATABASE_URL_OLD)
  2. Run: python scripts/migrate_to_postgres.py [sqlite_path] [postgres_url]

Example:
  python scripts/migrate_to_postgres.py \
    /opt/apps/diafit/backend/diafit.db \
    postgresql+asyncpg://diafit_user:password@localhost:5432/diafit
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Tables in order (parents before children to respect FK constraints)
TABLES = [
    "admin_users",
    "users",
    "follow_up_schedules",
    "reminders",
    "exercise_rag_rules",
    "participant_recovery_events",
    "app_sessions",
    "assessment_sessions",
    "question_responses",
    "risk_results",
    "prescriptions",
    "ai_prescription_requests",
    "ai_prescription_outputs",
    "sugar_readings",
    "activity_logs",
    "follow_up_sessions",
    "notification_subscriptions",
    "notification_events",
    "weekly_user_metrics",
    "audio_assets",
    "admin_sessions",
]

async def migrate():
    if len(sys.argv) < 3:
        sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diafit.db")
        pg_url = os.environ.get("DATABASE_URL", "")
        if not pg_url:
            print("Usage: python scripts/migrate_to_postgres.py <sqlite_path> <postgres_url>")
            print("   Or set DATABASE_URL env var and pass only sqlite_path")
            sys.exit(1)
    else:
        sqlite_path = sys.argv[1]
        pg_url = sys.argv[2]

    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found: {sqlite_path}")
        sys.exit(1)

    # Connect to SQLite (sync)
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url, poolclass=NullPool)
    sqlite_conn = sqlite_engine.connect()

    # Connect to PostgreSQL (async engine, but we use sync for data copy)
    pg_sync_url = pg_url.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
    try:
        pg_engine = create_engine(pg_sync_url, poolclass=NullPool)
        pg_conn = pg_engine.connect()
    except Exception as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        print("   Make sure psycopg2-binary is installed: pip install psycopg2-binary")
        sqlite_conn.close()
        sys.exit(1)

    # Reflect SQLite metadata
    meta = MetaData()
    meta.reflect(bind=sqlite_engine)

    # Enable PG UUID extension
    pg_conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
    pg_conn.commit()

    total_rows = 0

    for table_name in TABLES:
        if table_name not in meta.tables:
            print(f"  ⚠️  Table '{table_name}' not found in SQLite, skipping")
            continue

        table = meta.tables[table_name]
        rows = sqlite_conn.execute(table.select()).fetchall()

        if not rows:
            print(f"  ➖ {table_name}: 0 rows (empty)")
            continue

        columns = [col.name for col in table.columns]
        placeholders = ", ".join([f":{col}" for col in columns])
        col_list = ", ".join(columns)

        inserted = 0
        for row in rows:
            values = dict(zip(columns, row))
            # Convert datetime/date to string for PG compatibility
            for k, v in values.items():
                if hasattr(v, 'isoformat'):
                    values[k] = v.isoformat()
                elif v is None:
                    values[k] = None
            try:
                pg_conn.execute(
                    text(f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"),
                    values
                )
                inserted += 1
            except Exception as e:
                print(f"  ⚠️  {table_name}: row error: {e}")

        pg_conn.commit()
        total_rows += inserted
        print(f"  ✅ {table_name}: {inserted}/{len(rows)} rows migrated")

    sqlite_conn.close()
    pg_conn.close()

    print(f"\n{'='*50}")
    print(f"✅ Migration complete! {total_rows} total rows copied.")
    print(f"{'='*50}")
    print(f"\nNext steps:")
    print(f"  1. Update .env: DATABASE_URL={pg_url}")
    print(f"  2. Restart the backend: sudo systemctl restart diafit-backend")
    print(f"  3. Verify: curl http://localhost:8000/api/admin/login")
    print(f"  4. Delete old SQLite DB once verified: rm {sqlite_path}.bak")

if __name__ == '__main__':
    asyncio.run(migrate())
