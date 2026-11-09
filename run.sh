#!/usr/bin/env bash
# 美刻科技官网 · Linux / macOS 本地启动脚本
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已创建 .env（默认管理密码 meike2026，请按需修改）"
fi

if [ ! -d .venv ]; then
  echo "创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi

. .venv/bin/activate
pip install --disable-pip-version-check -q -r requirements.txt
echo "启动服务：http://127.0.0.1:8700  （管理端 /admin）"
exec python -m app.main
