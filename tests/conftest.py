import os

# Configure the app before importing it. The config module caches settings on
# first import, so these must be set at collection time.
# Tests use a dedicated local PostgreSQL database (never the production DB).
os.environ["PG_HOST"] = os.environ.get("TEST_PG_HOST", "127.0.0.1")
os.environ["PG_PORT"] = os.environ.get("TEST_PG_PORT", "55440")
os.environ["PG_USER"] = os.environ.get("TEST_PG_USER", "meishi")
os.environ["PG_PASSWORD"] = os.environ.get("TEST_PG_PASSWORD", "meishi-test-pass")
os.environ["PG_DB"] = os.environ.get("TEST_PG_DB", "meishi_test")
os.environ["ADMIN_PASSWORD"] = "test-password-123"
os.environ["CHAT_AUTO_REPLY"] = "true"
os.environ["SMS_PROVIDER"] = "mock"
os.environ["SMS_DEBUG"] = "true"
os.environ["USER_SESSION_SECRET"] = "test-user-session-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import reset_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    reset_db()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers(client):
    response = client.post("/api/admin/login", json={"password": "test-password-123"})
    assert response.status_code == 200
    return {"X-Admin-Token": response.json()["token"]}
