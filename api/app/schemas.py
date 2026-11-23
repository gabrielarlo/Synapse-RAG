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


class TransferIn(BaseModel):
    target_account_id: str


class ChatIn(BaseModel):
    account_id: str | None = None
    question: str
    session_id: str | None = None


class A2UIComponent(BaseModel):
    id: str
    type: str  # catalog-gated on render; see api/app/a2ui.py CATALOG
    props: dict | None = None
    children: list["A2UIComponent"] | None = None


class A2UISurface(BaseModel):
    surfaceId: str
    components: list[A2UIComponent]
    dataModel: dict | None = None


class ChatOut(BaseModel):
    answer: str
    session_id: str | None = None
    session_expired: bool = False
    escalated: bool = False
    department: str | None = None
    category: str = "general"
    a2ui: A2UISurface | None = None


class FaqIn(BaseModel):
    question: str


class FaqOut(BaseModel):
    answer: str
    category: str = "external_faq"
    department: str | None = None
    a2ui: A2UISurface | None = None


class CredentialIn(BaseModel):
    label: str | None = Field(default=None, max_length=64, description="human label for the key")
    expires_in_days: int | None = Field(default=None, ge=1, le=365, description="days until expiry, default 90")


class CredentialOut(BaseModel):
    key_id: str
    account_id: str
    secret: str = ""  # plaintext only at issuance/rotation
    revoked: bool = False
    label: str | None = None
    expires_at: str | None = None
    created_at: str | None = None
