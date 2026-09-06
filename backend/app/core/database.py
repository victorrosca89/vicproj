"""
Configurare SQLAlchemy: engine, sesiune si clasa Base pentru modele.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Necesar pentru SQLite in aplicatii multi-thread (ex: FastAPI + Uvicorn)
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency FastAPI: ofera o sesiune DB si o inchide automat dupa request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
