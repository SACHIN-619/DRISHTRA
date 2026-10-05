"""
DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI
Core Configuration and Settings
"""
import os
from typing import Any, List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DRISHTRA"
    PROJECT_SUBTITLE: str = "India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Deployment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "air-gapped-development") # "air-gapped-production", "air-gapped-development", "render-demo"
    IS_AIR_GAPPED: bool = os.getenv("IS_AIR_GAPPED", "true").lower() in ["true", "1", "yes"]
    
    # Server Bindings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Security & Auth
    # SECRET_KEY: never hardcoded. If unset, a random per-install secret is generated
    # under storage/keys/ on first start (see resolve_secret_key below).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 8))  # one working shift

    # Identity bootstrap & account policy
    # DEMO_MODE seeds one synthetic account per role so judges can walk every console.
    # It must be false for any real deployment.
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ["true", "1", "yes"]
    BOOTSTRAP_ADMIN_USERNAME: str = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    BOOTSTRAP_ADMIN_PASSWORD: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", 10))
    MAX_FAILED_LOGINS: int = int(os.getenv("MAX_FAILED_LOGINS", 5))
    LOCKOUT_MINUTES: int = int(os.getenv("LOCKOUT_MINUTES", 15))
    # Optional explanation layer (never required by the assurance core)
    ALLOW_EXTERNAL_EXPLAINER: bool = os.getenv("ALLOW_EXTERNAL_EXPLAINER", "false").lower() in ["true", "1", "yes"]
    
    # Database (Default: SQLite for air-gapped; also supports Neon.tech / Cloud PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./drishtra_vault.db")
    
    # Optional Grok / xAI LLM Integration (for tactical narrative incident debriefs)
    GROK_API_KEY: Optional[str] = os.getenv("GROK_API_KEY", None)
    GROK_API_BASE: str = os.getenv("GROK_API_BASE", "https://api.x.ai/v1")
    GROK_MODEL: str = os.getenv("GROK_MODEL", "grok-2-latest")
    
    # Storage Paths & Limits
    BASE_STORAGE_DIR: str = os.getenv("BASE_STORAGE_DIR", "./storage")
    ARTIFACTS_DIR: str = os.path.join(BASE_STORAGE_DIR, "artifacts")
    MANIFESTS_DIR: str = os.path.join(BASE_STORAGE_DIR, "manifests")
    AUDIT_DIR: str = os.path.join(BASE_STORAGE_DIR, "audit")
    FIXTURES_DIR: str = os.path.join(BASE_STORAGE_DIR, "fixtures")
    UPLOADS_DIR: str = os.path.join(BASE_STORAGE_DIR, "uploads")
    TEMP_DIR: str = os.path.join(BASE_STORAGE_DIR, "tmp")

    # Ingestion & Upload Policy Limits (MB)
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", 2048))
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", 25))
    MAX_ARCHIVE_SIZE_MB: int = int(os.getenv("MAX_ARCHIVE_SIZE_MB", 4096))
    INGESTION_CHUNK_SIZE: int = int(os.getenv("INGESTION_CHUNK_SIZE", 1000))
    MAX_RECORDS_PER_REQUEST: int = int(os.getenv("MAX_RECORDS_PER_REQUEST", 5000))
    
    # CORS
    # Supports comma-separated origins, JSON arrays, or wildcard via env var CORS_ORIGINS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    
    model_config = {
        "env_file": (".env", "../.env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()


_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


def database_host(url: str) -> str:
    """Host part of a database URL ('' for SQLite files)."""
    from urllib.parse import urlsplit
    if url.strip().lower().startswith("sqlite"):
        return ""
    try:
        return (urlsplit(url.strip()).hostname or "").lower()
    except ValueError:
        return "unknown"


def database_is_local(url: Optional[str] = None) -> bool:
    return database_host(url if url is not None else settings.DATABASE_URL) in _LOCAL_DB_HOSTS


def effective_air_gapped() -> bool:
    """Air-gapped only if the operator asked for it AND nothing the node depends on is remote.
    A cloud database (e.g. Neon) means the node is network-dependent, whatever IS_AIR_GAPPED says."""
    return bool(settings.IS_AIR_GAPPED and database_is_local())

KNOWN_PUBLIC_DEFAULT_SECRETS = {
    "drishtra-sovereign-defence-assurance-secret-key-2026",
    "changeme", "secret", "",
}
KEYS_DIR = os.path.join(settings.BASE_STORAGE_DIR, "keys")


def resolve_secret_key() -> str:
    """
    Returns the JWT/HMAC secret.
    Order: SECRET_KEY env var -> storage/keys/jwt_secret (generated once, 0600).
    A secret that was ever published in this repository is refused outside demo mode.
    """
    import secrets as _secrets
    import logging as _logging
    configured = (settings.SECRET_KEY or "").strip()
    if configured and configured not in KNOWN_PUBLIC_DEFAULT_SECRETS:
        return configured
    if configured in KNOWN_PUBLIC_DEFAULT_SECRETS and configured:
        if not settings.DEMO_MODE:
            raise RuntimeError(
                "SECRET_KEY is set to a publicly known default. Set a unique SECRET_KEY "
                "or remove it so DRISHTRA generates a per-install secret."
            )
        _logging.getLogger("drishtra").warning(
            "[!] SECRET_KEY is a publicly known default; ignoring it and using a per-install secret."
        )
    os.makedirs(KEYS_DIR, exist_ok=True)
    path = os.path.join(KEYS_DIR, "jwt_secret")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            value = fh.read().strip()
            if value:
                return value
    value = _secrets.token_urlsafe(48)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(value)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return value


settings.SECRET_KEY = resolve_secret_key()

# Ensure storage lifecycle directories exist
for path in [
    settings.ARTIFACTS_DIR,
    settings.MANIFESTS_DIR,
    settings.AUDIT_DIR,
    settings.FIXTURES_DIR,
    settings.UPLOADS_DIR,
    settings.TEMP_DIR
]:
    os.makedirs(path, exist_ok=True)

