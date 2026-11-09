"""Public API: health check, consultation sessions and lead capture."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request

from app.chatbot import auto_reply
from app.config import get_settings
from app.db import get_conn
from app.ratelimit import SlidingWindowLimiter
from app.repository import (
    add_message,
    ensure_conversation,
    get_conversation,
    has_admin_reply,
    list_messages,
    mark_read_by_visitor,
    update_contact,
)
from app.schemas import ChatMessageIn, ChatSessionIn, ContactIn, LeadIn

router = APIRouter()

message_limiter = SlidingWindowLimiter(limit=20, window=60)
contact_limiter = SlidingWindowLimiter(limit=10, window=60)
lead_limiter = SlidingWindowLimiter(limit=5, window=300)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64] or "unknown"
    return request.client.host if request.client else "unknown"


def _ensure_rate_limit(limiter: SlidingWindowLimiter, key: str, message: str) -> None:
    if not limiter.allow(key):
        raise HTTPException(status_code=429, detail=message)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat/sessions")
def create_session(payload: ChatSessionIn) -> dict[str, str]:
    session_id = payload.session_id or uuid.uuid4().hex
    with get_conn() as conn:
        ensure_conversation(conn, session_id, payload.source, payload.page)
    return {"session_id": session_id}


@router.get("/chat/sessions/{session_id}/messages")
def fetch_messages(
    session_id: str,
    after_id: int = Query(default=0, ge=0),
) -> dict:
    with get_conn() as conn:
        conversation = get_conversation(conn, session_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        messages = list_messages(conn, conversation["id"], after_id=after_id)
        mark_read_by_visitor(conn, conversation["id"])
        return {"session_id": session_id, "messages": messages}


@router.get("/chat/sessions/{session_id}/unread")
def unread_count(session_id: str) -> dict[str, int]:
    with get_conn() as conn:
        conversation = get_conversation(conn, session_id)
        if conversation is None:
            return {"count": 0}
        return {"count": int(conversation["unread_visitor"])}


@router.post("/chat/sessions/{session_id}/messages")
def send_message(session_id: str, payload: ChatMessageIn, request: Request) -> dict:
    _ensure_rate_limit(message_limiter, f"msg:{client_ip(request)}", "发送太频繁了，请稍后再试")
    with get_conn() as conn:
        conversation = ensure_conversation(conn, session_id)
        message = add_message(conn, conversation, "visitor", payload.content)

        reply = None
        if not has_admin_reply(conn, conversation["id"]):
            text = auto_reply(payload.content)
            if text:
                reply = add_message(conn, conversation, "bot", text)
        return {"message": message, "reply": reply}


@router.post("/chat/sessions/{session_id}/contact")
def save_contact(session_id: str, payload: ContactIn, request: Request) -> dict:
    _ensure_rate_limit(contact_limiter, f"contact:{client_ip(request)}", "操作太频繁，请稍后再试")
    with get_conn() as conn:
        conversation = ensure_conversation(conn, session_id)
        update_contact(conn, conversation, payload.name, payload.contact)
        name = payload.name or "你"
        reply = add_message(
            conn,
            conversation,
            "bot",
            f"已收到，{name}。我们会尽快通过你留下的联系方式与你沟通，请留意消息。",
        )
        return {"ok": True, "reply": reply}


@router.post("/leads")
def create_lead(payload: LeadIn, request: Request) -> dict:
    """Contact form submission: lands in the same admin inbox as chat."""
    _ensure_rate_limit(lead_limiter, f"lead:{client_ip(request)}", "提交太频繁了，请稍后再试")
    settings = get_settings()
    requirement = payload.requirement or "希望了解技术服务与报价"
    session_id = f"form-{uuid.uuid4().hex}"
    with get_conn() as conn:
        conversation = ensure_conversation(conn, session_id, source=payload.source, page="contact-form")
        update_contact(conn, conversation, payload.name, payload.contact)
        add_message(conn, conversation, "visitor", f"【官网表单】{requirement}")
    # Make sure a misconfigured (external) message never leaks the admin path.
    return {"ok": True, "session_id": session_id, "company": settings.company_short}
