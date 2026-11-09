"""FastAPI entry point for the Meike company site."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import content
from app.config import WEB_DIR, get_settings
from app.db import init_db
from app.routers import admin, public

settings = get_settings()

templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


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
    else:
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
app.include_router(public.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


def _base_context(request: Request) -> dict:
    return {
        "settings": settings,
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


@app.get("/favicon.ico")
def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/img/favicon.svg", status_code=307)


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin\n")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover - convenience for `python -m app.main`
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)
