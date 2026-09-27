"""
DRISHTRA Database Engine
SQLAlchemy Session Management supporting:
1. SQLite Sovereign Vault (Default for Air-Gapped / Offline Defence Execution)
2. PostgreSQL / Neon.tech (For Cloud Demonstration / Multi-Analyst Deployment)
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

import re

import logging

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL.strip()

# Normalize Neon / Heroku / AWS Postgres URLs and accidental prefix typos (e.g. sqpostgresql://)
if re.match(r"^sq+l*(ite)?postgres(ql)?://", db_url):
    db_url = re.sub(r"^sq+l*(ite)?postgres(ql)?://", "postgresql://", db_url)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Check driver availability for PostgreSQL (psycopg v3 vs psycopg2)
has_psycopg3 = False
try:
    import psycopg  # noqa: F401
    has_psycopg3 = True
except ImportError:
    pass

has_psycopg2 = False
try:
    import psycopg2  # noqa: F401
    has_psycopg2 = True
except ImportError:
    pass

# Dynamically negotiate dialect if specific driver is missing
if "postgresql+psycopg://" in db_url and not has_psycopg3 and has_psycopg2:
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not has_psycopg3 and has_psycopg2:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

def _build_sqlite_engine():
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    root_dir = os.path.abspath(os.path.join(cur_dir, "..", "..", ".."))
    abs_db_path = os.path.join(root_dir, "drishtra_vault.db").replace("\\", "/")
    sqlite_url = f"sqlite:///{abs_db_path}"
    return create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

if db_url.startswith("sqlite"):
    if "///./" in db_url:
        db_rel = db_url.split("///./")[-1]
        cur_dir = os.path.abspath(os.path.dirname(__file__))
        root_dir = os.path.abspath(os.path.join(cur_dir, "..", "..", ".."))
        abs_db_path = os.path.join(root_dir, db_rel).replace("\\", "/")
        db_url = f"sqlite:///{abs_db_path}"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True
    )
else:
    # PostgreSQL / Neon.tech configuration with pooling and fallback
    try:
        engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300
        )
    except Exception as e:
        logger.warning(f"[!] Failed to initialize Postgres engine ({e}), falling back to SQLite vault.")
        engine = _build_sqlite_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
