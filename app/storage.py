import sqlite3
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from .models import get_db, get_db_path


def insert_message(message_id: str, from_msisdn: str, to_msisdn: str, ts: str, text: Optional[str]) -> Tuple[bool, str]:
    """Insert message. Returns (created, result_str) where result_str is 'created' or 'duplicate'."""
    con = get_db()
    cur = con.cursor()
    created_at = datetime.utcnow().isoformat() + "Z"
    try:
        cur.execute(
            "INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, from_msisdn, to_msisdn, ts, text, created_at),
        )
        con.commit()
        return True, "created"
    except sqlite3.IntegrityError:
        return False, "duplicate"


def query_messages(limit: int, offset: int, from_filter: Optional[str], since: Optional[str], q: Optional[str]) -> Tuple[List[Dict[str, Any]], int]:
    con = get_db()
    cur = con.cursor()
    where = []
    params: List = []
    if from_filter:
        where.append("from_msisdn = ?")
        params.append(from_filter)
    if since:
        where.append("ts >= ?")
        params.append(since)
    if q:
        where.append("LOWER(text) LIKE ?")
        params.append(f"%{q.lower()}%")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    count_sql = f"SELECT COUNT(*) FROM messages {where_sql}"
    cur.execute(count_sql, params)
    total = cur.fetchone()[0]

    sql = f"SELECT message_id, from_msisdn, to_msisdn, ts, text, created_at FROM messages {where_sql} ORDER BY ts ASC, message_id ASC LIMIT ? OFFSET ?"
    cur.execute(sql, params + [limit, offset])
    rows = cur.fetchall()
    data = [
        {
            "message_id": r[0],
            "from": r[1],
            "to": r[2],
            "ts": r[3],
            "text": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]
    return data, total


def stats() -> Dict[str, Any]:
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM messages")
    total_messages = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT from_msisdn) FROM messages")
    senders_count = cur.fetchone()[0]

    cur.execute("SELECT from_msisdn, COUNT(*) as cnt FROM messages GROUP BY from_msisdn ORDER BY cnt DESC LIMIT 10")
    top = cur.fetchall()
    messages_per_sender = [{"from": r[0], "count": r[1]} for r in top]

    cur.execute("SELECT MIN(ts), MAX(ts) FROM messages")
    first_ts, last_ts = cur.fetchone()

    return {
        "total_messages": total_messages,
        "senders_count": senders_count,
        "messages_per_sender": messages_per_sender,
        "first_message_ts": first_ts,
        "last_message_ts": last_ts,
    }


def check_db_ready() -> bool:
    try:
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        row = cur.fetchone()
        return row is not None
    except Exception:
        return False
