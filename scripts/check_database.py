"""
Check the database DRISHTRA is configured to use (SQLite or PostgreSQL / Neon).

    cd backend
    python ../scripts/check_database.py            # read-only checks
    python ../scripts/check_database.py --init     # also create missing tables / columns

Reads DATABASE_URL from the environment or backend/.env exactly as the server does.
The password in the URL is never printed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "backend"))
os.chdir(os.path.join(HERE, "..", "backend"))

from urllib.parse import urlsplit  # noqa: E402


def masked(url: str) -> str:
    if url.startswith("sqlite"):
        return url
    p = urlsplit(url)
    user = p.username or ""
    host = p.hostname or ""
    port = f":{p.port}" if p.port else ""
    return f"{p.scheme}://{user}:***@{host}{port}{p.path}"


def main() -> int:
    from app.core.config import settings, database_is_local, effective_air_gapped
    print(f"DATABASE_URL     : {masked(settings.DATABASE_URL)}")
    print(f"Location         : {'local' if database_is_local() else 'REMOTE (network required)'}")
    print(f"IS_AIR_GAPPED    : {settings.IS_AIR_GAPPED}  ->  effective air-gap: {effective_air_gapped()}")
    print(f"DEMO_MODE        : {settings.DEMO_MODE}")
    print(f"External explainer (Grok) allowed: {bool(settings.ALLOW_EXTERNAL_EXPLAINER and settings.GROK_API_KEY and not settings.IS_AIR_GAPPED)}")
    try:
        from app.db.database import engine, Base
        import app.db.models  # noqa: F401
    except Exception as e:
        print(f"\nFAIL  could not create the engine: {e}")
        return 2
    print(f"Engine dialect   : {engine.dialect.name}")
    from sqlalchemy import inspect, text
    try:
        with engine.connect() as c:
            ver = c.execute(text("select version()" if engine.dialect.name == "postgresql" else "select sqlite_version()")).scalar()
        print(f"Server version   : {str(ver)[:70]}")
    except Exception as e:
        print(f"\nFAIL  cannot connect: {e.__class__.__name__}: {str(e).splitlines()[0][:200]}")
        print("      Neon: use the pooled or direct connection string with ?sslmode=require")
        return 3

    if "--init" in sys.argv:
        from app.db.migrations import run_migrations
        Base.metadata.create_all(bind=engine)
        run_migrations(engine)
        print("Initialised      : tables created / columns migrated")

    insp = inspect(engine)
    have = set(insp.get_table_names())
    want = {t.name for t in Base.metadata.sorted_tables}
    missing_tables = sorted(want - have)
    missing_cols = []
    for t in Base.metadata.sorted_tables:
        if t.name in have:
            cols = {c["name"] for c in insp.get_columns(t.name)}
            missing_cols += [f"{t.name}.{c.name}" for c in t.columns if c.name not in cols]
    print(f"Tables           : {len(want & have)}/{len(want)} present")
    if missing_tables:
        print(f"  missing tables : {', '.join(missing_tables)}  (run with --init, or start the server once)")
    if missing_cols:
        print(f"  missing columns: {', '.join(missing_cols[:12])}{' …' if len(missing_cols) > 12 else ''}")

    if not missing_tables:
        from sqlalchemy.orm import Session
        from app.services.platform_audit_service import PlatformAuditService
        from app.db.models import User, Case
        with Session(engine) as db:
            print(f"Users / cases    : {db.query(User).count()} / {db.query(Case).count()}")
            chain = PlatformAuditService.verify(db)
            print(f"Platform ledger  : {chain['status']} ({chain['verified_count']} events)")
    ok = not missing_tables and not missing_cols
    print("\nOK" if ok else "\nNEEDS ATTENTION")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
