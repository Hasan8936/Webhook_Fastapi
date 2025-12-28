import sqlite3
from datetime import datetime
from .config import settings
import os


DB_PATH = None


def get_db_path():
    global DB_PATH
    if DB_PATH:
        return DB_PATH
    # DATABASE_URL like sqlite:////data/app.db
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///"):
        # strip the sqlite:/// prefix; supports sqlite:////absolute/path
        path = url[len("sqlite:///"):]
        # ensure directory exists
        dirpath = os.path.dirname(path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        DB_PATH = path
        return DB_PATH
    raise RuntimeError("Invalid DATABASE_URL")


def init_db():
    path = get_db_path()
    con = sqlite3.connect(path, check_same_thread=False)
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
          message_id TEXT PRIMARY KEY,
          from_msisdn TEXT NOT NULL,
          to_msisdn TEXT NOT NULL,
          ts TEXT NOT NULL,
          text TEXT,
          created_at TEXT NOT NULL
        )
        """
    )
    con.commit()
    cur.close()
    return con


# Provide a simple connection factory
_GLOBAL_CON = None


def get_db():
    global _GLOBAL_CON
    if _GLOBAL_CON is None:
        _GLOBAL_CON = init_db()
    return _GLOBAL_CON
