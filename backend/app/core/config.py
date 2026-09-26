"""
DRISHTRA - Digital Reliability & Integrity Shield for Trusted AI
Core Configuration and Settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "DRISHTRA"
    PROJECT_SUBTITLE: str = "India-First Offline AI Assurance Fabric for Multi-Contributor Computer Vision"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Deployment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "air-gapped-development") # "air-gapped-production", "air-gapped-development", "render-demo"
    IS_AIR_GAPPED: bool = os.getenv("IS_AIR_GAPPED", "true").lower() in ["true", "1", "yes"]
    
    # Server Bindings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "drishtra-sovereign-defence-assurance-secret-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Database (Default: SQLite for air-gapped; also supports Neon.tech / Cloud PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./drishtra_vault.db")
    
    # Optional Grok / xAI LLM Integration (for tactical narrative incident debriefs)
    GROK_API_KEY: Optional[str] = os.getenv("GROK_API_KEY", None)
    GROK_API_BASE: str = os.getenv("GROK_API_BASE", "https://api.x.ai/v1")
    GROK_MODEL: str = os.getenv("GROK_MODEL", "grok-2-latest")
    
    # Storage Paths
    BASE_STORAGE_DIR: str = os.getenv("BASE_STORAGE_DIR", "./storage")
    ARTIFACTS_DIR: str = os.path.join(BASE_STORAGE_DIR, "artifacts")
    MANIFESTS_DIR: str = os.path.join(BASE_STORAGE_DIR, "manifests")
    AUDIT_DIR: str = os.path.join(BASE_STORAGE_DIR, "audit")
    FIXTURES_DIR: str = os.path.join(BASE_STORAGE_DIR, "fixtures")
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "*"
    ]
    
    model_config = {
        "env_file": (".env", "../.env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()

# Ensure directories exist
os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)
os.makedirs(settings.MANIFESTS_DIR, exist_ok=True)
os.makedirs(settings.AUDIT_DIR, exist_ok=True)
os.makedirs(settings.FIXTURES_DIR, exist_ok=True)
