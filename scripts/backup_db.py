"""
Standalone script to trigger a database backup.

Usage:
  python scripts/backup_db.py            # run once
  python scripts/backup_db.py --listen    # listen for PG NOTIFY (deprecated — use after_commit)

Reads config from backend/.env:
  DATABASE_URL
  GITHUB_TOKEN
  GITHUB_REPO
"""

import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from services.backup_service import do_backup


if __name__ == "__main__":
    if "--listen" in sys.argv:
        print("[backup] --listen mode is deprecated. The backup now runs via after_commit listener in main.py.")
        print("[backup] To run a one-off backup: python scripts/backup_db.py")
        sys.exit(0)

    do_backup(triggered_by="manual")
