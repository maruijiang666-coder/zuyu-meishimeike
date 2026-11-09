import os
import tempfile

# Configure the app before importing it. The config module caches settings on
# first import, so these must be set at collection time.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="meike-test-")
os.environ["ADMIN_PASSWORD"] = "test-password-123"
os.environ["CHAT_AUTO_REPLY"] = "true"

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
