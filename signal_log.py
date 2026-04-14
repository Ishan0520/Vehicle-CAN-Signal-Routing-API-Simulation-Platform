# db/signal_log.py
# All functions that read/write the signal_log table.

import sqlite3
import logging
from datetime import datetime
from db.database import get_db

logger = logging.getLogger(__name__)


def log_signal(feature_name, signal_name, signal_value, can_message_id, raw_bytes, success=True) -> int:
    sql = """
        INSERT INTO signal_log
            (feature_name, signal_name, signal_value, can_message_id, raw_bytes, success, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with get_db() as conn:
        cursor = conn.execute(sql, (
            feature_name, signal_name, signal_value,
            can_message_id, raw_bytes, int(success),
            datetime.utcnow().isoformat()
        ))
        return cursor.lastrowid


def get_recent_signals(limit: int = 50) -> list[dict]:
    sql = """
        SELECT id, feature_name, signal_name, signal_value,
               can_message_id, raw_bytes, success, timestamp
        FROM signal_log ORDER BY id DESC LIMIT ?
    """
    with get_db() as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_signals_by_feature(feature_name: str, limit: int = 20) -> list[dict]:
    sql = """
        SELECT id, feature_name, signal_name, signal_value,
               can_message_id, raw_bytes, success, timestamp
        FROM signal_log WHERE feature_name = ? ORDER BY id DESC LIMIT ?
    """
    with get_db() as conn:
        rows = conn.execute(sql, (feature_name, limit)).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_signal_stats() -> dict:
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM signal_log").fetchone()[0]
        success = conn.execute("SELECT COUNT(*) FROM signal_log WHERE success = 1").fetchone()[0]
        by_feature = conn.execute(
            "SELECT feature_name, COUNT(*) as count FROM signal_log GROUP BY feature_name ORDER BY count DESC"
        ).fetchall()
        latest = conn.execute("SELECT timestamp FROM signal_log ORDER BY id DESC LIMIT 1").fetchone()

    return {
        "total_signals_sent": total,
        "successful": success,
        "failed": total - success,
        "by_feature": {row[0]: row[1] for row in by_feature},
        "last_signal_at": latest[0] if latest else None,
    }


def clear_log() -> int:
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM signal_log")
        return cursor.rowcount


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "feature_name": row["feature_name"],
        "signal_name": row["signal_name"],
        "signal_value": row["signal_value"],
        "can_message_id": row["can_message_id"],
        "can_message_hex": f"0x{row['can_message_id']:03X}",
        "raw_bytes": row["raw_bytes"],
        "success": bool(row["success"]),
        "timestamp": row["timestamp"],
    }