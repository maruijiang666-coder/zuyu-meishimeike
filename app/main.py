"""FastAPI entry point for the Meike company site."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import content
from app.auth import get_current_user
from app.config import WEB_DIR, get_settings
from app.db import close_pool, get_conn, init_db
from app.routers import admin, auth, public
from app.security import safe_next_path
from app.user_repo import list_user_conversations

settings = get_settings()
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.database_url and not settings.pg_password:
        raise RuntimeError(
            "PostgreSQL 未配置：请在 .env 设置 PG_PASSWORD（或 DATABASE_URL），"
            "不要使用 SQLite"
        )
    init_db()
    logger.info(
        "PostgreSQL: host=%s port=%s db=%s",
        settings.pg_host,
        settings.pg_port,
        settings.pg_db,
    )
    if settings.sms_debug:
        logger.warning("SMS_DEBUG=true：验证码会出现在发送接口响应中，生产环境必须关闭")
    if settings.sms_mode == "disabled":
        logger.error("短信服务未配置：请设置 TENCENT_SMS_SECRET_ID / TENCENT_SMS_SECRET_KEY")
    elif settings.sms_mode == "mock":
        logger.warning("短信运行在本地 mock 模式：不会真实发送，验证码见服务端日志")
    yield
    close_pool()


app = FastAPI(
    title="美刻科技 · 公司主页",
    description="云南美刻网络科技有限公司官网与在线咨询",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(GZipMiddleware, minimum_size=600)

CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self'; "
    "script-src 'self'; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'self'"
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Content-Security-Policy", CSP)

    path = request.url.path
    if path.startswith("/static/"):
        response.headers.setdefault("Cache-Control", "public, max-age=3600")
    elif path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    elif path in {"/admin", "/admin/"}:
        response.headers.setdefault("Cache-Control", "no-store")
    elif path in {"/login", "/account"}:
        response.headers.setdefault("Cache-Control", "no-store")
    else:
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
app.include_router(public.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


def _local_label(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo(settings.timezone)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, KeyError):
        return value


def _base_context(request: Request) -> dict:
    return {
        "settings": settings,
        "user": get_current_user(request),
        "company": {
            "name": settings.company_name,
            "short": settings.company_short,
            "en": settings.company_en,
            "slogan": settings.slogan,
            "service_area": settings.service_area,
            "phone": settings.phone,
            "wechat": settings.wechat,
            "email": settings.email,
            "address": settings.address,
            "icp": settings.icp,
        },
        "contact_channels": settings.contact_channels,
        "year": datetime.now().year,
        "request": request,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    context = _base_context(request)
    context.update(
        {
            "nav": content.NAV_ITEMS,
            "hero": content.HERO,
            "stats": content.STATS,
            "services": content.SERVICES,
            "service_note": content.SERVICE_NOTE,
            "advantages": content.ADVANTAGES,
            "project_card": content.PROJECT_CARD,
            "process": content.PROCESS,
            "faq": content.FAQ,
            "contact": content.CONTACT,
            "footer_note": content.FOOTER_NOTE,
            "tagline": content.COMPANY_TAGLINE,
        }
    )
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request, name="admin.html", context=_base_context(request)
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = Query(default="/account")) -> Response:
    target = safe_next_path(next)
    if get_current_user(request) is not None:
        return RedirectResponse(url=target, status_code=303)
    context = _base_context(request)
    context.update({"next": target, "sms_debug": settings.sms_debug})
    return templates.TemplateResponse(request=request, name="login.html", context=context)


@app.get("/account", response_class=HTMLResponse)
def account_page(request: Request) -> Response:
    user = get_current_user(request)
    if user is None:
        return RedirectResponse(url="/login?next=/account", status_code=303)

    with get_conn() as conn:
        conversations = list_user_conversations(conn, int(user["id"]))

    for item in conversations:
        item["updated_label"] = _local_label(item["updated_at"])
        item["source_label"] = "官网表单" if item["source"] == "form" else "在线咨询"
        item["preview"] = item["last_message"] or "开始咨询"

    context = _base_context(request)
    context.update(
        {
            "user": user,
            "conversations": conversations,
            "user_since": _local_label(user["created_at"]),
        }
    )
    return templates.TemplateResponse(request=request, name="account.html", context=context)


@app.get("/favicon.ico")
def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/img/favicon.svg", status_code=307)


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    return PlainTextResponse(
        "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin\nDisallow: /account\nDisallow: /login\n"
    )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - convenience for `python -m app.main`
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)
