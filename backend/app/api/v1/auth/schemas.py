"""Request/response schemas for the auth API."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """New candidate signup payload (text fields only; files are handled
    separately as multipart uploads in the router).

    ``password`` is bounded at 128 chars to stay within bcrypt's 72-byte window
    plus headroom; ``full_name`` matches the ``users.full_name`` column length.
    Profile fields map to ``user_profiles`` columns; ``years_of_experience`` fits
    the ``numeric(4,2)`` column (0–99.99).
    """

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    current_organization: str = Field(min_length=1, max_length=200)
    current_designation: str = Field(min_length=1, max_length=150)
    years_of_experience: Annotated[
        Decimal,
        Field(ge=0, le=Decimal("99.99"), max_digits=4, decimal_places=2),
    ]
    phone_number: str | None = Field(default=None, max_length=30)


class AuthUser(BaseModel):
    """The authenticated user's public identity returned to the client.

    Tokens are delivered via httpOnly cookies, never in the body — the client
    only needs identity + roles to drive UI and route protection.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    roles: list[str]
    profile_photo_path: str | None = None


class LoginResponse(BaseModel):
    user: AuthUser


class SendEmailOtpRequest(BaseModel):
    email: EmailStr


class SendEmailOtpResponse(BaseModel):
    success: bool
    message: str
    cooldown_seconds: int = 60


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyEmailResponse(BaseModel):
    success: bool
    verified: bool
    message: str
