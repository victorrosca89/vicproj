"""
Nucleul de securitate VicProj:
- Hashing/verificare PIN admin (bcrypt via passlib)
- Emitere / validare JWT de sesiune
- Logica F-PAS: generare jeton criptografic, hash-uire, verificare single-use
"""
import secrets
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.models import MagicToken

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------- PIN Admin ----------------

def verify_pin(plain_pin: str, pin_hash: str) -> bool:
    return pwd_context.verify(plain_pin, pin_hash)


def hash_pin(plain_pin: str) -> str:
    return pwd_context.hash(plain_pin)


# ---------------- JWT Sesiune ----------------

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, "type": "admin_session"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesiune invalid sau expirat.",
        )


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Dependency FastAPI care protejeaza rutele Admin. Cere header Authorization: Bearer <jwt>."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentificare necesara.",
        )
    payload = decode_access_token(credentials.credentials)
    if payload.get("type") != "admin_session":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid.")
    return payload.get("sub")


# ---------------- F-PAS: Magic Link Single-Use ----------------

def _hash_token(raw_token: str) -> str:
    """Nu stocam niciodata jetonul in clar in DB, doar hash-ul lui (SHA-256)."""
    return sha256(raw_token.encode("utf-8")).hexdigest()


def generate_magic_token(db: Session, admin_id: str) -> tuple[str, MagicToken]:
    """
    Genereaza un jeton criptografic securizat (32 bytes, urlsafe),
    il stocheaza HASH-uit in DB cu is_used=False si expires_at = now + N minute.
    Returneaza (jeton_in_clar_pentru_link, obiect_DB).
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.MAGIC_TOKEN_EXPIRE_MINUTES)

    db_token = MagicToken(
        token_hash=token_hash,
        admin_id=admin_id,
        expires_at=expires_at,
        is_used=False,
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return raw_token, db_token


def consume_magic_token(db: Session, raw_token: str) -> MagicToken:
    """
    Valideaza si consuma (single-use) un jeton F-PAS:
      1. Cauta hash-ul jetonului in DB.
      2. Verifica is_used == False.
      3. Verifica expires_at > now.
      4. Marcheaza imediat is_used = True (enforcement single-use) inainte de a returna.
    Arunca HTTPException 401 daca oricare din verificari esueaza.
    """
    token_hash = _hash_token(raw_token)
    db_token = db.query(MagicToken).filter(MagicToken.token_hash == token_hash).first()

    if db_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton invalid.")

    if db_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acest Magic Link a fost deja folosit.",
        )

    now = datetime.now(timezone.utc)
    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton expirat.")

    # Enforcement single-use: marcam folosit ATOMIC, inainte de a emite sesiunea.
    db_token.is_used = True
    db.commit()
    db.refresh(db_token)
    return db_token
