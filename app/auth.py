"""User session cookie helpers shared by pages and API routes."""

from __future__ import annotations

from typing import Any

import psycopg
from fastapi import Request, Response

from app.config import get_settings
from app.db import get_conn
from app.security import (
    create_session_token,
    mask_phone,
    request_is_https,
    verify_session_token,
)
from app.user_repo import get_user_by_id

COOKIE_NAME = "meike_user"


def public_user(row: dict[str, Any]) -> dict:
    return {
        "id": int(row["id"]),
        "phone": row["phone"],
        "masked_phone": mask_phone(row["phone"]),
        "nickname": row["nickname"],
        "status": row["status"],
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
    }


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    settings = get_settings()
    user_id = verify_session_token(token, settings.session_secret)
    if user_id is None:
        return None
    try:
        with get_conn() as conn:
            row = get_user_by_id(conn, user_id)
    except psycopg.Error:
        return None
    if row is None or row["status"] != "active":
        return None
    return public_user(row)


def set_user_cookie(response: Response, user_id: int, request: Request) -> None:
    settings = get_settings()
    max_age = max(1, settings.user_session_days) * 86400
    token = create_session_token(user_id, settings.session_secret, max_age)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=request_is_https(request),
        path="/",
    )


def clear_user_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
