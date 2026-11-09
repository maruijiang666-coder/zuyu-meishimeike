"""Tencent Cloud SMS (TC3-HMAC-SHA256) for login verification codes.

The reference implementation lives in the zuyu-app project. This module is a
trimmed, single-recipient version that never raises: callers get a structured
result and decide how to surface the failure.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.config import Settings, get_settings
from app.security import to_e164

logger = logging.getLogger(__name__)

CONTENT_TYPE = "application/json; charset=utf-8"
ALGORITHM = "TC3-HMAC-SHA256"
SERVICE = "sms"
SIGNED_HEADERS = "content-type;host;x-tc-action"
API_ACTION = "SendSms"
API_VERSION = "2021-01-11"
DEFAULT_ENDPOINT = "sms.tencentcloudapi.com"


@dataclass(frozen=True)
class SmsResult:
    ok: bool
    request_id: str = ""
    code: str = ""
    message: str = ""
    raw: dict = field(default_factory=dict)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def build_canonical_request(*, host: str, body: str, action: str = API_ACTION) -> str:
    canonical_headers = (
        f"content-type:{CONTENT_TYPE}\n"
        f"host:{host}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    return (
        f"POST\n"
        f"/\n"
        f"\n"
        f"{canonical_headers}\n"
        f"{SIGNED_HEADERS}\n"
        f"{sha256_hex(body)}"
    )


def tc3_authorization(
    *,
    secret_id: str,
    secret_key: str,
    host: str,
    body: str,
    timestamp: int,
    action: str = API_ACTION,
    service: str = SERVICE,
) -> str:
    date = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y-%m-%d")
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = (
        f"{ALGORITHM}\n"
        f"{int(timestamp)}\n"
        f"{credential_scope}\n"
        f"{sha256_hex(build_canonical_request(host=host, body=body, action=action))}"
    )
    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return (
        f"{ALGORITHM} "
        f"Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={SIGNED_HEADERS}, "
        f"Signature={signature}"
    )


class TencentSmsSender:
    def __init__(
        self,
        *,
        secret_id: str,
        secret_key: str,
        sdk_app_id: str,
        sign_name: str,
        region: str,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
        clock=lambda: time.time,
    ) -> None:
        self._secret_id = secret_id
        self._secret_key = secret_key
        self._sdk_app_id = sdk_app_id
        self._sign_name = sign_name
        self._region = region
        self._endpoint = endpoint
        self._timeout = timeout
        self._transport = transport
        self._clock = clock

    def _headers(self, body: str, timestamp: int) -> dict[str, str]:
        return {
            "Authorization": tc3_authorization(
                secret_id=self._secret_id,
                secret_key=self._secret_key,
                host=self._endpoint,
                body=body,
                timestamp=timestamp,
            ),
            "Content-Type": CONTENT_TYPE,
            "Host": self._endpoint,
            "X-TC-Action": API_ACTION,
            "X-TC-Version": API_VERSION,
            "X-TC-Timestamp": str(int(timestamp)),
            "X-TC-Region": self._region,
        }

    def send(self, phone: str, template_id: str, params: list[str] | None = None) -> SmsResult:
        payload: dict = {
            "SmsSdkAppId": self._sdk_app_id,
            "SignName": self._sign_name,
            "TemplateId": str(template_id),
            "PhoneNumberSet": [to_e164(phone)],
        }
        if params:
            payload["TemplateParamSet"] = [str(item) for item in params]

        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        timestamp = int(self._clock())
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(
                    f"https://{self._endpoint}/",
                    content=body.encode("utf-8"),
                    headers=self._headers(body, timestamp),
                )
        except httpx.HTTPError as exc:
            return SmsResult(ok=False, code="NetworkError", message=f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - SMS must never break the request
            return SmsResult(ok=False, code="ClientError", message=f"{type(exc).__name__}: {exc}")

        if response.status_code != 200:
            return SmsResult(
                ok=False,
                code=f"HTTP{response.status_code}",
                message=response.text[:300],
                raw={"statusCode": response.status_code, "body": response.text[:1000]},
            )
        try:
            data = response.json()
        except ValueError:
            return SmsResult(
                ok=False,
                code="InvalidJson",
                message=response.text[:300],
                raw={"statusCode": response.status_code, "body": response.text[:1000]},
            )
        return self._parse_response(data)

    @staticmethod
    def _parse_response(data: object) -> SmsResult:
        if not isinstance(data, dict):
            return SmsResult(ok=False, code="InvalidResponse", message="返回体不是 JSON 对象")
        response = data.get("Response")
        if not isinstance(response, dict):
            return SmsResult(ok=False, code="InvalidResponse", message="返回体缺少 Response")
        request_id = str(response.get("RequestId") or "")
        error = response.get("Error")
        if isinstance(error, dict):
            return SmsResult(
                ok=False,
                request_id=request_id,
                code=str(error.get("Code") or ""),
                message=str(error.get("Message") or ""),
                raw=data,
            )
        statuses = response.get("SendStatusSet")
        if not isinstance(statuses, list) or not statuses:
            return SmsResult(
                ok=False,
                request_id=request_id,
                code="EmptySendStatusSet",
                message="腾讯云未返回 SendStatusSet",
                raw=data,
            )
        for item in statuses:
            if not isinstance(item, dict) or item.get("Code") != "Ok":
                return SmsResult(
                    ok=False,
                    request_id=request_id,
                    code=str(item.get("Code") or "") if isinstance(item, dict) else "",
                    message=str(item.get("Message") or "") if isinstance(item, dict) else "",
                    raw=data,
                )
        return SmsResult(ok=True, request_id=request_id, code="Ok", message="send success", raw=data)


def _is_template_param_error(result: SmsResult) -> bool:
    text = f"{result.code} {result.message}".lower()
    return "template" in text and ("param" in text or "参数" in text)


def _params(settings: Settings, code: str) -> list[list[str]]:
    """Candidate parameter sets, most likely first.

    Tencent verification templates differ: some only contain {1} (the code),
    others also contain {2} (validity minutes). `SMS_TEMPLATE_PARAMS=auto`
    lets us try both without needing the console content at build time.
    """
    code_only = [str(code)]
    code_with_ttl = [str(code), str(settings.sms_code_ttl_minutes)]
    if settings.sms_template_params == "code":
        return [code_only]
    if settings.sms_template_params in {"code,ttl", "code+ttl", "code_ttl"}:
        return [code_with_ttl]
    return [code_only, code_with_ttl]


def send_login_code(phone: str, code: str) -> SmsResult:
    """Send a login verification code. Never raises."""
    settings = get_settings()
    mode = settings.sms_mode

    if mode == "mock":
        if settings.sms_debug:
            logger.warning("[SMS-MOCK] phone=%s code=%s（SMS_DEBUG=true，仅本地调试）", phone, code)
        else:
            logger.warning("[SMS-MOCK] phone=%s 短信未配置，验证码未发送（本地调试请设置 SMS_DEBUG=true）", phone)
        return SmsResult(ok=True, code="Mock", message="mock sms")
    if mode == "disabled":
        logger.error("短信发送失败：SMS_PROVIDER=tencent 但腾讯云短信配置不完整")
        return SmsResult(ok=False, code="NotConfigured", message="短信服务未配置")

    sender = TencentSmsSender(
        secret_id=settings.tencent_sms_secret_id,
        secret_key=settings.tencent_sms_secret_key,
        sdk_app_id=settings.tencent_sms_sdk_app_id,
        sign_name=settings.tencent_sms_sign_name,
        region=settings.tencent_sms_region,
        timeout=settings.tencent_sms_timeout,
    )
    candidates = _params(settings, code)
    result = SmsResult(ok=False, code="NotAttempted", message="")
    for index, params in enumerate(candidates):
        result = sender.send(phone, settings.tencent_sms_login_template_id, params)
        if result.ok:
            if index > 0:
                logger.info("短信模板 %s 使用参数组 %s 发送成功", settings.tencent_sms_login_template_id, params)
            return result
        if index == 0 and len(candidates) > 1 and _is_template_param_error(result):
            logger.warning(
                "短信模板 %s 参数不匹配（%s），自动重试带有效期的参数组",
                settings.tencent_sms_login_template_id,
                result.code,
            )
            continue
        break
    logger.warning("短信发送失败：%s %s", result.code, result.message)
    return result
