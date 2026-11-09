"""Pydantic request models."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

SESSION_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


def _clean(value: str) -> str:
    return " ".join(value.split()).strip()


class ChatSessionIn(BaseModel):
    session_id: str | None = Field(default=None, pattern=SESSION_PATTERN)
    source: str = Field(default="chat", max_length=20)
    page: str = Field(default="", max_length=200)


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("消息不能为空")
        return cleaned


class ContactIn(BaseModel):
    name: str = Field(default="", max_length=40)
    contact: str = Field(min_length=2, max_length=80)

    @field_validator("name", "contact")
    @classmethod
    def clean_fields(cls, value: str) -> str:
        return _clean(value)

    @field_validator("contact")
    @classmethod
    def contact_not_blank(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("请填写有效的联系方式")
        return value


class LeadIn(BaseModel):
    name: str = Field(default="", max_length=40)
    contact: str = Field(min_length=2, max_length=80)
    requirement: str = Field(default="", max_length=500)
    source: str = Field(default="form", max_length=20)

    @field_validator("name", "contact", "requirement")
    @classmethod
    def clean_fields(cls, value: str) -> str:
        return _clean(value)


class AdminLoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class AdminReplyIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("回复内容不能为空")
        return cleaned
