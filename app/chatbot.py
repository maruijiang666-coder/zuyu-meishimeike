"""Keyword based first-line replies for the consultation widget.

The bot only handles the very first exchange; once a human replies from the
admin console it steps aside and every visitor message goes to the inbox.
"""

from __future__ import annotations

import re

from app.config import get_settings


def _contact_reply() -> str:
    settings = get_settings()
    parts: list[str] = []
    if settings.phone:
        parts.append(f"电话 {settings.phone}")
    if settings.wechat:
        parts.append(f"微信 {settings.wechat}")
    if parts:
        return "可以直接联系：" + "，".join(parts) + "。也可以把手机号或微信号留在聊天框下方，顾问会尽快联系你。"
    return "可以点聊天框下方的「留个联系方式」，把手机号或微信号留一下，顾问会尽快联系你。"


def _greeting() -> str:
    settings = get_settings()
    return (
        f"你好，这里是{settings.company_short}（{settings.company_name}）。"
        "我们做微信小程序、企业网站和安卓 App 定制开发。你想了解哪一块？"
    )


RULES: list[tuple[str, str]] = [
    (
        r"价格|报价|多少钱|费用|预算|收费|便宜",
        "具体费用要看功能范围，不同做法差别会比较大。你可以先说说想解决什么问题、"
        "大概需要哪些功能，我帮你判断一个合理的区间，再让顾问给你详细方案。",
    ),
    (
        r"小程序",
        "小程序是我们做得比较多的方向：商城、预约、会员、工具类都可以做。"
        "你这边是哪个行业，想实现什么功能？我可以先帮你梳理需要哪些页面和接口。",
    ),
    (
        r"网站|网页|官网|h5|落地页|web",
        "网站方面我们做企业官网、品牌展示页和活动 H5，会一起考虑手机端体验和内容维护后台。"
        "你是想先做一个展示官网，还是需要带业务功能的后台系统？",
    ),
    (
        r"app|安卓|android|应用|上架",
        "安卓 App 我们支持原生和跨平台两种方案，会一起评估开发成本和后续更新成本。"
        "方便说下 App 主要给谁用、核心功能是什么吗？",
    ),
    (
        r"系统|预约|进销存|crm|后台|看板|管理",
        "业务系统这块我们做过预约、进销存、CRM 和数据看板类需求。"
        "你可以先描述一下现在的流程，我帮你看看哪些环节适合系统化。",
    ),
    (
        r"周期|多久|时间|排期|几天|几个月",
        "周期和功能范围直接相关：展示型官网一般 1–2 周，小程序通常 3–6 周，"
        "复杂系统按模块排期。你把需求发我，我可以先给一个大致的时间表。",
    ),
    (
        r"维护|售后|bug|上线后|保修",
        "上线后我们有维护期，负责缺陷修复和必要适配，源码和部署文档也会一并交付。"
        "后续想自己维护或者继续交给我们都可以。",
    ),
    (
        r"案例|作品|做过|经验",
        "案例和方案可以发你参考。方便留一个手机号或微信号吗？我让顾问把相关的整理给你。",
    ),
    (
        r"电话|微信|联系|怎么联系|联系方式",
        _contact_reply(),
    ),
    (
        r"你好|您好|在吗|咨询|了解一下|想了解|hello|hi",
        _greeting(),
    ),
]

DEFAULT_REPLY = (
    "收到，我先记下来了。方便的话可以留一下手机号或微信号，顾问看到后会第一时间联系你；"
    "也可以继续在这里说说具体需求，我帮你一起梳理。"
)


def auto_reply(message: str) -> str | None:
    settings = get_settings()
    if not settings.chat_auto_reply:
        return None
    text = message.strip()
    if not text:
        return None
    if len(text) <= 12 and re.fullmatch(r"[你您好在吗\s，。,.!?！？~～]+", text):
        return _greeting()
    for pattern, reply in RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return reply
    return DEFAULT_REPLY
