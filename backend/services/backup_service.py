import os
import sys
import json
import time
import shutil
import datetime
import sqlite3
import subprocess
import threading
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

from github import Github

from config import settings
from utils import ist_now
from models.backup_log import BackupLog

logger = logging.getLogger(__name__)

BACKUP_DIR_LOCAL = Path("/opt/apps/diacare/backups")
BACKUP_DIR_GITHUB = "backups/"
MAX_BACKUPS = 15
MIN_DAILY = 7
_lock = threading.Lock()


def _get_github_repo():
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPO")
    if not token or not repo_name:
        logger.warning("GITHUB_TOKEN or GITHUB_REPO not set")
        return None
    try:
        return Github(token).get_repo(repo_name)
    except Exception as e:
        logger.error("GitHub connection failed: %s", e)
        return None


def _pg_to_sqlite(pg_url, sqlite_path):
    import psycopg2
    from psycopg2.extras import RealDictCursor

    pg_conn = psycopg2.connect(pg_url)
    pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)

    pg_cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE'"
    )
    tables = [r["table_name"] for r in pg_cur.fetchall()]

    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)

    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row

    for table in tables:
        pg_cur.execute(f'SELECT * FROM "{table}"')
        rows = pg_cur.fetchall()
        if not rows:
            logger.info("  %s: 0 rows (empty)", table)
            continue

        cols = list(rows[0].keys())
        col_defs = []
        for c in cols:
            val = rows[0][c]
            if val is None:
                col_defs.append(f'"{c}" TEXT')
            elif isinstance(val, bool):
                col_defs.append(f'"{c}" BOOLEAN')
            elif isinstance(val, int):
                col_defs.append(f'"{c}" INTEGER')
            elif isinstance(val, float):
                col_defs.append(f'"{c}" REAL')
            else:
                col_defs.append(f'"{c}" TEXT')

        sq.execute(f'DROP TABLE IF EXISTS "{table}"')
        sq.execute(f'CREATE TABLE "{table}" ({", ".join(col_defs)})')

        placeholders = ", ".join(["?" for _ in cols])
        quoted_cols = ", ".join([f'"{c}"' for c in cols])
        for row in rows:
            values = []
            for c in cols:
                v = row[c]
                if isinstance(v, bool):
                    v = int(v)
                elif isinstance(v, (datetime.datetime, datetime.date)):
                    v = v.isoformat()
                elif isinstance(v, (dict, list)):
                    v = json.dumps(v)
                values.append(v)
            sq.execute(
                f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})',
                values,
            )
        sq.commit()
        logger.info("  %s: %s rows", table, len(rows))

    sq.close()
    pg_cur.close()
    pg_conn.close()
    logger.info("SQLite snapshot saved to %s", sqlite_path)


def _pg_dump_local(pg_url, bkp_path):
    pg_dump_path = shutil.which("pg_dump")
    if not pg_dump_path:
        logger.warning("pg_dump not found in PATH — skipping local .bkp dump")
        return

    BACKUP_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["pg_dump", "-Fc", "-Z", "9", "-d", pg_url, "-f", str(bkp_path)],
        check=True,
    )
    logger.info("pg_dump saved to %s", bkp_path)


def _parse_backup_name(name):
    try:
        date_part = name.replace("DiaCare_", "").replace(".db", "").replace(".bkp", "")
        return datetime.datetime.strptime(date_part, "%Y%m%d_%H%M%S")
    except (ValueError, AttributeError):
        return None


def _retain(backups):
    backups.sort(key=lambda x: x["date"], reverse=True)
    kept = set()
    kept_paths = set()
    for item in backups:
        day = item["date"].strftime("%Y-%m-%d")
        if day not in kept and len(kept) < MIN_DAILY:
            kept.add(day)
            kept_paths.add(item["path"])
    for item in backups:
        if len(kept_paths) >= MAX_BACKUPS:
            break
        if item["path"] not in kept_paths:
            kept_paths.add(item["path"])
    return kept_paths


def _delete_old_backups_github(repo):
    try:
        contents = repo.get_contents(BACKUP_DIR_GITHUB, ref="main")
    except Exception:
        return

    backups = []
    for f in contents:
        dt = _parse_backup_name(f.name)
        if dt:
            backups.append({"file": f, "path": f.path, "date": dt})

    kept = _retain(backups)
    for item in backups:
        if item["path"] not in kept:
            try:
                repo.delete_file(item["path"], f"Deleted {item['file'].name}", item["file"].sha, branch="main")
                logger.info("Deleted old GitHub backup: %s", item["file"].name)
            except Exception as e:
                logger.warning("GitHub delete failed for %s: %s", item["file"].name, e)


def _delete_old_backups_local():
    if not BACKUP_DIR_LOCAL.exists():
        return
    files = []
    for p in sorted(BACKUP_DIR_LOCAL.iterdir(), reverse=True):
        dt = _parse_backup_name(p.name)
        if dt:
            files.append({"path": str(p), "date": dt})

    kept = _retain(files)
    for item in files:
        if item["path"] not in kept:
            try:
                os.remove(item["path"])
                logger.info("Deleted old local backup: %s", item["path"])
            except Exception as e:
                logger.warning("Local delete failed for %s: %s", item["path"], e)


def _update_backup_log(db_url, triggered_by):
    from sqlalchemy import create_engine, text

    engine = create_engine(_to_sync_url(db_url))
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO backup_log (id, last_backup_at, triggered_by) "
                    "VALUES (gen_random_uuid()::text, :now, :by)"
                ),
                {"now": ist_now(), "by": triggered_by},
            )
            conn.commit()
        logger.info("BackupLog updated")
    finally:
        engine.dispose()


def _to_sync_url(async_url):
    """Convert postgresql+asyncpg://... to postgresql://... for sync drivers."""
    if "+" in async_url and "://" in async_url:
        scheme, rest = async_url.split("://", 1)
        if "+" in scheme:
            return scheme.split("+")[0] + "://" + rest
    return async_url


def do_backup(triggered_by="auto"):
    if not _lock.acquire(blocking=False):
        logger.info("Backup skipped — another run in progress")
        return

    try:
        if settings.DATABASE_URL.startswith("sqlite"):
            logger.info("SQLite database — skipping backup")
            return

        pg_url = _to_sync_url(settings.DATABASE_URL)

        IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        timestamp = datetime.datetime.now(IST).strftime("%Y%m%d_%H%M%S")

        tmp_sqlite = f"/tmp/DiaCare_{timestamp}.db"
        local_bkp = BACKUP_DIR_LOCAL / f"DiaCare_{timestamp}.bkp"

        logger.info("Starting backup (triggered_by=%s) ...", triggered_by)

        _pg_to_sqlite(pg_url, tmp_sqlite)
        _pg_dump_local(pg_url, local_bkp)

        # Upload to GitHub
        repo = _get_github_repo()
        if repo:
            gh_path = f"{BACKUP_DIR_GITHUB}DiaCare_{timestamp}.db"
            with open(tmp_sqlite, "rb") as f:
                content = f.read()
            repo.create_file(gh_path, f"Backup {timestamp}", content, branch="main")
            logger.info("Uploaded to GitHub: %s", gh_path)
            _delete_old_backups_github(repo)

        # Cleanup local old backups
        _delete_old_backups_local()

        # Update log
        _update_backup_log(pg_url, triggered_by)

        os.remove(tmp_sqlite)
        logger.info("Backup complete")
    except Exception as e:
        logger.error("Backup failed: %s", e)
        import traceback
        traceback.print_exc()
    finally:
        _lock.release()
