"""Data access helpers for conversations, messages and leads."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.db import utc_now


def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def _row_to_conversation(row: sqlite3.Row, *, message_count: int | None = None) -> dict[str, Any]:
    data = {
        "session_id": row["session_id"],
        "name": row["name"],
        "contact": row["contact"],
        "source": row["source"],
        "page": row["page"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_message": row["last_message"],
        "unread_admin": row["unread_admin"],
        "unread_visitor": row["unread_visitor"],
    }
    if message_count is not None:
        data["message_count"] = message_count
    return data


def get_conversation(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()


def ensure_conversation(
    conn: sqlite3.Connection, session_id: str, source: str = "chat", page: str = ""
) -> sqlite3.Row:
    row = get_conversation(conn, session_id)
    if row is not None:
        if source and row["source"] == "chat" and source != "chat":
            conn.execute(
                "UPDATE conversations SET source = ? WHERE id = ?", (source, row["id"])
            )
        return row

    now = utc_now()
    try:
        conn.execute(
            """
            INSERT INTO conversations (session_id, source, page, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, source, page[:200], now, now),
        )
    except sqlite3.IntegrityError:
        # Another request created it first; reuse it.
        pass
    row = get_conversation(conn, session_id)
    assert row is not None
    return row


def add_message(
    conn: sqlite3.Connection, conversation: sqlite3.Row, role: str, content: str
) -> dict[str, Any]:
    now = utc_now()
    cur = conn.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation["id"], role, content, now),
    )
    unread_admin = 1 if role == "visitor" else 0
    unread_visitor = 1 if role == "admin" else 0
    # Bot replies should not overwrite the inbox preview: the admin cares about
    # what the visitor (or a teammate) actually said.
    if role == "bot":
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation["id"]),
        )
    else:
        conn.execute(
            """
            UPDATE conversations
            SET last_message = ?, updated_at = ?,
                unread_admin = unread_admin + ?,
                unread_visitor = unread_visitor + ?
            WHERE id = ?
            """,
            (content.strip()[:120], now, unread_admin, unread_visitor, conversation["id"]),
        )
    return {
        "id": cur.lastrowid,
        "role": role,
        "content": content,
        "created_at": now,
    }


def list_messages(
    conn: sqlite3.Connection, conversation_id: int, after_id: int = 0, limit: int = 200
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = ? AND id > ?
        ORDER BY id ASC
        LIMIT ?
        """,
        (conversation_id, after_id, limit),
    ).fetchall()
    return [_row_to_message(row) for row in rows]


def update_contact(
    conn: sqlite3.Connection, conversation: sqlite3.Row, name: str, contact: str
) -> None:
    conn.execute(
        """
        UPDATE conversations
        SET name = ?, contact = ?,
            last_message = CASE WHEN last_message = '' THEN ? ELSE last_message END,
            updated_at = ?
        WHERE id = ?
        """,
        (name[:40], contact[:80], f"联系方式：{contact[:80]}", utc_now(), conversation["id"]),
    )


def has_admin_reply(conn: sqlite3.Connection, conversation_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM messages WHERE conversation_id = ? AND role = 'admin' LIMIT 1",
        (conversation_id,),
    ).fetchone()
    return row is not None


def mark_read_by_admin(conn: sqlite3.Connection, conversation_id: int) -> None:
    conn.execute(
        "UPDATE conversations SET unread_admin = 0 WHERE id = ?", (conversation_id,)
    )


def mark_read_by_visitor(conn: sqlite3.Connection, conversation_id: int) -> None:
    conn.execute(
        "UPDATE conversations SET unread_visitor = 0 WHERE id = ?", (conversation_id,)
    )


def list_conversations(
    conn: sqlite3.Connection, query: str = "", limit: int = 50, offset: int = 0
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if query:
        like = f"%{query}%"
        where = "WHERE c.name LIKE ? OR c.contact LIKE ? OR c.last_message LIKE ?"
        params.extend([like, like, like])
    params.extend([limit, offset])
    rows = conn.execute(
        f"""
        SELECT c.*,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        {where}
        ORDER BY c.updated_at DESC
        LIMIT ? OFFSET ?
        """,
        params,
    ).fetchall()
    return [_row_to_conversation(row, message_count=row["message_count"]) for row in rows]


def count_conversations(conn: sqlite3.Connection, query: str = "") -> int:
    params: list[Any] = []
    where = ""
    if query:
        like = f"%{query}%"
        where = "WHERE name LIKE ? OR contact LIKE ? OR last_message LIKE ?"
        params.extend([like, like, like])
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM conversations {where}", params
    ).fetchone()
    return int(row["n"])


def overview(conn: sqlite3.Connection, today_start: str) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]
    today = conn.execute(
        "SELECT COUNT(*) AS n FROM conversations WHERE created_at >= ?", (today_start,)
    ).fetchone()["n"]
    leads = conn.execute(
        "SELECT COUNT(*) AS n FROM conversations WHERE contact <> ''"
    ).fetchone()["n"]
    unread = conn.execute(
        "SELECT COALESCE(SUM(unread_admin), 0) AS n FROM conversations"
    ).fetchone()["n"]
    messages = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
    return {
        "total": int(total),
        "today": int(today),
        "leads": int(leads),
        "unread": int(unread),
        "messages": int(messages),
    }


def export_rows(conn: sqlite3.Connection, limit: int = 5000) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT session_id, name, contact, source, last_message,
               created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
