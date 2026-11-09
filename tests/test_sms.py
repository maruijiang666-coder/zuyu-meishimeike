import json

import httpx

from app.sms import (
    TencentSmsSender,
    build_canonical_request,
    send_login_code,
    sha256_hex,
)


def test_canonical_request_matches_official_document_example():
    payload = (
        '{"Limit": 1, "Filters": [{"Values": ["\\u672a\\u547d\\u540d"], '
        '"Name": "instance-name"}]}'
    )
    canonical = build_canonical_request(
        host="cvm.tencentcloudapi.com", body=payload, action="DescribeInstances"
    )
    assert sha256_hex(payload) == "35e9c5b0e3ae67532d3c9f17ead6c90222632e5b1ff7f6e89887f1398934f064"
    assert sha256_hex(canonical) == "7019a55be8395899b900fb5564e4200d984910f34794a27cb3fb7d10ff6a1e84"


def test_tencent_sender_builds_login_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        captured["headers"] = request.headers
        return httpx.Response(
            200,
            json={
                "Response": {
                    "SendStatusSet": [{"Code": "Ok", "Message": "send success"}],
                    "RequestId": "req-login-ok",
                }
            },
        )

    sender = TencentSmsSender(
        secret_id="AKIDtest",
        secret_key="test-key",
        sdk_app_id="1401204550",
        sign_name="云南美刻网络科技",
        region="ap-guangzhou",
        transport=httpx.MockTransport(handler),
        clock=lambda: 1700000000,
    )
    result = sender.send("13238689505", "2744631", ["123456"])
    assert result.ok is True
    assert result.request_id == "req-login-ok"
    assert captured["payload"] == {
        "SmsSdkAppId": "1401204550",
        "SignName": "云南美刻网络科技",
        "TemplateId": "2744631",
        "PhoneNumberSet": ["+8613238689505"],
        "TemplateParamSet": ["123456"],
    }
    assert captured["headers"]["X-TC-Action"] == "SendSms"
    assert captured["headers"]["X-TC-Timestamp"] == "1700000000"


def test_mock_provider_sends_without_network():
    # tests/conftest.py sets SMS_PROVIDER=mock
    result = send_login_code("13800009999", "123456")
    assert result.ok is True
    assert result.code == "Mock"
