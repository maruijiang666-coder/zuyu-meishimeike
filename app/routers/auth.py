"""Phone + SMS verification code login for site visitors."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth import clear_user_cookie, get_current_user, public_user, set_user_cookie
from app.config import get_settings
from app.db import get_conn
from app.ratelimit import SlidingWindowLimiter
from app.schemas import PhoneLoginIn, SendCodeIn
from app.security import (
    client_ip,
    generate_code,
    hash_code,
    normalize_phone,
)
from app.sms import send_login_code
from app.user_repo import (
    consume_code,
    count_codes_since,
    create_code,
    delete_code,
    get_or_create_user,
    increment_attempts,
    last_code_sent_at,
    latest_code,
    touch_login,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

send_code_ip_limiter = SlidingWindowLimiter(limit=10, window=600)
login_ip_limiter = SlidingWindowLimiter(limit=20, window=300)

CODE_COOLDOWN_SECONDS = 60
CODE_HOURLY_LIMIT = 5
CODE_MAX_ATTEMPTS = 5


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@router.post("/send-code")
def send_code(payload: SendCodeIn, request: Request) -> dict:
    settings = get_settings()
    ip = client_ip(request)
    if not send_code_ip_limiter.allow(f"send:{ip}"):
        raise HTTPException(status_code=429, detail="操作太频繁，请稍后再试")
    if settings.sms_mode == "disabled":
        raise HTTPException(status_code=503, detail="短信服务未配置，请联系管理员")

    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号")

    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        last = last_code_sent_at(conn, phone)
        if last:
            elapsed = (now - _parse_utc(last)).total_seconds()
            if elapsed < CODE_COOLDOWN_SECONDS:
                wait = max(1, int(CODE_COOLDOWN_SECONDS - elapsed))
                raise HTTPException(status_code=429, detail=f"发送太频繁，请 {wait} 秒后再试")
        since = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if count_codes_since(conn, phone, since) >= CODE_HOURLY_LIMIT:
            raise HTTPException(status_code=429, detail="该手机号验证码发送次数过多，请稍后再试")

        code = generate_code(6)
        expires_at = (now + timedelta(seconds=settings.sms_code_ttl_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        code_id = create_code(
            conn,
            phone,
            hash_code(settings.session_secret, phone, code),
            expires_at,
            ip,
        )

    result = send_login_code(phone, code)
    if not result.ok:
        with get_conn() as conn:
            delete_code(conn, code_id)
        logger.warning("登录验证码发送失败 phone=%s code=%s", phone, result.code)
        raise HTTPException(status_code=502, detail="短信发送失败，请稍后再试")

    return {
        "ok": True,
        "cooldown": CODE_COOLDOWN_SECONDS,
        "message": "验证码已发送",
        # Only exposed in local debugging; never enable SMS_DEBUG in production.
        "debug_code": code if settings.sms_debug else "",
    }


@router.post("/login")
def login(payload: PhoneLoginIn, request: Request) -> JSONResponse:
    settings = get_settings()
    ip = client_ip(request)
    if not login_ip_limiter.allow(f"login:{ip}"):
        raise HTTPException(status_code=429, detail="尝试次数过多，请稍后再试")

    phone = normalize_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="请输入正确的 11 位手机号")
    code = payload.code.strip()
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="请输入短信中的数字验证码")

    error: tuple[int, str] | None = None
    user_data: dict | None = None
    with get_conn() as conn:
        row = latest_code(conn, phone)
        if row is None:
            error = (401, "验证码已失效，请重新获取")
        elif _parse_utc(row["expires_at"]) < datetime.now(timezone.utc):
            error = (401, "验证码已过期，请重新获取")
        elif int(row["attempts"]) >= CODE_MAX_ATTEMPTS:
            error = (401, "验证码错误次数过多，请重新获取")
        elif not compare_digest(
            hash_code(settings.session_secret, phone, code), row["code_hash"]
        ):
            increment_attempts(conn, row["id"])
            error = (401, "验证码不正确")
        else:
            user = get_or_create_user(conn, phone)
            if user["status"] != "active":
                error = (403, "账号状态异常，请联系客服")
            else:
                consume_code(conn, row["id"])
                touch_login(conn, user["id"])
                user_data = public_user(user)

    if error is not None:
        raise HTTPException(status_code=error[0], detail=error[1])
    assert user_data is not None

    response = JSONResponse({"ok": True, "user": user_data})
    set_user_cookie(response, int(user_data["id"]), request)
    return response


@router.post("/logout")
def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    clear_user_cookie(response)
    return response


@router.get("/me")
def me(request: Request) -> dict:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return {"user": user}
