import os
import sqlite3
from datetime import datetime
from pathlib import Path

source = Path(os.getenv("DATABASE_PATH", "./data/wishlist.sqlite3"))
target_dir = Path(os.getenv("BACKUP_DIR", "./backups"))
target_dir.mkdir(parents=True, exist_ok=True)
if not source.exists():
    raise SystemExit(f"Database not found: {source}")
target = target_dir / f"wishlist-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3"
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
print(f"Backup created: {target}")
