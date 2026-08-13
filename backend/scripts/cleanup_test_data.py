"""
Cleanup script: removes all user-generated test data from PostgreSQL.
Retains: admin accounts, audio assets, RAG rules, questionnaire data.

Usage:
  python scripts/cleanup_test_data.py [postgres_url]

  If DATABASE_URL is set in .env or environment, no argument needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

DELETE_ORDER = [
    # Children first (no FK dependencies on each other)
    "ai_prescription_outputs",
    "ai_prescription_requests",
    "question_responses",
    "risk_results",
    "prescriptions",
    "sugar_readings",
    "activity_logs",
    "follow_up_sessions",
    "follow_up_schedules",
    "notification_events",
    "notification_subscriptions",
    "reminders",
    "weekly_user_metrics",
    "participant_recovery_events",
    "app_sessions",
    "assessment_sessions",
    # Parent tables last
    "users",
]

KEEP_TABLES = [
    "admin_users",
    "admin_sessions",
    "audio_assets",
    "exercise_rag_rules",
]


def get_url() -> str:
    if len(sys.argv) >= 2:
        return sys.argv[1]
    from config import settings
    return settings.DATABASE_URL


async def cleanup():
    raw_url = get_url()
    # Convert async URL to sync psycopg2 URL for the cleanup
    pg_url = raw_url.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")

    if "sqlite" in pg_url:
        print("❌ This script is for PostgreSQL only. You're using SQLite.")
        print("   Switch to PostgreSQL first, then run this script.")
        sys.exit(1)

    print(f"Connecting to: {pg_url}")
    engine = create_engine(pg_url, poolclass=NullPool)

    try:
        conn = engine.connect()
        conn.execute(text("SELECT 1"))
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Cannot connect: {e}")
        sys.exit(1)

    # Disable triggers temporarily for clean truncation
    conn.execute(text("SET session_replication_role = 'replica';"))

    total_deleted = 0

    for table in DELETE_ORDER:
        # Check if table exists
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)",
            {"t": table}
        ))
        if not result.scalar():
            print(f"  ⚠️  Table '{table}' not found, skipping")
            continue

        result = conn.execute(text(f"DELETE FROM {table}"))
        deleted = result.rowcount
        total_deleted += deleted
        print(f"  🗑️  {table}: {deleted} rows deleted")

    # Re-enable triggers
    conn.execute(text("SET session_replication_role = 'origin';"))
    conn.commit()

    # Verify kept tables still have data
    print(f"\n{'='*50}")
    print(f"✅ Cleanup complete! {total_deleted} total rows removed.")
    print(f"{'='*50}")

    print("\nRetained tables:")
    for table in KEEP_TABLES:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"  ✅ {table}: {count} rows")

    conn.close()
    print("\nDone. System is ready for fresh testing.")


if __name__ == '__main__':
    asyncio.run(cleanup())
