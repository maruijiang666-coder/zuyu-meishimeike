# 美刻科技官网 · Windows 本地启动脚本
# 用法：右键“使用 PowerShell 运行”，或在终端执行 .\run.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "已根据 .env.example 创建 .env" -ForegroundColor Yellow
}

$envText = Get-Content ".env" -Raw
if ($envText -match '(?m)^PG_PASSWORD=\s*$' -and $envText -notmatch '(?m)^DATABASE_URL=\S+') {
    Write-Host "请先在 .env 填写 PG_PASSWORD（或 DATABASE_URL），本项目不使用 SQLite。" -ForegroundColor Red
    Write-Host "本地连服务器 PG 需要先开 SSH 隧道，见 README 的「数据库（PostgreSQL）」。" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "创建虚拟环境 .venv ..." -ForegroundColor Cyan
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
Write-Host "启动服务：http://127.0.0.1:8700  （管理端 /admin，登录 /login）" -ForegroundColor Green

& ".\.venv\Scripts\python.exe" -m app.main
