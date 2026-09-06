"""
Punct de intrare al aplicatiei VicProj Backend (FastAPI).
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import Base, engine
from app.api import auth, files, share

settings = get_settings()

# Creeaza tabelele daca nu exista (pentru productie reala, foloseste Alembic pentru migratii).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VicProj API",
    description="Platforma scolara de management resurse & F-PAS Magic Link Auth.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(share.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Format unitar de eroare, usor de consumat din frontend (toast notifications)."""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "Date invalide.", "details": exc.errors()})


@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "vicproj-backend"}
