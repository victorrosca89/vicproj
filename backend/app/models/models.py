"""
Modele SQLAlchemy: reflecta schema descrisa in specificatie
(users/admins, files, magic_tokens).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, Enum, Integer
from sqlalchemy.sql import func

from app.core.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class FileStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"


class AdminUser(Base):
    """
    Cont de administrator. In majoritatea instalarilor VicProj exista un singur
    admin autentificat prin PIN (ADMIN_PIN_HASH din .env), dar tabela permite
    extinderea la mai multi utilizatori daca este nevoie in viitor.
    """
    __tablename__ = "admins"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String, unique=True, nullable=False, default="admin")
    pin_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FileResource(Base):
    """Fisier / proiect scolar publicat in VicProj."""
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=gen_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # cale locala sau URL (S3/etc.)
    materia = Column(String, nullable=False)
    shared_code = Column(String, unique=True, nullable=False, index=True)
    status = Column(Enum(FileStatus), nullable=False, default=FileStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MagicToken(Base):
    """
    Jeton F-PAS (Single-Use Magic Link).
    Se stocheaza DOAR hash-ul jetonului, niciodata valoarea in clar.
    """
    __tablename__ = "magic_tokens"

    id = Column(String, primary_key=True, default=gen_uuid)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    admin_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, nullable=False, default=False)
