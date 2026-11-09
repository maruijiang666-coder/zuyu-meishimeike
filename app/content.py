"""All marketing copy for the one-page company site.

Keeping the copy in Python makes it easy to update products and FAQ items
without touching HTML, and lets us render the page server-side (good for
WeChat's in-app browser and for SEO).
"""

from __future__ import annotations

COMPANY_TAGLINE = "扎根云南的技术开发团队"

NAV_ITEMS = [
    {"id": "services", "label": "服务方案"},
    {"id": "advantages", "label": "我们的优势"},
    {"id": "process", "label": "合作流程"},
    {"id": "faq", "label": "常见问题"},
]

HERO = {
    "eyebrow": "云南美刻网络科技有限公司",
    "title_a": "把想法，做成",
    "title_b": "真正好用的产品",
    "description": (
        "我们是一支扎根云南的技术团队，专注微信小程序、企业网站与安卓 App "
        "定制开发。从需求梳理、设计开发到上线维护，一个团队跟到底。"
    ),
    "primary_cta": "免费咨询方案",
    "secondary_cta": "看看我们能做什么",
    "trust": ["源码交付", "合同保障", "上线后维护"],
}

STATS = [
    {"value": "1 个工作日", "label": "需求响应"},
    {"value": "100%", "label": "源码交付"},
    {"value": "1 对 1", "label": "项目跟进"},
    {"value": "7×12h", "label": "售后支持"},
]

SERVICES = [
    {
        "slug": "miniapp",
        "icon": "miniapp",
        "index": "01",
        "title": "微信小程序开发",
        "summary": "商城、预约、会员、工具类小程序，打通微信登录、支付与消息能力。",
        "tags": ["商城小程序", "预约系统", "会员运营"],
        "deliverables": "需求清单 · UI 设计 · 前后端 · 提审上架",
        "ask": "我想咨询微信小程序开发",
    },
    {
        "slug": "website",
        "icon": "browser",
        "index": "02",
        "title": "企业网站 / H5 开发",
        "summary": "企业官网、品牌展示页、活动落地页，兼顾手机与电脑端的浏览体验。",
        "tags": ["企业官网", "活动 H5", "后台管理"],
        "deliverables": "页面策划 · 响应式开发 · 内容后台 · 部署",
        "ask": "我想咨询企业网站或 H5 开发",
    },
    {
        "slug": "android",
        "icon": "mobile",
        "index": "03",
        "title": "安卓 App 开发",
        "summary": "原生或跨平台 App 开发，覆盖需求梳理、UI 设计、开发测试到应用市场上架。",
        "tags": ["工具类 App", "行业应用", "上架支持"],
        "deliverables": "原型设计 · App 开发 · 接口联调 · 上架指导",
        "ask": "我想咨询安卓 App 开发",
    },
    {
        "slug": "system",
        "icon": "layers",
        "index": "04",
        "title": "数字化系统定制",
        "summary": "预约、进销存、CRM、数据看板等业务系统，把重复的流程交给系统。",
        "tags": ["预约管理", "进销存", "数据看板"],
        "deliverables": "流程梳理 · 权限设计 · 系统开发 · 培训交付",
        "ask": "我想咨询业务系统定制",
    },
]

SERVICE_NOTE = "不确定该做小程序、网站还是 App？先把业务讲给我们听，我们帮你判断更合适的方案。"

ADVANTAGES = [
    {
        "icon": "pin",
        "title": "本地团队，沟通不绕弯",
        "text": "云南本地技术团队，支持线上沟通与当面交流，需求确认和问题反馈都更直接。",
    },
    {
        "icon": "compass",
        "title": "先梳理需求，再谈方案",
        "text": "不急着报价，先理解你的业务场景，给出可落地的功能清单、技术方案与排期。",
    },
    {
        "icon": "shield",
        "title": "源码交付，资产归你",
        "text": "项目验收后交付完整源码与部署文档，后续可以自主迭代，也可以继续交给我们维护。",
    },
    {
        "icon": "refresh",
        "title": "上线不是结束",
        "text": "提供上线后维护期，持续修复问题、优化体验，陪产品走过最需要打磨的冷启动阶段。",
    },
]

PROJECT_CARD = {
    "title": "一个项目，五道确认",
    "subtitle": "每一步都让你看得见进度",
    "items": [
        {"label": "需求与范围确认", "value": 100},
        {"label": "原型与视觉稿", "value": 100},
        {"label": "开发与联调", "value": 72},
        {"label": "测试与验收", "value": 40},
    ],
    "footnote": "示意进度 · 实际以项目排期为准",
}

PROCESS = [
    {
        "step": "01",
        "title": "需求沟通",
        "text": "聊业务、聊用户、聊预期，明确要解决的问题和边界。",
        "tag": "免费",
    },
    {
        "step": "02",
        "title": "方案与报价",
        "text": "输出功能清单、技术方案、排期与明细报价，确认后再启动。",
        "tag": "透明",
    },
    {
        "step": "03",
        "title": "原型与设计",
        "text": "先定结构和交互，再定视觉，避免开发阶段反复返工。",
        "tag": "可确认",
    },
    {
        "step": "04",
        "title": "开发与测试",
        "text": "按模块推进，阶段性演示；功能、兼容性与异常场景逐项自测。",
        "tag": "有节奏",
    },
    {
        "step": "05",
        "title": "交付与维护",
        "text": "源码、文档、部署一并交付，并提供上线后的持续维护支持。",
        "tag": "有保障",
    },
]

FAQ = [
    {
        "q": "开发一个小程序大概需要多少钱？",
        "a": (
            "费用取决于功能范围。展示型小程序相对轻量，商城、预约、会员等按模块评估。"
            "先聊清楚需求，我们会给出明确的功能清单和报价，避免做到一半再加价。"
        ),
    },
    {
        "q": "开发周期一般多久？",
        "a": (
            "展示型官网通常 1–2 周，小程序通常 3–6 周，复杂业务系统按模块排期。"
            "需求确认后我们会给出带里程碑的排期表，并按节点同步进度。"
        ),
    },
    {
        "q": "可以先做一部分，后续再加功能吗？",
        "a": (
            "可以。我们建议按模块设计，先上线核心流程，再根据真实使用情况迭代。"
            "这样预算更可控，也能更早拿到用户反馈。"
        ),
    },
    {
        "q": "上线后出现问题怎么办？",
        "a": (
            "交付后提供维护期，负责修复缺陷和必要的适配调整。"
            "维护期结束后可以选择按次支持或签订长期维护，源码和文档都在你手里。"
        ),
    },
    {
        "q": "我们在外地，可以合作吗？",
        "a": (
            "可以。大部分流程线上完成：需求会议、原型确认、阶段演示和验收都可以远程进行。"
            "云南本地客户也支持当面沟通。"
        ),
    },
]

CONTACT = {
    "eyebrow": "开始合作",
    "title": "有想法？先聊聊，不收费",
    "description": (
        "说说你的业务和预期，我们会在 1 个工作日内给出初步建议和大致方案。"
        "暂时不合作也没关系，多一个懂技术的人帮你参谋。"
    ),
    "form_title": "留下联系方式",
    "form_note": "仅用于本次咨询，不会群发打扰。",
}

FOOTER_NOTE = "云南美刻网络科技有限公司 · 专注小程序 / 网站 / App 定制开发"
