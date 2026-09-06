"""
Endpoint public (fara autentificare):
- GET /api/v1/share/{code}          -> stare fisier (pentru afisare pagina publica)
- GET /api/v1/share/{code}/download -> descarcare efectiva (doar daca status == active)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import FileResource, FileStatus
from app.models.schemas import SharePublicOut

router = APIRouter(prefix="/api/v1/share", tags=["share"])


def _get_file_or_404(code: str, db: Session) -> FileResource:
    db_file = db.query(FileResource).filter(FileResource.shared_code == code).first()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link inexistent.")
    return db_file


@router.get("/{code}", response_model=SharePublicOut)
def get_share_status(code: str, db: Session = Depends(get_db)):
    db_file = _get_file_or_404(code, db)
    return SharePublicOut(
        filename=db_file.filename,
        materia=db_file.materia,
        status=db_file.status,
        download_available=(db_file.status == FileStatus.ACTIVE),
    )


@router.get("/{code}/download")
def download_shared_file(code: str, db: Session = Depends(get_db)):
    db_file = _get_file_or_404(code, db)

    if db_file.status == FileStatus.PAUSED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Resursa suspendata temporar.")
    if db_file.status == FileStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Link blocat definitiv.")

    return FileResponse(path=db_file.file_path, filename=db_file.filename)
