# 美刻科技 · 公司官网与在线咨询

云南美刻网络科技有限公司的官方业务介绍页，面向**微信服务号内打开的 H5** 场景。
单页展示技术服务（微信小程序 / 企业网站 / 安卓 App / 数字化系统），核心目标是让访客
**发起在线咨询、留下联系方式**，不接微信支付，不做完整的商城订单流程。

后端使用 **FastAPI**，前端为原生 HTML / CSS / JavaScript，数据落在 **SQLite**，无前端构建步骤。

![官网首页](docs/screenshots/home-desktop.png)

## 功能

- **公司主页**：首屏品牌展示、4 项服务方案、选择理由、合作流程、常见问题、联系表单、页脚。
- **在线咨询窗口**：右下角悬浮入口，支持快捷问题、关键词自动回复、会话持久化（刷新不丢）、
  人工接管（客服回复后机器人自动静默）、未读提醒、留电话 / 微信。
- **留资表单**：姓名、手机号 / 微信号、需求描述，直接进入客服后台；带蜜罐字段和频率限制。
- **客服管理后台** `/admin`：密码登录、会话列表、未读消息、搜索、实时回复（8 秒轮询）、
  链路来源区分（在线咨询 / 官网表单）、导出 CSV。
- **移动端优先**：适配微信内置浏览器、iPhone 安全区、iOS 输入框缩放、全屏聊天。
- **安全基础**：CSP、X-Frame-Options、参数校验、SQL 参数化、输出转义、IP 限流、
  管理端登录限流、无第三方 CDN 依赖。

| 手机端首页 | 在线咨询 |
| --- | --- |
| ![手机端](docs/screenshots/home-mobile.png) | ![在线咨询](docs/screenshots/chat.png) |

![客服管理后台](docs/screenshots/admin.png)

## 技术栈

- Python 3.11+ / FastAPI 0.115 / Uvicorn
- Jinja2 服务端渲染（SEO 友好，首屏无白屏）
- SQLite（WAL 模式，零外部依赖）
- 原生 HTML / CSS / JS（无 npm、无构建）
- Docker + Nginx（HTTPS 反向代理）

## 目录结构

```text
meishi-app/
├─ app/
│  ├─ main.py              # FastAPI 入口、页面路由、安全响应头
│  ├─ config.py            # 环境变量 / .env 配置
│  ├─ content.py           # 官网文案：服务、优势、流程、FAQ
│  ├─ chatbot.py           # 关键词自动回复
│  ├─ db.py                # SQLite 连接与建表
│  ├─ repository.py        # 会话 / 消息 / 线索数据访问
│  ├─ schemas.py           # Pydantic 请求模型
│  ├─ ratelimit.py         # 进程内滑动窗口限流
│  └─ routers/
│     ├─ public.py         # 健康检查、咨询会话、留资
│     └─ admin.py          # 登录、会话、回复、CSV 导出
├─ web/
│  ├─ templates/
│  │  ├─ index.html        # 公司主页
│  │  └─ admin.html        # 客服后台
│  └─ static/
│     ├─ css/style.css
│     ├─ css/admin.css
│     ├─ js/app.js
│     ├─ js/admin.js
│     └─ img/favicon.svg
├─ tests/                  # pytest 接口测试
├─ deploy/                 # Nginx / systemd 示例
├─ data/                   # SQLite 数据（已 gitignore）
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ .env.example
├─ run.ps1
└─ run.sh
```

## 本地运行

要求：Python 3.11+（3.12 / 3.13 均可），无需 Node.js。

### Windows

```powershell
.\run.ps1
```

### macOS / Linux

```bash
chmod +x run.sh
./run.sh
```

脚本会自动创建 `.env`、虚拟环境并安装依赖，然后启动在 **8700** 端口。

也可以手动启动：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

打开：

- 公司主页：<http://127.0.0.1:8700/>
- 客服后台：<http://127.0.0.1:8700/admin>
- 直接打开咨询窗口：<http://127.0.0.1:8700/?chat=1>

> 默认管理密码是 `meike2026`。**部署到公网前必须修改 `.env` 中的 `ADMIN_PASSWORD`。**

