"""Pydantic v2 schemas for User and Authentication."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, description="Staff email address")
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str
    department: Optional[str] = None
    registration_number: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    department: Optional[str] = None
    registration_number: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime


class UserLogin(BaseModel):
    email: str = Field(..., description="Staff email address")
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    role: str
    permissions: List[str] = []
    exp: datetime
    iat: datetime
    jti: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

