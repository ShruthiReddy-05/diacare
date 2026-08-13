"""
Standalone script to seed an admin user.
Usage: python scripts/seed_admin.py [db_url] [username] [password]

If no args given, reads DATABASE_URL from environment (or .env),
or falls back to the local SQLite file.
"""

import sys
import os
import re
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _dotenv_load(path):
    """Minimal .env loader – only reads DATABASE_URL."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${pwd_hash}"


def parse_pg_dsn(dsn: str):
    """Extract host, port, dbname, user, password from a postgresql+asyncpg:// URL."""
    # strip any +driver suffix
    dsn = re.sub(r"^postgresql(\+[a-z0-9_]+)?://", "postgresql://", dsn)
    m = re.match(
        r"postgresql://(?:([^:]+)(?::([^@]+))?@)?([^:/]+)(?::(\d+))?/(.+)",
        dsn,
    )
    if not m:
        raise ValueError(f"Cannot parse PostgreSQL DSN: {dsn}")
    user, pwd, host, port, dbname = m.groups()
    return {
        "host": host or "localhost",
        "port": int(port) if port else 5432,
        "dbname": dbname,
        "user": user or "postgres",
        "password": pwd or "",
    }


def main():
    # --- resolve db_url ---
    db_url = sys.argv[1] if len(sys.argv) >= 2 else os.getenv("DATABASE_URL")
    if not db_url and Path(".env").exists():
        db_url = _dotenv_load(Path(".env"))
    if not db_url:
        # fallback to local SQLite
        script_dir = Path(__file__).resolve().parent
        db_path = script_dir.parent / "diafit.db"
        if not db_path.exists():
            print(f"Error: SQLite database not found at {db_path}")
            print("Provide a DATABASE_URL or a local path.")
            sys.exit(1)
        db_url = f"sqlite:///{db_path}"

    username = sys.argv[2] if len(sys.argv) >= 3 else "admin"
    password = sys.argv[3] if len(sys.argv) >= 4 else "diafit2026"

    # --- connect & insert ---
    if db_url.startswith("sqlite"):
        # --- SQLite path ---
        m = re.match(r"sqlite:///(.+)", db_url)
        db_path = m.group(1) if m else db_url.replace("sqlite:///", "")
        db_path = Path(db_path)
        if not db_path.exists():
            print(f"Error: Database not found at {db_path}")
            sys.exit(1)

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'"
        )
        if not cursor.fetchone():
            print("Error: admin_users table does not exist. Run the backend first.")
            conn.close()
            sys.exit(1)

        cursor.execute(
            "SELECT id FROM admin_users WHERE username = ?", (username,)
        )
        existing = cursor.fetchone()
        if existing:
            print(f"Admin user '{username}' already exists (id={existing[0]}). Skipping.")
            conn.close()
            return

        user_id = str(uuid.uuid4())
        pwd_hash = hash_password(password)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO admin_users (id, username, password_hash, display_name, role, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, pwd_hash, username.capitalize(), "admin", now),
        )
        conn.commit()
        conn.close()

    elif db_url.startswith("postgresql"):
        # --- PostgreSQL path ---
        try:
            import psycopg2
        except ImportError:
            import psycopg2.binary as psycopg2  # psycopg2-binary

        params = parse_pg_dsn(db_url)
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'admin_users')"
        )
        if not cursor.fetchone()[0]:
            print("Error: admin_users table does not exist. Run the backend first.")
            conn.close()
            sys.exit(1)

        cursor.execute("SELECT id FROM admin_users WHERE username = %s", (username,))
        existing = cursor.fetchone()
        if existing:
            print(f"Admin user '{username}' already exists (id={existing[0]}). Skipping.")
            conn.close()
            return

        user_id = str(uuid.uuid4())
        pwd_hash = hash_password(password)
        now = datetime.now(timezone.utc)

        cursor.execute(
            "INSERT INTO admin_users (id, username, password_hash, display_name, role, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, username, pwd_hash, username.capitalize(), "admin", now),
        )
        conn.commit()
        conn.close()

    else:
        print(f"Unsupported database URL scheme: {db_url}")
        sys.exit(1)

    print(f"Admin user created successfully!")
    print(f"  Database: {db_url}")
    print(f"  Username: {username}")
    print(f"  Password: {password}")


if __name__ == "__main__":
    main()
