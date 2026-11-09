"""Application settings, loaded from environment variables / .env."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
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
    data_dir: Path = field(default_factory=lambda: Path(_text("DATA_DIR", str(BASE_DIR / "data"))))
    admin_password: str = _text("ADMIN_PASSWORD", "meike2026")
    chat_auto_reply: bool = _flag("CHAT_AUTO_REPLY", True)
    message_rate_limit: int = int(_text("MESSAGE_RATE_LIMIT", "20"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "meike.db"

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
