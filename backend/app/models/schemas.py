"""
Scheme Pydantic pentru validarea request/response-urilor API.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.models import FileStatus


# ---------- Auth ----------

class PinLoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class MagicGenerateResponse(BaseModel):
    magic_url_path: str  # ex: /auth/magic?token=xxxx  (frontend-ul construieste URL-ul complet)
    token: str  # trimis o singura data catre admin, niciodata stocat in clar
    expires_at: datetime


class MagicVerifyRequest(BaseModel):
    token: str


# ---------- Files ----------

class FileOut(BaseModel):
    id: str
    filename: str
    materia: str
    shared_code: str
    status: FileStatus
    created_at: datetime

    class Config:
        from_attributes = True


class FileStatusUpdate(BaseModel):
    status: FileStatus


# ---------- Share (public) ----------

class SharePublicOut(BaseModel):
    filename: str
    materia: str
    status: FileStatus
    download_available: bool
