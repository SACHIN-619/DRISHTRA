"""
Authentication endpoints.

  POST /api/v1/auth/token            sign in with username + password (no role in the request)
  GET  /api/v1/auth/me               current identity, role mission and permissions
  POST /api/v1/auth/change-password  change own password (also completes first-login setup)
  POST /api/v1/auth/logout           revoke all of the caller's sessions
  GET  /api/v1/auth/roles            role catalogue (authenticated)

There is no self-registration endpoint. Accounts are created by an
ADMINISTRATOR through /api/v1/users.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.rbac import RBACService, Role
from app.core.security import (
    TokenData, get_current_user, get_current_user_allow_pending, issue_token_for,
)
from app.db.database import get_db
from app.db.models import User
from app.services.platform_audit_service import PlatformAuditService
from app.services.user_service import AuthError, UserService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=256)


def _profile(user: User) -> dict:
    role = Role(user.role)
    caps = RBACService.get_role_capabilities(role)
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "access_scope": user.access_scope,
        "must_change_password": bool(user.must_change_password),
        "last_login_at": user.last_login_at,
        "is_demo_account": bool(user.is_demo_account),
        "capabilities": caps,
        "permissions": caps["permissions"],
    }


@router.post("/token")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user = UserService.authenticate(
            db, req.username, req.password, request_id=getattr(request.state, "request_id", None)
        )
    except AuthError as e:
        status_code = 423 if e.code == "ACCOUNT_LOCKED" else 401
        raise HTTPException(status_code=status_code, detail=e.message)
    token = issue_token_for(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _profile(user),
        # kept for older clients
        "role": user.role,
        "username": user.username,
        "permissions": RBACService.permissions_for(Role(user.role)),
    }


@router.get("/me")
def me(user: TokenData = Depends(get_current_user_allow_pending), db: Session = Depends(get_db)):
    u = UserService.get(db, user.user_id)
    return _profile(u)


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    user: TokenData = Depends(get_current_user_allow_pending),
    db: Session = Depends(get_db),
):
    u = UserService.get(db, user.user_id)
    try:
        UserService.change_own_password(
            db, u, req.current_password, req.new_password,
            request_id=getattr(request.state, "request_id", None),
        )
    except AuthError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Old tokens were revoked by the token_version bump; hand back a fresh one.
    return {"access_token": issue_token_for(u), "token_type": "bearer", "user": _profile(u)}


@router.post("/logout")
def logout(request: Request, user: TokenData = Depends(get_current_user_allow_pending), db: Session = Depends(get_db)):
    u = UserService.get(db, user.user_id)
    u.token_version = (u.token_version or 1) + 1
    db.commit()
    PlatformAuditService.record(
        db, "AUTH", actor=u.username, actor_role=u.role, action="LOGOUT",
        request_id=getattr(request.state, "request_id", None),
    )
    return {"status": "SIGNED_OUT"}


@router.get("/roles")
def list_roles(user: TokenData = Depends(get_current_user)):
    return {r.value: RBACService.get_role_capabilities(r) for r in Role}
