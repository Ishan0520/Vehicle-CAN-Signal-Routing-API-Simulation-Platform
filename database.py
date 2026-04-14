# db/database.py
# Sets up the SQLite database that stores every CAN signal ever sent.

import sqlite3
import logging
from contextlib import contextmanager
from core.config import settings

logger = logging.getLogger(__name__)

CREATE_SIGNAL_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS signal_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_name    TEXT    NOT NULL,
    signal_name     TEXT    NOT NULL,
    signal_value    REAL    NOT NULL,
    can_message_id  INTEGER NOT NULL,
    raw_bytes       TEXT    NOT NULL,
    success         INTEGER NOT NULL DEFAULT 1,
    timestamp       TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_signal_log_timestamp
ON signal_log (timestamp DESC);
"""

CREATE_FEATURE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_signal_log_feature
ON signal_log (feature_name);
"""


def init_db() -> None:
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(CREATE_SIGNAL_LOG_TABLE)
        conn.execute(CREATE_TIMESTAMP_INDEX)
        conn.execute(CREATE_FEATURE_INDEX)
        conn.commit()

    logger.info(f"Database initialised: {db_path}")


@contextmanager
def get_db():
    conn = sqlite3.connect(str(settings.db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()