## 配置

配置读取顺序：系统环境变量 > 项目根目录 `.env` > 代码默认值。修改 `.env` 后重启服务生效。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_PORT` | `8700` | 本地启动端口（Docker 中为宿主机映射端口） |
| `APP_TIMEZONE` | `Asia/Shanghai` | 后台“今日”统计与导出时间使用的时区 |
| `ADMIN_PASSWORD` | `meike2026` | 管理后台密码，上线前务必修改 |
| `DATA_DIR` | `data` | SQLite 数据目录，Docker 中固定为 `/app/data` |
| `CHAT_AUTO_REPLY` | `true` | 是否启用关键词自动回复 |
| `MESSAGE_RATE_LIMIT` | `20` | 单 IP 每分钟聊天消息上限 |
| `COMPANY_NAME` | 云南美刻网络科技有限公司 | 公司全称 |
| `COMPANY_SHORT` | 美刻科技 | 品牌短名 |
| `COMPANY_EN` | MEIKE TECH | 英文标识 |
| `COMPANY_SLOGAN` | 把好想法，做成好产品 | 品牌语 |
| `COMPANY_SERVICE_AREA` | 云南 | 服务区域，显示在联系区 / 页脚 |
| `COMPANY_PHONE` | 空 | 电话；填写后显示在联系区，可点击拨打 |
| `COMPANY_WECHAT` | 空 | 微信号；填写后显示 |
| `COMPANY_EMAIL` | 空 | 邮箱；填写后显示 |
| `COMPANY_ADDRESS` | 空 | 地址；填写后显示 |
| `COMPANY_ICP` | 空 | ICP 备案号；备案后填写并链接工信部 |
| `SITE_URL` | 空 | 线上域名（用于 canonical / og:url） |

联系方式留空时，页面只展示“在线咨询 / 服务范围”，不会出现空号码。

## 管理后台

1. 访问 `/admin`，输入 `ADMIN_PASSWORD` 登录。
2. 左侧是会话列表：显示称呼、联系方式、最后一条消息、未读数，支持搜索。
3. 点击会话查看完整对话；访客发来的消息会实时出现（8 秒轮询），未读自动清零。
4. 在底部输入回复，访客聊天窗口会在 3.5 秒内收到（轮询）。
5. “导出 CSV” 导出全部会话和联系方式，Excel 可直接打开（带 UTF-8 BOM）。
6. 后台登录态保存在当前浏览器标签页的 `sessionStorage`，关闭标签页即退出。

管理接口使用 `X-Admin-Token` 请求头校验，Token 由密码派生；修改密码后旧 Token 立即失效。

## 接入微信服务号

1. **域名与 HTTPS**：微信内置浏览器要求网页可正常访问，生产环境请使用**已完成 ICP 备案的域名 + HTTPS**。
   不要用 IP、HTTP 或未备案域名。
2. **自定义菜单**：在公众号后台「自定义菜单」添加“跳转网页”，地址填
   `https://你的域名/?chat=1`（打开即弹出咨询窗口）或 `https://你的域名/`（先看主页）。
3. **JS 接口安全域名**：当前页面没有接入微信 JS-SDK（不需要自定义分享、拍照、定位等能力），
   因此不强制配置。后续若要做自定义分享卡片，再在公众号后台配置「JS 接口安全域名」并接入签名接口。
4. **不需要微信支付**：本项目没有支付、下单、退款相关逻辑。
5. **手机端验证**：上线后分别在 iOS 微信、安卓微信中检查首屏、咨询窗口、表单键盘和安全区。

## 部署

### 方式一：Docker Compose（推荐）

```bash
cp .env.example .env
# 编辑 .env：至少修改 ADMIN_PASSWORD
docker compose up -d --build
```

- 容器内监听 `8700`，宿主机默认只映射到 `127.0.0.1:8700`，由 Nginx 对外提供 HTTPS。
- 数据目录 `./data` 挂载到容器 `/app/data`，重建容器不会丢数据。
- 如需直接对外暴露端口，把 `docker-compose.yml` 中的
  `"127.0.0.1:${APP_PORT:-8700}:8700"` 改为 `"${APP_PORT:-8700}:8700"`。

