"""
DRISHTRA authentication and authorization dependencies.

Rules enforced here:
  1. Every protected endpoint requires a valid Bearer token. There is no
     anonymous or "default operator" fallback.
  2. The token only identifies the user (sub + token version). The role is
     re-read from the users table on every request, so a role change or a
     disabled account takes effect immediately.
  3. Permission checks consult the RBAC matrix only. No role bypasses it.
  4. Accounts with a temporary password can do nothing except read their
     profile and change the password.
  5. Every denial is written to the platform ledger.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rbac import Permission, RBACService, Role
from app.core.passwords import hash_password as get_password_hash  # noqa: F401  (re-export)
from app.core.passwords import verify_password  # noqa: F401  (re-export)
from app.db.database import get_db


class TokenData(BaseModel):
    user_id: str
    username: str
    full_name: str = ""
    role: Role
    access_scope: str = "INTERNAL"
    must_change_password: bool = False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    to_encode.update({
        "iat": now,
        "exp": now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        "iss": "drishtra",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def issue_token_for(user) -> str:
    # The role is included only as a UI hint; authorization never trusts it.
    return create_access_token({"sub": user.user_id, "tv": user.token_version or 1, "role_hint": user.role})


security_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> TokenData:
    from app.db.models import User  # local import avoids a circular import at startup

    if not credentials or not credentials.credentials:
        raise _unauthorized("Authentication required.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM], issuer="drishtra",
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Session expired. Please sign in again.")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid authentication token.")

    user = db.query(User).filter(User.user_id == payload.get("sub")).first()
    if not user:
        raise _unauthorized("Account no longer exists.")
    if user.status != "ACTIVE":
        raise _unauthorized("Account disabled.")
    if int(payload.get("tv", 0)) != int(user.token_version or 1):
        raise _unauthorized("Session revoked. Please sign in again.")
    try:
        role = Role(user.role)
    except ValueError:
        raise _unauthorized("Account has an unknown role.")

    td = TokenData(
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        role=role,
        access_scope=user.access_scope or "INTERNAL",
        must_change_password=bool(user.must_change_password),
    )
    request.state.user = td
    return td


def get_current_user_allow_pending(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> TokenData:
    """Authenticated user, even if they still must change a temporary password."""
    return _resolve_user(request, credentials, db)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db),
) -> TokenData:
    """Authenticated user with a usable (non-temporary) password."""
    user = _resolve_user(request, credentials, db)
    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required before using DRISHTRA.",
        )
    return user


def _deny(request: Request, db: Session, user: TokenData, needed: str) -> HTTPException:
    from app.services.platform_audit_service import PlatformAuditService
    try:
        PlatformAuditService.record(
            db, "AUTHZ", actor=user.username, actor_role=user.role.value,
            action="ACCESS_DENIED", result="DENIED",
            target=f"{request.method} {request.url.path}",
            details={"required": needed},
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception:
        pass
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Your role ({user.role.value}) is not permitted to perform this action (requires {needed}).",
    )


def require_permission(required_perm: Permission):
    def perm_checker(
        request: Request,
        user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TokenData:
        if not RBACService.has_permission(user.role, required_perm):
            raise _deny(request, db, user, required_perm.value)
        return user
    return perm_checker


def require_role(allowed_roles: List[Role]):
    def role_checker(
        request: Request,
        user: TokenData = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TokenData:
        if user.role not in allowed_roles:
            raise _deny(request, db, user, "role in " + ",".join(r.value for r in allowed_roles))
        return user
    return role_checker
