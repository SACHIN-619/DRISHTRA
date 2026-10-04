"""
User administration (ADMINISTRATOR only) and platform governance views.

  GET   /api/v1/users                          list accounts
  POST  /api/v1/users                          create account (returns a one-time temporary password)
  PATCH /api/v1/users/{user_id}/role           change role (revokes sessions)
  PATCH /api/v1/users/{user_id}/status         enable / disable (revokes sessions)
  POST  /api/v1/users/{user_id}/reset-password issue a new temporary password

  GET   /api/v1/platform/events                hash-chained platform ledger
  POST  /api/v1/platform/events/verify         recompute the platform chain
  GET   /api/v1/platform/security-summary      auth / authz counters for the security view
"""
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.rbac import Permission, RBACService, Role
from app.core.security import TokenData, require_permission
from app.db.database import get_db
from app.db.models import PlatformEvent, User
from app.services.platform_audit_service import PlatformAuditService
from app.services.user_service import ACCESS_SCOPES, UserService

router = APIRouter(tags=["Administration & Governance"])


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: Role
    access_scope: str = "INTERNAL"


class RoleChangeRequest(BaseModel):
    role: Role


class StatusChangeRequest(BaseModel):
    status: str


def _actor(db: Session, user: TokenData) -> User:
    return UserService.get(db, user.user_id)


def _target(db: Session, user_id: str) -> User:
    t = UserService.get(db, user_id)
    if not t:
        raise HTTPException(status_code=404, detail="User not found")
    return t


def _rid(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


@router.get("/api/v1/users")
def list_users(
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.USER_MANAGE)),
):
    users = db.query(User).order_by(User.created_at.asc()).all()
    return {
        "users": [UserService.serialize(u) for u in users],
        "roles": {r.value: RBACService.get_role_capabilities(r) for r in Role},
        "access_scopes": ACCESS_SCOPES,
    }


@router.post("/api/v1/users", status_code=201)
def create_user(
    req: CreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.USER_MANAGE)),
):
    try:
        u, temp_pw = UserService.create_user(
            db, _actor(db, user), req.username, req.full_name, req.role, req.access_scope, _rid(request)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "user": UserService.serialize(u),
        "temporary_password": temp_pw,
        "note": "Shown once. The user must change it at first sign-in.",
    }


@router.patch("/api/v1/users/{user_id}/role")
def change_role(
    user_id: str, req: RoleChangeRequest, request: Request,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.USER_MANAGE)),
):
    try:
        t = UserService.change_role(db, _actor(db, user), _target(db, user_id), req.role, _rid(request))
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return UserService.serialize(t)


@router.patch("/api/v1/users/{user_id}/status")
def change_status(
    user_id: str, req: StatusChangeRequest, request: Request,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.USER_MANAGE)),
):
    try:
        t = UserService.set_status(db, _actor(db, user), _target(db, user_id), req.status.upper(), _rid(request))
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserService.serialize(t)


@router.post("/api/v1/users/{user_id}/reset-password")
def reset_password(
    user_id: str, request: Request,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.USER_MANAGE)),
):
    t = _target(db, user_id)
    temp_pw = UserService.reset_password(db, _actor(db, user), t, _rid(request))
    return {"user": UserService.serialize(t), "temporary_password": temp_pw, "note": "Shown once."}


# --------------------------------------------------------------------------- platform ledger

def _can_read_category(role: Role, category: str) -> bool:
    if category == "GOVERNANCE":
        return RBACService.has_permission(role, Permission.AUDIT_READ) or \
            RBACService.has_permission(role, Permission.USER_MANAGE)
    # AUTH / AUTHZ events reveal other people's sign-in behaviour: least privilege.
    return RBACService.has_permission(role, Permission.SECURITY_EVENTS_READ)


@router.get("/api/v1/platform/events")
def platform_events(
    category: Optional[List[str]] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.AUDIT_READ)),
):
    wanted = [c.upper() for c in (category or ["GOVERNANCE", "AUTH", "AUTHZ"])]
    allowed = [c for c in wanted if _can_read_category(user.role, c)]
    if not allowed:
        raise HTTPException(status_code=403, detail="Your role cannot read these event categories.")
    events = PlatformAuditService.list_events(db, allowed, limit)
    return {
        "categories": allowed,
        "events": [PlatformAuditService.serialize(e) for e in events],
    }


@router.post("/api/v1/platform/events/verify")
def verify_platform_chain(
    request: Request,
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.AUDIT_VERIFY)),
):
    result = PlatformAuditService.verify(db)
    PlatformAuditService.record(
        db, "GOVERNANCE", actor=user.username, actor_role=user.role.value,
        action="PLATFORM_CHAIN_VERIFIED", result="SUCCESS" if result["status"] == "VALID" else "FAILURE",
        details={"status": result["status"], "verified": result["verified_count"]},
        request_id=_rid(request),
    )
    return result


@router.get("/api/v1/platform/security-summary")
def security_summary(
    db: Session = Depends(get_db),
    user: TokenData = Depends(require_permission(Permission.SECURITY_EVENTS_READ)),
):
    rows = db.query(PlatformEvent).filter(PlatformEvent.category.in_(["AUTH", "AUTHZ", "GOVERNANCE"])).all()
    by_action = Counter(e.action for e in rows)
    users = db.query(User).all()
    return {
        "counts": {
            "login_succeeded": by_action.get("LOGIN_SUCCEEDED", 0),
            "login_failed": by_action.get("LOGIN_FAILED", 0),
            "account_locked": by_action.get("ACCOUNT_LOCKED", 0),
            "access_denied": by_action.get("ACCESS_DENIED", 0),
            "role_changes": by_action.get("USER_ROLE_CHANGED", 0),
            "users_created": by_action.get("USER_CREATED", 0),
            "users_disabled": by_action.get("USER_DISABLED", 0),
        },
        "accounts": {
            "total": len(users),
            "active": sum(1 for u in users if u.status == "ACTIVE"),
            "disabled": sum(1 for u in users if u.status != "ACTIVE"),
            "pending_password_change": sum(1 for u in users if u.must_change_password),
            "by_role": dict(Counter(u.role for u in users)),
        },
    }
