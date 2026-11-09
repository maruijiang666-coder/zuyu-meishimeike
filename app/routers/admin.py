"""Admin API: password login, inbox, replies and CSV export."""

from __future__ import annotations

import csv
import hmac
import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.db import get_conn
from app.ratelimit import SlidingWindowLimiter
from app.repository import (
    add_message,
    count_conversations,
    ensure_conversation,
    export_rows,
    get_conversation,
    list_conversations,
    list_messages,
    mark_read_by_admin,
    overview,
)
from app.schemas import AdminLoginIn, AdminReplyIn

router = APIRouter(prefix="/admin")

login_limiter = SlidingWindowLimiter(limit=10, window=300)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64] or "unknown"
    return request.client.host if request.client else "unknown"


def require_admin(x_admin_token: str = Header(default="")) -> None:
    settings = get_settings()
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="未登录或登录已过期")


def _conversation_payload(row) -> dict:
    return {
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


@router.post("/login")
def login(payload: AdminLoginIn, request: Request) -> dict[str, str]:
    if not login_limiter.allow(f"login:{_client_ip(request)}"):
        raise HTTPException(status_code=429, detail="尝试次数过多，请 5 分钟后再试")
    settings = get_settings()
    if not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(status_code=401, detail="密码不正确")
    return {"token": settings.admin_token}


@router.get("/me", dependencies=[Depends(require_admin)])
def me() -> dict[str, bool]:
    return {"ok": True}


@router.get("/overview", dependencies=[Depends(require_admin)])
def get_overview() -> dict[str, int]:
    settings = get_settings()
    try:
        tz = ZoneInfo(settings.timezone)
    except Exception:
        tz = timezone.utc
    local_now = datetime.now(tz)
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start = local_start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_conn() as conn:
        return overview(conn, today_start)


@router.get("/conversations", dependencies=[Depends(require_admin)])
def conversations(
    q: str = Query(default="", max_length=60),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    query = q.strip()
    with get_conn() as conn:
        items = list_conversations(conn, query=query, limit=limit, offset=offset)
        total = count_conversations(conn, query=query)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/conversations/{session_id}", dependencies=[Depends(require_admin)])
def conversation_detail(session_id: str) -> dict:
    with get_conn() as conn:
        conversation = get_conversation(conn, session_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        messages = list_messages(conn, conversation["id"], after_id=0, limit=500)
        mark_read_by_admin(conn, conversation["id"])
        return {
            "conversation": _conversation_payload(conversation),
            "messages": messages,
        }


@router.post("/conversations/{session_id}/read", dependencies=[Depends(require_admin)])
def mark_read(session_id: str) -> dict[str, bool]:
    with get_conn() as conn:
        conversation = get_conversation(conn, session_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        mark_read_by_admin(conn, conversation["id"])
    return {"ok": True}


@router.post("/conversations/{session_id}/messages", dependencies=[Depends(require_admin)])
def reply(session_id: str, payload: AdminReplyIn) -> dict:
    with get_conn() as conn:
        conversation = ensure_conversation(conn, session_id)
        message = add_message(conn, conversation, "admin", payload.content)
        mark_read_by_admin(conn, conversation["id"])
    return {"message": message}


@router.get("/export.csv", dependencies=[Depends(require_admin)])
def export_csv() -> StreamingResponse:
    settings = get_settings()
    try:
        tz = ZoneInfo(settings.timezone)
    except Exception:
        tz = timezone.utc

    def local_time(value: str) -> str:
        try:
            dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return value

    with get_conn() as conn:
        rows = export_rows(conn)

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(["会话ID", "称呼", "联系方式", "来源", "最后消息", "创建时间", "更新时间"])
    for row in rows:
        writer.writerow(
            [
                row["session_id"],
                row["name"],
                row["contact"],
                row["source"],
                row["last_message"],
                local_time(row["created_at"]),
                local_time(row["updated_at"]),
            ]
        )
    data = buffer.getvalue()
    filename = "meike-leads.csv"
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
