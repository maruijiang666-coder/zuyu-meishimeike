from __future__ import annotations


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "云南美刻网络科技有限公司" in html
    assert "微信小程序开发" in html
    assert "在线咨询" in html
    assert response.headers["content-security-policy"].startswith("default-src 'self'")


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_conversation_flow(client, admin_headers):
    session = "pytest-session-0001"
    response = client.post("/api/chat/sessions", json={"session_id": session})
    assert response.status_code == 200
    assert response.json()["session_id"] == session

    response = client.post(
        f"/api/chat/sessions/{session}/messages",
        json={"content": "你好，我想做一个预约小程序"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]["role"] == "visitor"
    assert "小程序" in payload["reply"]["content"]

    response = client.get(f"/api/chat/sessions/{session}/messages")
    messages = response.json()["messages"]
    assert [message["role"] for message in messages] == ["visitor", "bot"]

    response = client.post(
        f"/api/chat/sessions/{session}/contact",
        json={"name": "王先生", "contact": "13800000000"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    response = client.get("/api/admin/conversations", headers=admin_headers)
    items = response.json()["items"]
    conversation = next(item for item in items if item["session_id"] == session)
    assert conversation["contact"] == "13800000000"
    assert conversation["unread_admin"] >= 1
    # Saving a contact must not replace the chat preview with the phone number.
    assert "小程序" in conversation["last_message"]

    response = client.post(
        f"/api/admin/conversations/{session}/messages",
        headers=admin_headers,
        json={"content": "你好，方便留个电话详细聊聊吗？"},
    )
    assert response.status_code == 200
    assert response.json()["message"]["role"] == "admin"

    response = client.get(f"/api/chat/sessions/{session}/messages")
    roles = [message["role"] for message in response.json()["messages"]]
    assert "admin" in roles

    # Once a human has replied, the keyword bot stops talking.
    response = client.post(
        f"/api/chat/sessions/{session}/messages",
        json={"content": "这个大概要多少钱？"},
    )
    assert response.status_code == 200
    assert response.json()["reply"] is None


def test_admin_requires_auth(client):
    assert client.get("/api/admin/conversations").status_code == 401
    assert (
        client.post("/api/admin/login", json={"password": "wrong-password"}).status_code == 401
    )

    response = client.post("/api/admin/login", json={"password": "test-password-123"})
    assert response.status_code == 200
    token = response.json()["token"]
    assert len(token) == 64

    response = client.get(
        "/api/admin/overview", headers={"X-Admin-Token": token}
    )
    assert response.status_code == 200
    assert set(response.json()) >= {"total", "today", "leads", "unread"}


def test_lead_form_creates_conversation(client, admin_headers):
    response = client.post(
        "/api/leads",
        json={
            "name": "李女士",
            "contact": "wx_li_nvshi",
            "requirement": "想做一个企业官网，带后台",
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    assert session_id.startswith("form-")

    response = client.get("/api/admin/conversations", headers=admin_headers)
    conversation = next(
        item for item in response.json()["items"] if item["session_id"] == session_id
    )
    assert conversation["source"] == "form"
    assert conversation["contact"] == "wx_li_nvshi"


def test_message_validation(client):
    session = "pytest-session-0002"
    client.post("/api/chat/sessions", json={"session_id": session})
    assert (
        client.post(f"/api/chat/sessions/{session}/messages", json={"content": "   "}).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/chat/sessions/{session}/messages", json={"content": "x" * 1001}
        ).status_code
        == 422
    )


def test_export_csv(client, admin_headers):
    client.post(
        "/api/leads",
        json={"name": "张先生", "contact": "13900000000", "requirement": "小程序商城"},
    )
    response = client.get("/api/admin/export.csv", headers=admin_headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    assert "\ufeff" in response.text
    assert "联系方式" in response.text
