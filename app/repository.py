"""Data access helpers for conversations, messages and leads (PostgreSQL)."""

from __future__ import annotations

from typing import Any

import psycopg

from app.db import utc_now

Row = dict[str, Any]


def _row_to_message(row: Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def _row_to_conversation(row: Row, *, message_count: int | None = None) -> dict[str, Any]:
    data = {
        "session_id": row["session_id"],
        "user_id": row["user_id"],
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


def get_conversation(conn: psycopg.Connection, session_id: str) -> Row | None:
    return conn.execute(
        "SELECT * FROM conversations WHERE session_id = %s", (session_id,)
    ).fetchone()


def ensure_conversation(
    conn: psycopg.Connection, session_id: str, source: str = "chat", page: str = ""
) -> Row:
    row = get_conversation(conn, session_id)
    if row is not None:
        if source and row["source"] == "chat" and source != "chat":
            conn.execute(
                "UPDATE conversations SET source = %s WHERE id = %s", (source, row["id"])
            )
        return row

    now = utc_now()
    conn.execute(
        """
        INSERT INTO conversations (session_id, source, page, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (session_id) DO NOTHING
        """,
        (session_id, source, page[:200], now, now),
    )
    row = get_conversation(conn, session_id)
    assert row is not None
    return row


def add_message(
    conn: psycopg.Connection, conversation: Row, role: str, content: str
) -> dict[str, Any]:
    now = utc_now()
    cur = conn.execute(
        """
        INSERT INTO messages (conversation_id, role, content, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (conversation["id"], role, content, now),
    )
    message_id = cur.fetchone()["id"]

    unread_admin = 1 if role == "visitor" else 0
    unread_visitor = 1 if role == "admin" else 0
    # Bot replies should not overwrite the inbox preview: the admin cares about
    # what the visitor (or a teammate) actually said.
    if role == "bot":
        conn.execute(
            "UPDATE conversations SET updated_at = %s WHERE id = %s",
            (now, conversation["id"]),
        )
    else:
        conn.execute(
            """
            UPDATE conversations
            SET last_message = %s, updated_at = %s,
                unread_admin = unread_admin + %s,
                unread_visitor = unread_visitor + %s
            WHERE id = %s
            """,
            (content.strip()[:120], now, unread_admin, unread_visitor, conversation["id"]),
        )
    return {
        "id": message_id,
        "role": role,
        "content": content,
        "created_at": now,
    }


def list_messages(
    conn: psycopg.Connection, conversation_id: int, after_id: int = 0, limit: int = 200
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, role, content, created_at
        FROM messages
        WHERE conversation_id = %s AND id > %s
        ORDER BY id ASC
        LIMIT %s
        """,
        (conversation_id, after_id, limit),
    ).fetchall()
    return [_row_to_message(row) for row in rows]


def update_contact(
    conn: psycopg.Connection, conversation: Row, name: str, contact: str
) -> None:
    conn.execute(
        """
        UPDATE conversations
        SET name = %s, contact = %s,
            last_message = CASE WHEN last_message = '' THEN %s ELSE last_message END,
            updated_at = %s
        WHERE id = %s
        """,
        (name[:40], contact[:80], f"联系方式：{contact[:80]}", utc_now(), conversation["id"]),
    )


def has_admin_reply(conn: psycopg.Connection, conversation_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM messages WHERE conversation_id = %s AND role = 'admin' LIMIT 1",
        (conversation_id,),
    ).fetchone()
    return row is not None


def mark_read_by_admin(conn: psycopg.Connection, conversation_id: int) -> None:
    conn.execute(
        "UPDATE conversations SET unread_admin = 0 WHERE id = %s", (conversation_id,)
    )


def mark_read_by_visitor(conn: psycopg.Connection, conversation_id: int) -> None:
    conn.execute(
        "UPDATE conversations SET unread_visitor = 0 WHERE id = %s", (conversation_id,)
    )


def list_conversations(
    conn: psycopg.Connection, query: str = "", limit: int = 50, offset: int = 0
) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if query:
        like = f"%{query}%"
        where = "WHERE c.name LIKE %s OR c.contact LIKE %s OR c.last_message LIKE %s"
        params.extend([like, like, like])
    params.extend([limit, offset])
    rows = conn.execute(
        f"""
        SELECT c.*,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        {where}
        ORDER BY c.updated_at DESC
        LIMIT %s OFFSET %s
        """,
        params,
    ).fetchall()
    return [_row_to_conversation(row, message_count=row["message_count"]) for row in rows]


def count_conversations(conn: psycopg.Connection, query: str = "") -> int:
    params: list[Any] = []
    where = ""
    if query:
        like = f"%{query}%"
        where = "WHERE name LIKE %s OR contact LIKE %s OR last_message LIKE %s"
        params.extend([like, like, like])
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM conversations {where}", params
    ).fetchone()
    return int(row["n"])


def overview(conn: psycopg.Connection, today_start: str) -> dict[str, int]:
    total = conn.execute("SELECT COUNT(*) AS n FROM conversations").fetchone()["n"]
    today = conn.execute(
        "SELECT COUNT(*) AS n FROM conversations WHERE created_at >= %s", (today_start,)
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


def export_rows(conn: psycopg.Connection, limit: int = 5000) -> list[Row]:
    return conn.execute(
        """
        SELECT session_id, name, contact, source, last_message,
               created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
