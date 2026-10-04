"""
Bootstrap DRISHTRA locally: migrate the schema, create the first administrator
and (when DEMO_MODE=true, the default) the synthetic demo accounts and cases.

    python scripts/bootstrap_demo.py            # idempotent
    python scripts/bootstrap_demo.py --reset    # rebuild the demo cases
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.config import settings  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402
from app.db.migrations import run_migrations  # noqa: E402
from app.services.demo_service import DemoService  # noqa: E402
from app.services.user_service import UserService  # noqa: E402

if __name__ == "__main__":
    run_migrations(engine)
    db = SessionLocal()
    try:
        created = UserService.bootstrap(db)["created"]
        print(f"[*] Accounts created this run: {created or 'none (already present)'}")
        if settings.DEMO_MODE:
            res = DemoService.bootstrap_demo_case(db, force_reset="--reset" in sys.argv)
            for cid, r in res["cases"].items():
                print(f"[*] {cid}: {r}")
            print("[*] Demo accounts: admin, ml.analyst, sec.analyst, reviewer, auditor  (password: Drishtra@2026)")
        else:
            print("[*] DEMO_MODE=false: no demo data. If no admin password was set, see storage/keys/initial_admin_password.txt")
    finally:
        db.close()
