"""
Rute de management fisiere (protejate - necesita sesiune Admin):
- GET    /api/v1/files              -> lista + filtre + cautare
- POST   /api/v1/files/upload       -> upload fisier + salvare metadata
- PATCH  /api/v1/files/{id}/status  -> schimbare stare (active/paused/blocked)
"""
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.models import FileResource, FileStatus
from app.models.schemas import FileOut, FileStatusUpdate

router = APIRouter(prefix="/api/v1/files", tags=["files"])
settings = get_settings()


def _generate_unique_code(db: Session) -> str:
    while True:
        code = secrets.token_hex(4)  # 8 caractere hex, greu de ghicit
        exists = db.query(FileResource).filter(FileResource.shared_code == code).first()
        if not exists:
            return code


@router.get("", response_model=list[FileOut])
def list_files(
    search: Optional[str] = None,
    status_filter: Optional[FileStatus] = None,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
):
    query = db.query(FileResource)
    if search:
        like = f"%{search.lower()}%"
        query = query.filter(
            or_(FileResource.filename.ilike(like), FileResource.materia.ilike(like))
        )
    if status_filter:
        query = query.filter(FileResource.status == status_filter)
    return query.order_by(FileResource.created_at.desc()).all()


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    materia: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    code = _generate_unique_code(db)
    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(settings.UPLOAD_DIR, f"{code}_{safe_name}")

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    db_file = FileResource(
        filename=safe_name,
        file_path=dest_path,
        materia=materia,
        shared_code=code,
        status=FileStatus.ACTIVE,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file


@router.patch("/{file_id}/status", response_model=FileOut)
def update_file_status(
    file_id: str,
    payload: FileStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: str = Depends(get_current_admin),
):
    db_file = db.query(FileResource).filter(FileResource.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fisier inexistent.")

    # Blocarea este ireversibila: backend-ul respinge orice modificare ulterioara.
    if db_file.status == FileStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acest link a fost blocat definitiv si nu mai poate fi modificat.",
        )

    db_file.status = payload.status
    db.commit()
    db.refresh(db_file)
    return db_file
