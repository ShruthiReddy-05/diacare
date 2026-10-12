import os
import sys
from pathlib import Path

# Must be set before config/database are imported: tests never touch the
# dev diafit.db or any DATABASE_URL from .env (and the after-commit backup
# hook is a no-op on SQLite).
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
