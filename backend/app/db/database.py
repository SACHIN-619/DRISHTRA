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

db_url = settings.DATABASE_URL.strip()

# Normalize Neon / Heroku / AWS Postgres URLs and accidental prefix typos (e.g. sqpostgresql://)
if re.match(r"^sq+l*(ite)?postgres(ql)?://", db_url):
    db_url = re.sub(r"^sq+l*(ite)?postgres(ql)?://", "postgresql://", db_url)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

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
    # PostgreSQL / Neon.tech configuration with pooling
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