### 方式二：systemd + 虚拟环境

参考 `deploy/meike-site.service`，把代码放到 `/opt/meike-site`，创建 `.venv` 后：

```bash
sudo cp deploy/meike-site.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now meike-site
```

### Nginx + HTTPS

参考 `deploy/nginx.conf.example`：

- 80 端口跳转 443，`/.well-known/acme-challenge/` 留给 certbot；
- 443 反向代理到 `127.0.0.1:8700`；
- 传递 `X-Forwarded-For` / `X-Forwarded-Proto`；
- 静态资源单独缓存 1 小时。

首次签发证书示例：

```bash
sudo certbot --nginx -d meike.example.com
```

### 端口说明

本项目默认端口是 **8700**，与原 zuyu 项目的 `8600` / `8080` / `8081` 均不冲突。
本地开发、Docker 宿主机映射、Nginx upstream 都使用 8700；如需修改，只改 `APP_PORT`（本地）
或 compose 端口映射，不要改动原项目配置。

## 数据与备份

- 数据库文件：`data/meike.db`（SQLite，WAL 模式，另有 `-wal` / `-shm` 临时文件）。
- 表：`conversations`（会话 / 联系方式 / 未读数）、`messages`（访客、机器人、客服消息）。
- 备份：停止写入或直接复制 `data/` 目录即可；恢复时替换整个目录。
- 本项目不提供删除会话的界面，避免误删线索；如需清理测试数据，可在维护窗口操作数据库。
- 聊天内容会原样保存，用于客服跟进。建议在隐私政策中说明用途，不要用于群发营销。

## API 摘要

公开接口（无需登录）：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/chat/sessions` | 创建 / 复用会话（`session_id` 可选） |
| GET | `/api/chat/sessions/{id}/messages?after_id=0` | 拉取消息（同时清除访客未读） |
| POST | `/api/chat/sessions/{id}/messages` | 发送访客消息，返回机器人回复 |
| GET | `/api/chat/sessions/{id}/unread` | 未读客服消息数 |
| POST | `/api/chat/sessions/{id}/contact` | 保存称呼 + 手机号 / 微信 |
| POST | `/api/leads` | 联系表单留资 |

管理接口（需要 `X-Admin-Token`）：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/admin/login` | 密码登录，返回 token |
| GET | `/api/admin/me` | 校验登录态 |
| GET | `/api/admin/overview` | 今日 / 全部 / 留资 / 未读统计 |
| GET | `/api/admin/conversations?q=` | 会话列表与搜索 |
| GET | `/api/admin/conversations/{id}` | 会话详情（自动标记已读） |
| POST | `/api/admin/conversations/{id}/messages` | 客服回复 |
| POST | `/api/admin/conversations/{id}/read` | 标记已读 |
| GET | `/api/admin/export.csv` | 导出 CSV |

公开接口均有 IP 限流；被限流时返回 `429`。

## 测试

```bash
pip install -r requirements-dev.txt
pytest -q
```

覆盖：主页渲染 / 安全响应头、健康检查、完整咨询链路、机器人静默、留资、管理端鉴权、
消息校验、CSV 导出。测试使用临时数据目录，不会污染 `data/`。

## 上线检查清单

- [ ] 修改 `ADMIN_PASSWORD`，不要使用默认密码
- [ ] 配置已备案域名 + HTTPS 证书
- [ ] 填写 `COMPANY_PHONE` / `COMPANY_WECHAT` / `COMPANY_EMAIL` / `COMPANY_ICP`
- [ ] 确认 `data/` 目录可写、已纳入备份
- [ ] 用手机微信打开首页、发消息、留联系方式、后台回复各走一遍
- [ ] 检查公众号菜单链接为 `https://域名/?chat=1`
- [ ] 不对外暴露 8700 端口（只允许 Nginx 访问）
- [ ] 定期查看后台未读，及时回复

## 版权

© 云南美刻网络科技有限公司。本项目为内部业务系统，未授权请勿转载或商用。
