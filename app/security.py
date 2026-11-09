"""Phone normalization, SMS code hashing and signed user sessions."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
import time
from urllib.parse import urlsplit


def normalize_phone(raw: str | None) -> str:
    """Return an 11-digit mainland phone number, or an empty string."""
    text = str(raw or "").strip()
    if not text:
        return ""
    digits = re.sub(r"[\s\-()（）]", "", text)
    if digits.startswith("+"):
        digits = digits[1:]
    if not digits.isdigit():
        return ""
    if digits.startswith("0086"):
        digits = digits[4:]
    elif digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    if len(digits) != 11 or digits[0] != "1" or digits[1] not in "3456789":
        return ""
    return digits


def to_e164(phone: str) -> str:
    return "+86" + phone


def mask_phone(phone: str) -> str:
    if len(phone) != 11:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def generate_code(length: int = 6) -> str:
    upper = 10**length
    return str(secrets.randbelow(upper)).zfill(length)


def hash_code(secret: str, phone: str, code: str) -> str:
    message = f"meike-sms::{phone}::{code}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def create_session_token(user_id: int, secret: str, ttl_seconds: int) -> str:
    expires = int(time.time()) + max(60, int(ttl_seconds))
    nonce = secrets.token_urlsafe(12)
    payload = f"{int(user_id)}.{expires}.{nonce}"
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}.{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def verify_session_token(token: str, secret: str) -> int | None:
    """Return the user id for a valid, unexpired token; None otherwise."""
    if not token or len(token) > 512:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        user_id_text, expires_text, nonce, signature = raw.split(".", 3)
        if not user_id_text.isdigit() or not expires_text.isdigit() or not nonce:
            return None
        payload = f"{user_id_text}.{expires_text}.{nonce}"
        expected = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(expires_text) < int(time.time()):
            return None
        return int(user_id_text)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def safe_next_path(value: str | None, default: str = "/account") -> str:
    """Only allow local absolute paths, preventing open redirects."""
    if not value:
        return default
    value = value.strip()
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return default
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return default
    return value


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64] or "unknown"
    return request.client.host if request.client else "unknown"


def request_is_https(request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded.split(",")[0].strip() == "https"
