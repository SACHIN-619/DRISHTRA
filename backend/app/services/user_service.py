"""
Identity lifecycle: authentication, account creation by administrators,
role changes, disable/enable, password change, lockout.

Every state change writes a hash-chained platform event.
"""
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import Role
from app.core.passwords import hash_password, verify_password
from app.db.models import User, utc_now_iso
from app.services.platform_audit_service import PlatformAuditService

USERNAME_RE = re.compile(r"^[a-z][a-z0-9._-]{2,31}$")
ACCESS_SCOPES = ["PUBLIC", "INTERNAL", "RESTRICTED", "SENSITIVE"]

# Synthetic demo accounts (DEMO_MODE only). Names are fictional.
DEMO_ACCOUNTS = [
    ("ml.analyst", "Asha Verma", Role.ML_ANALYST, "INTERNAL"),
    ("sec.analyst", "Kabir Rao", Role.SECURITY_ANALYST, "RESTRICTED"),
    ("reviewer", "Meera Iyer", Role.REVIEWER_SUPERVISOR, "RESTRICTED"),
    ("auditor", "Dev Malhotra", Role.AUDITOR, "RESTRICTED"),
]
DEMO_PASSWORD = "Drishtra@2026"


class AuthError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class UserService:
    # ------------------------------------------------------------------ helpers
    @staticmethod
    def validate_password(pw: str) -> None:
        if len(pw) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters.")
        classes = sum(bool(re.search(p, pw)) for p in [r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]"])
        if classes < 3:
            raise ValueError("Password must mix at least three of: lowercase, uppercase, digits, symbols.")

    @staticmethod
    def generate_temporary_password() -> str:
        # 4 groups, always satisfies the policy
        core = secrets.token_urlsafe(9).replace("-", "x").replace("_", "y")
        return f"Tmp-{core}-{secrets.randbelow(90) + 10}"

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username.strip().lower()).first()

    @staticmethod
    def get(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def count_active_admins(db: Session) -> int:
        return db.query(User).filter(
            User.role == Role.ADMINISTRATOR.value, User.status == "ACTIVE"
        ).count()

    # ------------------------------------------------------------- bootstrap
    @staticmethod
    def bootstrap(db: Session) -> dict:
        """
        Ensures the platform can be administered on first start.
        - If no administrator exists, create one. Password comes from
          BOOTSTRAP_ADMIN_PASSWORD; otherwise a random one is generated and
          written once to storage/keys/initial_admin_password.txt.
        - In DEMO_MODE, seed one synthetic account per operational role.
        """
        import os
        from app.core.config import KEYS_DIR
        created = []
        if db.query(User).filter(User.role == Role.ADMINISTRATOR.value).count() == 0:
            pw = settings.BOOTSTRAP_ADMIN_PASSWORD
            demo_pw_used = False
            if not pw:
                if settings.DEMO_MODE:
                    pw = DEMO_PASSWORD
                    demo_pw_used = True
                else:
                    pw = UserService.generate_temporary_password()
                    os.makedirs(KEYS_DIR, exist_ok=True)
                    path = os.path.join(KEYS_DIR, "initial_admin_password.txt")
                    with open(path, "w", encoding="utf-8") as fh:
                        fh.write(pw + "\n")
                    try:
                        os.chmod(path, 0o600)
                    except OSError:
                        pass
            admin = User(
                user_id=f"USR-{uuid.uuid4().hex[:10].upper()}",
                username=settings.BOOTSTRAP_ADMIN_USERNAME.lower(),
                full_name="Platform Administrator",
                role=Role.ADMINISTRATOR.value,
                access_scope="RESTRICTED",
                status="ACTIVE",
                password_hash=hash_password(pw),
                must_change_password=not demo_pw_used,
                created_by="SYSTEM_BOOTSTRAP",
                created_at=utc_now_iso(),
                is_demo_account=demo_pw_used,
            )
            db.add(admin)
            db.commit()
            PlatformAuditService.record(
                db, "GOVERNANCE", actor="SYSTEM_BOOTSTRAP", action="USER_CREATED",
                target=admin.username,
                details={"role": admin.role, "reason": "initial administrator", "demo": demo_pw_used},
            )
            created.append(admin.username)

        if settings.DEMO_MODE:
            for username, name, role, scope in DEMO_ACCOUNTS:
                if UserService.get_by_username(db, username):
                    continue
                u = User(
                    user_id=f"USR-{uuid.uuid4().hex[:10].upper()}",
                    username=username,
                    full_name=name,
                    role=role.value,
                    access_scope=scope,
                    status="ACTIVE",
                    password_hash=hash_password(DEMO_PASSWORD),
                    must_change_password=False,
                    created_by="SYSTEM_BOOTSTRAP",
                    created_at=utc_now_iso(),
                    is_demo_account=True,
                )
                db.add(u)
                db.commit()
                PlatformAuditService.record(
                    db, "GOVERNANCE", actor="SYSTEM_BOOTSTRAP", action="USER_CREATED",
                    target=username, details={"role": role.value, "demo": True},
                )
                created.append(username)
        return {"created": created}

    # ----------------------------------------------------------- authenticate
    @staticmethod
    def authenticate(db: Session, username: str, password: str, request_id: Optional[str] = None) -> User:
        uname = (username or "").strip().lower()
        user = UserService.get_by_username(db, uname)
        now = datetime.now(timezone.utc)

        if not user:
            # Same message as a wrong password: do not reveal which usernames exist.
            PlatformAuditService.record(
                db, "AUTH", actor=uname or "(blank)", action="LOGIN_FAILED", result="FAILURE",
                details={"reason": "unknown_user"}, request_id=request_id,
            )
            raise AuthError("INVALID_CREDENTIALS", "Invalid username or password.")

        if user.status != "ACTIVE":
            PlatformAuditService.record(
                db, "AUTH", actor=uname, actor_role=user.role, action="LOGIN_FAILED", result="DENIED",
                details={"reason": "account_disabled"}, request_id=request_id,
            )
            raise AuthError("ACCOUNT_DISABLED", "This account is disabled. Contact your administrator.")

        if user.locked_until:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until > now:
                PlatformAuditService.record(
                    db, "AUTH", actor=uname, actor_role=user.role, action="LOGIN_FAILED", result="DENIED",
                    details={"reason": "account_locked", "locked_until": user.locked_until}, request_id=request_id,
                )
                mins = max(1, int((locked_until - now).total_seconds() // 60) + 1)
                raise AuthError("ACCOUNT_LOCKED", f"Account temporarily locked after repeated failures. Try again in {mins} min.")
            user.locked_until = None
            user.failed_attempts = 0

        if not verify_password(password or "", user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            locked = user.failed_attempts >= settings.MAX_FAILED_LOGINS
            if locked:
                user.locked_until = (now + timedelta(minutes=settings.LOCKOUT_MINUTES)).isoformat()
            db.commit()
            PlatformAuditService.record(
                db, "AUTH", actor=uname, actor_role=user.role,
                action="ACCOUNT_LOCKED" if locked else "LOGIN_FAILED", result="FAILURE",
                details={"reason": "bad_password", "failed_attempts": user.failed_attempts}, request_id=request_id,
            )
            raise AuthError("INVALID_CREDENTIALS", "Invalid username or password.")

        user.failed_attempts = 0
        user.locked_until = None
        user.last_login_at = utc_now_iso()
        db.commit()
        PlatformAuditService.record(
            db, "AUTH", actor=uname, actor_role=user.role, action="LOGIN_SUCCEEDED",
            request_id=request_id,
        )
        return user

    # ---------------------------------------------------------- lifecycle ops
    @staticmethod
    def create_user(
        db: Session, actor: User, username: str, full_name: str, role: Role,
        access_scope: str = "INTERNAL", request_id: Optional[str] = None,
    ) -> Tuple[User, str]:
        uname = (username or "").strip().lower()
        if not USERNAME_RE.match(uname):
            raise ValueError("Username must be 3-32 chars: lowercase letters, digits, '.', '_' or '-', starting with a letter.")
        if UserService.get_by_username(db, uname):
            raise ValueError(f"Username '{uname}' already exists.")
        if access_scope not in ACCESS_SCOPES:
            raise ValueError(f"access_scope must be one of {ACCESS_SCOPES}")
        temp_pw = UserService.generate_temporary_password()
        u = User(
            user_id=f"USR-{uuid.uuid4().hex[:10].upper()}",
            username=uname,
            full_name=full_name.strip() or uname,
            role=role.value,
            access_scope=access_scope,
            status="ACTIVE",
            password_hash=hash_password(temp_pw),
            must_change_password=True,
            created_by=actor.username,
            created_at=utc_now_iso(),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        PlatformAuditService.record(
            db, "GOVERNANCE", actor=actor.username, actor_role=actor.role, action="USER_CREATED",
            target=uname, details={"role": role.value, "access_scope": access_scope}, request_id=request_id,
        )
        return u, temp_pw

    @staticmethod
    def change_role(db: Session, actor: User, target: User, new_role: Role, request_id: Optional[str] = None) -> User:
        if target.user_id == actor.user_id:
            raise PermissionError("Administrators cannot change their own role.")
        if target.role == Role.ADMINISTRATOR.value and new_role != Role.ADMINISTRATOR \
                and UserService.count_active_admins(db) <= 1:
            raise PermissionError("Cannot remove the last active administrator.")
        before = target.role
        if before == new_role.value:
            return target
        target.role = new_role.value
        target.token_version = (target.token_version or 1) + 1  # revoke sessions
        db.commit()
        PlatformAuditService.record(
            db, "GOVERNANCE", actor=actor.username, actor_role=actor.role, action="USER_ROLE_CHANGED",
            target=target.username, details={"before": before, "after": new_role.value}, request_id=request_id,
        )
        return target

    @staticmethod
    def set_status(db: Session, actor: User, target: User, status: str, request_id: Optional[str] = None) -> User:
        if status not in ("ACTIVE", "DISABLED"):
            raise ValueError("status must be ACTIVE or DISABLED")
        if target.user_id == actor.user_id:
            raise PermissionError("Administrators cannot disable their own account.")
        if status == "DISABLED" and target.role == Role.ADMINISTRATOR.value \
                and UserService.count_active_admins(db) <= 1:
            raise PermissionError("Cannot disable the last active administrator.")
        before = target.status
        if before == status:
            return target
        target.status = status
        target.token_version = (target.token_version or 1) + 1
        if status == "ACTIVE":
            target.failed_attempts = 0
            target.locked_until = None
        db.commit()
        PlatformAuditService.record(
            db, "GOVERNANCE", actor=actor.username, actor_role=actor.role,
            action="USER_DISABLED" if status == "DISABLED" else "USER_ENABLED",
            target=target.username, details={"before": before, "after": status}, request_id=request_id,
        )
        return target

    @staticmethod
    def reset_password(db: Session, actor: User, target: User, request_id: Optional[str] = None) -> str:
        temp_pw = UserService.generate_temporary_password()
        target.password_hash = hash_password(temp_pw)
        target.must_change_password = True
        target.failed_attempts = 0
        target.locked_until = None
        target.token_version = (target.token_version or 1) + 1
        db.commit()
        PlatformAuditService.record(
            db, "GOVERNANCE", actor=actor.username, actor_role=actor.role, action="USER_PASSWORD_RESET",
            target=target.username, request_id=request_id,
        )
        return temp_pw

    @staticmethod
    def change_own_password(db: Session, user: User, current: str, new: str, request_id: Optional[str] = None) -> User:
        if not verify_password(current, user.password_hash):
            PlatformAuditService.record(
                db, "AUTH", actor=user.username, actor_role=user.role, action="PASSWORD_CHANGE_FAILED",
                result="FAILURE", request_id=request_id,
            )
            raise AuthError("INVALID_CREDENTIALS", "Current password is incorrect.")
        if current == new:
            raise ValueError("New password must differ from the current one.")
        UserService.validate_password(new)
        user.password_hash = hash_password(new)
        user.must_change_password = False
        user.token_version = (user.token_version or 1) + 1
        db.commit()
        PlatformAuditService.record(
            db, "AUTH", actor=user.username, actor_role=user.role, action="PASSWORD_CHANGED",
            request_id=request_id,
        )
        return user

    @staticmethod
    def serialize(u: User) -> dict:
        return {
            "user_id": u.user_id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "access_scope": u.access_scope,
            "status": u.status,
            "locked": bool(u.locked_until and datetime.fromisoformat(u.locked_until) > datetime.now(timezone.utc)),
            "must_change_password": bool(u.must_change_password),
            "created_by": u.created_by,
            "created_at": u.created_at,
            "last_login_at": u.last_login_at,
            "is_demo_account": bool(u.is_demo_account),
        }
