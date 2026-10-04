"""
DRISHTRA Sovereign Database Migration & Schema Synchronizer
Performs non-destructive schema migrations and column synchronization across SQLite & PostgreSQL.
Guarantees schema stability without dropping tables or corrupting historical audit chains.
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from app.db.database import Base, engine
import app.db.models  # Ensures all ORM models are registered with Base.metadata


logger = logging.getLogger(__name__)

# Explicit list of columns to ensure exist on existing tables if upgraded
EXPECTED_COLUMNS = {
    "contributors": [
        ("metadata_json", "TEXT DEFAULT '{}'")
    ],
    "datasets": [
        ("evidence_label", "VARCHAR(32) DEFAULT 'SYNTHETIC'"),
        ("metadata_json", "TEXT DEFAULT '{}'")
    ],
    "model_assets": [
        ("structural_digest", "VARCHAR(64)"),
        ("parameter_count", "INTEGER DEFAULT 0"),
        ("opset_version", "INTEGER"),
        ("evidence_label", "VARCHAR(32) DEFAULT 'SYNTHETIC'"),
        ("metadata_json", "TEXT DEFAULT '{}'")
    ],
    "inference_records": [
        ("evidence_label", "VARCHAR(32) DEFAULT 'SYNTHETIC'"),
        ("signer", "VARCHAR(128) DEFAULT 'edge_drone_01'"),
        ("dataset_id", "VARCHAR(64)"),
        ("sample_id", "VARCHAR(64)"),
        ("runtime_id", "VARCHAR(64)"),
        ("model_digest", "VARCHAR(64)"),
        ("configuration_digest", "VARCHAR(64)")
    ],
    "findings": [
        ("deterministic", "BOOLEAN DEFAULT FALSE"),
        ("limitations", "TEXT")
    ],
    "evidence_items": [
        ("target_type", "VARCHAR(64) DEFAULT 'DATASET'"),
        ("target_id", "VARCHAR(64) DEFAULT ''"),
        ("lifecycle_stage", "VARCHAR(64) DEFAULT 'DATASET'"),
        ("detector_id", "VARCHAR(64) DEFAULT 'DETECTOR'"),
        ("finding_type", "VARCHAR(64) DEFAULT 'INTEGRITY_CHECK'"),
        ("status", "VARCHAR(32) DEFAULT 'FINDING'"),
        ("deterministic", "BOOLEAN DEFAULT FALSE"),
        ("artifact_digest", "VARCHAR(64)"),
        ("limitations", "TEXT")
    ],
    "assurance_cases": [
        ("incriminating_evidence_json", "TEXT DEFAULT '[]'"),
        ("convergence_json", "TEXT DEFAULT '{}'"),
        ("initiated_by", "VARCHAR(128)"),
        ("human_disposition", "VARCHAR(64)"),
        ("approved_by", "VARCHAR(128)"),
        ("approved_at", "VARCHAR(64)"),
        ("approval_notes", "TEXT")
    ],
    "audit_events": [
        ("sequence", "INTEGER DEFAULT 1")
    ]
}

def run_migrations(target_engine: Engine = engine) -> bool:
    """
    Applies non-destructive schema synchronization.
    1. Creates newly introduced tables (e.g. dataset_chunks, runtime_bindings, pipeline_runs).
    2. Adds newly introduced columns to existing tables if missing.
    """
    try:
        # Step 1: Create any tables that don't exist yet
        Base.metadata.create_all(bind=target_engine)
        
        # Step 2: Inspect existing tables and synchronize columns
        inspector = inspect(target_engine)
        existing_tables = set(inspector.get_table_names())
        
        for table_name, columns in EXPECTED_COLUMNS.items():
            if table_name in existing_tables:
                existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                for col_name, col_def in columns:
                    if col_name not in existing_cols:
                        logger.info(f"[*] Applying migration: adding column {table_name}.{col_name}")
                        try:
                            with target_engine.connect() as conn:
                                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def};"
                                conn.execute(text(alter_sql))
                                conn.commit()
                        except Exception as ex:
                            logger.warning(f"[!] Migration warning for {table_name}.{col_name}: {ex}")
        
        logger.info("[*] DRISHTRA schema migrations synchronized successfully.")
        return True
    except Exception as e:
        logger.error(f"[!] Migration failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
