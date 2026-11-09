"""PostgreSQL access layer.

The application shares the PostgreSQL server already running on the deployment
host, but uses its own database (``meishi_app``). No SQLite files are involved.
"""

from __future__ import annotations

import atexit
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: ConnectionPool | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    phone         TEXT    NOT NULL UNIQUE,
    nickname      TEXT    NOT NULL DEFAULT '',
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    TEXT    NOT NULL,
    last_login_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sms_codes (
    id          BIGSERIAL PRIMARY KEY,
    phone       TEXT    NOT NULL,
    purpose     TEXT    NOT NULL DEFAULT 'login',
    code_hash   TEXT    NOT NULL,
    expires_at  TEXT    NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    consumed_at TEXT,
    ip          TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id             BIGSERIAL PRIMARY KEY,
    session_id     TEXT    NOT NULL UNIQUE,
    user_id        BIGINT,
    name           TEXT    NOT NULL DEFAULT '',
    contact        TEXT    NOT NULL DEFAULT '',
    source         TEXT    NOT NULL DEFAULT 'chat',
    page           TEXT    NOT NULL DEFAULT '',
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL,
    last_message   TEXT    NOT NULL DEFAULT '',
    unread_admin   INTEGER NOT NULL DEFAULT 0,
    unread_visitor INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT   NOT NULL CHECK (role IN ('visitor', 'admin', 'bot')),
    content         TEXT   NOT NULL,
    created_at      TEXT   NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sms_codes_phone ON sms_codes(phone, id DESC);
"""


def utc_now() -> str:
    """Current UTC time as an ISO-8601 string (second precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def conninfo() -> str:
    settings = get_settings()
    if settings.database_url:
        return settings.database_url
    return make_conninfo(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        dbname=settings.pg_db,
        connect_timeout=8,
        application_name="meishi-app",
    )


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    pool = get_pool()
    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo(),
            min_size=1,
            max_size=10,
            timeout=10,
            kwargs={"row_factory": dict_row},
            name="meishi-app",
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def _execute_script(conn: psycopg.Connection, script: str) -> None:
    for statement in script.split(";"):
        statement = statement.strip()
        if statement:
            conn.execute(statement)


def init_db() -> None:
    with get_conn() as conn:
        _execute_script(conn, SCHEMA)
        # Lightweight migration for an existing installation.
        conn.execute(
            "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id BIGINT"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
        )


def reset_db() -> None:
    """Drop our tables. Refuses to run against anything but a *_test database."""
    settings = get_settings()
    if not settings.pg_db.endswith("_test"):
        raise RuntimeError(
            f"拒绝清空数据库 {settings.pg_db!r}：reset_db 只允许 *_test 测试库"
        )
    with get_conn() as conn:
        conn.execute(
            "DROP TABLE IF EXISTS messages, conversations, sms_codes, users CASCADE"
        )
        _execute_script(conn, SCHEMA)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)"
        )


atexit.register(close_pool)
