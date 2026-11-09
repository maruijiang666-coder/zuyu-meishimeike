from __future__ import annotations


def login_with_code(client, phone: str) -> dict:
    response = client.post("/api/auth/send-code", json={"phone": phone})
    assert response.status_code == 200
    payload = response.json()
    code = payload["debug_code"]
    assert len(code) == 6
    response = client.post("/api/auth/login", json={"phone": phone, "code": code})
    assert response.status_code == 200, response.text
    return response.json()["user"]


def test_login_page_and_guard(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "手机号登录" in response.text

    response = client.get("/account", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_phone_code_login_and_logout(client):
    phone = "13800001111"
    response = client.post("/api/auth/send-code", json={"phone": phone})
    assert response.status_code == 200
    code = response.json()["debug_code"]
    assert response.json()["cooldown"] == 60

    # Immediate resend is blocked by the per-phone cooldown.
    assert client.post("/api/auth/send-code", json={"phone": phone}).status_code == 429

    wrong = "111111" if code != "111111" else "222222"
    response = client.post("/api/auth/login", json={"phone": phone, "code": wrong})
    assert response.status_code == 401

    response = client.post("/api/auth/login", json={"phone": phone, "code": code})
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["phone"] == phone
    assert user["masked_phone"] == "138****1111"

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == user["id"]

    response = client.get("/account")
    assert response.status_code == 200
    assert "我的咨询" in response.text
    assert "138****1111" in response.text

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/account", follow_redirects=False).status_code == 303


def test_code_rejects_invalid_phone_and_empty_code(client):
    assert client.post("/api/auth/send-code", json={"phone": "12345"}).status_code == 400
    assert (
        client.post("/api/auth/send-code", json={"phone": "abc"}).status_code == 400
    )
    assert (
        client.post("/api/auth/login", json={"phone": "13800001112", "code": "abcdef"}).status_code
        == 400
    )


def test_logged_in_chat_links_to_account_and_admin(client, admin_headers):
    phone = "13900002222"
    user = login_with_code(client, phone)

    session_id = "auth-chat-0001"
    response = client.post("/api/chat/sessions", json={"session_id": session_id})
    assert response.status_code == 200
    response = client.post(
        f"/api/chat/sessions/{session_id}/messages",
        json={"content": "登录后咨询：想做一个企业官网"},
    )
    assert response.status_code == 200

    response = client.get("/account")
    assert "登录后咨询：想做一个企业官网" in response.text

    response = client.get("/api/admin/conversations", headers=admin_headers)
    conversation = next(
        item for item in response.json()["items"] if item["session_id"] == session_id
    )
    assert conversation["user_id"] == user["id"]
    assert conversation["contact"] == phone


def test_login_attempts_are_limited(client):
    phone = "13700003333"
    response = client.post("/api/auth/send-code", json={"phone": phone})
    code = response.json()["debug_code"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert (
            client.post("/api/auth/login", json={"phone": phone, "code": wrong}).status_code
            == 401
        )
    response = client.post("/api/auth/login", json={"phone": phone, "code": code})
    assert response.status_code == 401
    assert "次数过多" in response.json()["detail"]


def test_safe_next_is_not_open_redirect(client):
    response = client.get("/login?next=https://evil.example.com", follow_redirects=False)
    assert response.status_code == 200
    assert "evil.example.com" not in response.text
    assert 'data-next="/account"' in response.text
