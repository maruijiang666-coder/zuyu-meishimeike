"""Persistence for users, SMS login codes and a user's consultation history."""

from __future__ import annotations

from typing import Any

import psycopg

from app.db import utc_now

Row = dict[str, Any]


def get_user_by_phone(conn: psycopg.Connection, phone: str) -> Row | None:
    return conn.execute("SELECT * FROM users WHERE phone = %s", (phone,)).fetchone()


def get_user_by_id(conn: psycopg.Connection, user_id: int) -> Row | None:
    return conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()


def get_or_create_user(conn: psycopg.Connection, phone: str) -> Row:
    row = get_user_by_phone(conn, phone)
    if row is not None:
        return row
    now = utc_now()
    conn.execute(
        """
        INSERT INTO users (phone, nickname, status, created_at, last_login_at)
        VALUES (%s, %s, 'active', %s, %s)
        ON CONFLICT (phone) DO NOTHING
        """,
        (phone, f"用户{phone[-4:]}", now, now),
    )
    row = get_user_by_phone(conn, phone)
    assert row is not None
    return row


def touch_login(conn: psycopg.Connection, user_id: int) -> None:
    conn.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (utc_now(), user_id))


def invalidate_codes(conn: psycopg.Connection, phone: str, purpose: str = "login") -> None:
    conn.execute(
        """
        UPDATE sms_codes SET consumed_at = %s
        WHERE phone = %s AND purpose = %s AND consumed_at IS NULL
        """,
        (utc_now(), phone, purpose),
    )


def create_code(
    conn: psycopg.Connection,
    phone: str,
    code_hash: str,
    expires_at: str,
    ip: str,
    purpose: str = "login",
) -> int:
    invalidate_codes(conn, phone, purpose)
    cur = conn.execute(
        """
        INSERT INTO sms_codes (phone, purpose, code_hash, expires_at, ip, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (phone, purpose, code_hash, expires_at, ip[:64], utc_now()),
    )
    return int(cur.fetchone()["id"])


def latest_code(conn: psycopg.Connection, phone: str, purpose: str = "login") -> Row | None:
    return conn.execute(
        """
        SELECT * FROM sms_codes
        WHERE phone = %s AND purpose = %s AND consumed_at IS NULL
        ORDER BY id DESC LIMIT 1
        """,
        (phone, purpose),
    ).fetchone()


def increment_attempts(conn: psycopg.Connection, code_id: int) -> None:
    conn.execute("UPDATE sms_codes SET attempts = attempts + 1 WHERE id = %s", (code_id,))


def consume_code(conn: psycopg.Connection, code_id: int) -> None:
    conn.execute("UPDATE sms_codes SET consumed_at = %s WHERE id = %s", (utc_now(), code_id))


def delete_code(conn: psycopg.Connection, code_id: int) -> None:
    conn.execute("DELETE FROM sms_codes WHERE id = %s", (code_id,))


def last_code_sent_at(conn: psycopg.Connection, phone: str, purpose: str = "login") -> str | None:
    row = conn.execute(
        "SELECT MAX(created_at) AS last_sent FROM sms_codes WHERE phone = %s AND purpose = %s",
        (phone, purpose),
    ).fetchone()
    return row["last_sent"] if row and row["last_sent"] else None


def count_codes_since(
    conn: psycopg.Connection, phone: str, since: str, purpose: str = "login"
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM sms_codes
        WHERE phone = %s AND purpose = %s AND created_at >= %s
        """,
        (phone, purpose, since),
    ).fetchone()
    return int(row["n"])


def link_conversation_user(
    conn: psycopg.Connection, conversation_id: int, user_id: int, phone: str, nickname: str
) -> None:
    """Attach a conversation to a logged-in user without overwriting its data."""
    conn.execute(
        """
        UPDATE conversations
        SET user_id = COALESCE(user_id, %s),
            name = CASE WHEN name = '' THEN %s ELSE name END,
            contact = CASE WHEN contact = '' THEN %s ELSE contact END
        WHERE id = %s
        """,
        (user_id, nickname, phone, conversation_id),
    )


def list_user_conversations(
    conn: psycopg.Connection, user_id: int, limit: int = 50
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.session_id, c.source, c.page, c.created_at, c.updated_at,
               c.last_message, c.unread_visitor,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        WHERE c.user_id = %s
        ORDER BY c.updated_at DESC
        LIMIT %s
        """,
        (user_id, limit),
    ).fetchall()
    return [
        {
            "session_id": row["session_id"],
            "source": row["source"],
            "page": row["page"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_message": row["last_message"],
            "unread_visitor": row["unread_visitor"],
            "message_count": row["message_count"],
        }
        for row in rows
    ]
