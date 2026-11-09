"""Send one real login-code SMS, to verify Tencent credentials/template.

Usage (from the project root, with .env configured):
    .\\.venv\\Scripts\\python.exe scripts\\send_test_sms.py --to 13800001234

The code is a test value and is NOT stored in the database, so it cannot be
used to log in. This script only validates signature, signature name, template
and phone number formatting against Tencent Cloud.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.security import normalize_phone  # noqa: E402
from app.sms import send_login_code  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="发送一条腾讯云登录验证码测试短信")
    parser.add_argument("--to", required=True, help="接收短信的手机号，如 13800001234")
    parser.add_argument("--code", default="123456", help="测试验证码（默认 123456）")
    args = parser.parse_args()

    settings = get_settings()
    phone = normalize_phone(args.to)
    if not phone:
        print("号码不合法：需要中国大陆 11 位手机号，1[3-9] 开头")
        return 2
    print(
        f"短信模式={settings.sms_mode} 模板={settings.tencent_sms_login_template_id} "
        f"参数模式={settings.sms_template_params}"
    )
    result = send_login_code(phone, args.code)
    print(json.dumps({"ok": result.ok, "code": result.code,
                      "message": result.message, "request_id": result.request_id},
                     ensure_ascii=False, indent=2))
    if result.raw:
        print(json.dumps(result.raw, ensure_ascii=False, indent=2, default=str)[:2000])
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
