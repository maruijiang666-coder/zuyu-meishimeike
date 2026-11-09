#!/usr/bin/env bash
# 美刻科技官网 · Linux / macOS 本地启动脚本
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已创建 .env（请填写 PG_PASSWORD 等配置）"
fi

if grep -Eq '^PG_PASSWORD=[[:space:]]*$' .env && ! grep -Eq '^DATABASE_URL=[^[:space:]]+' .env; then
  echo "请先在 .env 填写 PG_PASSWORD（或 DATABASE_URL），本项目不使用 SQLite。" >&2
  echo "本地连服务器 PG 需要先开 SSH 隧道，见 README 的「数据库（PostgreSQL）」。" >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi

. .venv/bin/activate
pip install --disable-pip-version-check -q -r requirements.txt
echo "启动服务：http://127.0.0.1:8700  （管理端 /admin，登录 /login）"
exec python -m app.main
