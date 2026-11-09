"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

load_dotenv(BASE_DIR / ".env", override=False)


def _text(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def _flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    company_name: str = _text("COMPANY_NAME", "云南美刻网络科技有限公司")
    company_short: str = _text("COMPANY_SHORT", "美刻科技")
    company_en: str = _text("COMPANY_EN", "MEIKE TECH")
    slogan: str = _text("COMPANY_SLOGAN", "把好想法，做成好产品")
    service_area: str = _text("COMPANY_SERVICE_AREA", "云南")
    phone: str = _text("COMPANY_PHONE")
    wechat: str = _text("COMPANY_WECHAT")
    email: str = _text("COMPANY_EMAIL")
    address: str = _text("COMPANY_ADDRESS")
    icp: str = _text("COMPANY_ICP")
    site_url: str = _text("SITE_URL")

    port: int = int(_text("APP_PORT", "8700"))
    timezone: str = _text("APP_TIMEZONE", "Asia/Shanghai")
    #: PostgreSQL（复用服务器上已有的 PG 服务，只使用独立的新库）
    database_url: str = _text("DATABASE_URL")
    pg_host: str = _text("PG_HOST", "host.docker.internal")
    pg_port: int = int(_text("PG_PORT", "5432"))
    pg_user: str = _text("PG_USER", "quant")
    pg_password: str = _text("PG_PASSWORD")
    pg_db: str = _text("PG_DB", "meishi_app")
    admin_password: str = _text("ADMIN_PASSWORD", "meike2026")
    chat_auto_reply: bool = _flag("CHAT_AUTO_REPLY", True)
    message_rate_limit: int = int(_text("MESSAGE_RATE_LIMIT", "20"))

    # ---- 用户手机号登录 / 腾讯云短信 ----
    user_session_days: int = int(_text("USER_SESSION_DAYS", "30"))
    user_session_secret: str = _text("USER_SESSION_SECRET")
    sms_provider: str = _text("SMS_PROVIDER", "auto").lower()
    sms_debug: bool = _flag("SMS_DEBUG", False)
    sms_code_ttl_seconds: int = int(_text("SMS_CODE_TTL_SECONDS", "300"))
    #: auto = 先按「只传验证码」发送，模板参数不匹配时再尝试「验证码 + 有效分钟数」
    sms_template_params: str = _text("SMS_TEMPLATE_PARAMS", "auto").lower()
    tencent_sms_secret_id: str = _text("TENCENT_SMS_SECRET_ID")
    tencent_sms_secret_key: str = _text("TENCENT_SMS_SECRET_KEY")
    tencent_sms_sdk_app_id: str = _text("TENCENT_SMS_SDK_APP_ID", "1401204550")
    tencent_sms_sign_name: str = _text("TENCENT_SMS_SIGN_NAME", "云南美刻网络科技")
    tencent_sms_login_template_id: str = _text("TENCENT_SMS_LOGIN_TEMPLATE_ID", "2744631")
    tencent_sms_region: str = _text("TENCENT_SMS_REGION", "ap-guangzhou")
    tencent_sms_timeout: float = float(_text("TENCENT_SMS_TIMEOUT", "5"))

    @property
    def sms_configured(self) -> bool:
        return bool(
            self.tencent_sms_secret_id
            and self.tencent_sms_secret_key
            and self.tencent_sms_sdk_app_id
            and self.tencent_sms_sign_name
            and self.tencent_sms_login_template_id
        )

    @property
    def sms_mode(self) -> str:
        """tencent / mock / disabled.

        `auto` only falls back to mock in explicit local-debug mode. Without
        credentials in production it must fail loudly instead of pretending a
        code was sent.
        """
        if self.sms_provider == "mock":
            return "mock"
        if self.sms_provider == "tencent":
            return "tencent" if self.sms_configured else "disabled"
        if self.sms_configured:
            return "tencent"
        return "mock" if self.sms_debug else "disabled"

    @property
    def session_secret(self) -> str:
        """用户登录态签名密钥；未单独配置时由管理密码派生（改密码会踢下线）。"""
        return self.user_session_secret or hashlib.sha256(
            f"meike-user-session::{self.admin_password}".encode("utf-8")
        ).hexdigest()

    @property
    def sms_code_ttl_minutes(self) -> int:
        return max(1, self.sms_code_ttl_seconds // 60)

    @property
    def admin_token(self) -> str:
        """Stateless admin token derived from the password."""
        return hashlib.sha256(f"meike-admin::{self.admin_password}".encode()).hexdigest()

    @property
    def contact_channels(self) -> list[dict[str, str]]:
        channels: list[dict[str, str]] = []
        if self.phone:
            channels.append({"label": "电话", "value": self.phone, "href": f"tel:{self.phone}"})
        if self.wechat:
            channels.append({"label": "微信", "value": self.wechat, "href": ""})
        if self.email:
            channels.append({"label": "邮箱", "value": self.email, "href": f"mailto:{self.email}"})
        if self.address:
            channels.append({"label": "地址", "value": self.address, "href": ""})
        return channels


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
