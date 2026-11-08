"""Pydantic schemas at trust boundaries."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"


class UserIn(BaseModel):
    username: str
    password: str = Field(min_length=4, max_length=72)  # bcrypt truncates past 72 bytes
    role: str = "staff"
    display_name: str | None = None


class AccountIn(BaseModel):
    name: str


class AssignIn(BaseModel):
    user_id: str


class ChatIn(BaseModel):
    account_id: str | None = None
    question: str
    session_id: str | None = None


class ChatOut(BaseModel):
    answer: str
    session_id: str | None = None
    session_expired: bool = False
    escalated: bool = False
    department: str | None = None
    category: str = "general"


class FaqIn(BaseModel):
    question: str


class CredentialOut(BaseModel):
    key_id: str
    account_id: str
    secret: str = ""  # plaintext only at issuance/rotation
    revoked: bool = False
