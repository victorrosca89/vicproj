"""
Rute de autentificare:
- POST /api/v1/auth/login-pin      -> login clasic cu PIN
- POST /api/v1/auth/magic-generate -> genereaza Magic Link F-PAS (necesita sesiune admin)
- POST /api/v1/auth/magic-verify   -> valideaza si consuma jetonul F-PAS, emite JWT
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_pin,
    create_access_token,
    generate_magic_token,
    consume_magic_token,
    get_current_admin,
)
from app.models.schemas import (
    PinLoginRequest,
    TokenResponse,
    MagicGenerateResponse,
    MagicVerifyRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


@router.post("/login-pin", response_model=TokenResponse)
def login_pin(payload: PinLoginRequest):
    """Autentificare clasica prin PIN (hash-uit in variabilele de mediu / DB)."""
    if not settings.ADMIN_PIN_HASH or not verify_pin(payload.pin, settings.ADMIN_PIN_HASH):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PIN incorect.")

    access_token = create_access_token(subject="admin")
    return TokenResponse(access_token=access_token, expires_in_minutes=settings.JWT_EXPIRE_MINUTES)


@router.post("/magic-generate", response_model=MagicGenerateResponse)
def magic_generate(
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
):
    """
    Genereaza un Magic Link F-PAS nou. Necesita o sesiune Admin activa
    (adminul deja logat pe un dispozitiv genereaza link-ul pentru alt dispozitiv).
    """
    raw_token, db_token = generate_magic_token(db, admin_id=current_admin)
    return MagicGenerateResponse(
        magic_url_path=f"/auth/magic?token={raw_token}",
        token=raw_token,
        expires_at=db_token.expires_at,
    )


@router.post("/magic-verify", response_model=TokenResponse)
def magic_verify(payload: MagicVerifyRequest, db: Session = Depends(get_db)):
    """
    Consuma jetonul F-PAS (single-use enforcement in security.consume_magic_token)
    si emite un JWT de sesiune Admin daca jetonul este valid.
    """
    db_token = consume_magic_token(db, payload.token)
    access_token = create_access_token(subject=db_token.admin_id or "admin")
    return TokenResponse(access_token=access_token, expires_in_minutes=settings.JWT_EXPIRE_MINUTES)
