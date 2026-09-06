"""
Configurare centralizata a aplicatiei VicProj, incarcata din variabile de mediu (.env).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # JWT / Sesiune Admin
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    # PIN Admin (stocat DOAR ca hash bcrypt)
    ADMIN_PIN_HASH: str = ""

    # F-PAS Magic Link
    MAGIC_TOKEN_EXPIRE_MINUTES: int = 15

    # Baza de date
    DATABASE_URL: str = "sqlite:///./vicproj.db"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080"

    # Fisiere
    UPLOAD_DIR: str = "./uploads"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
