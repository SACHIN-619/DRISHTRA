"""
Platform event ledger: identity lifecycle, authentication and authorization events.

Every row is hash-chained to the previous one:
    H_n = SHA256(H_{n-1} || canonical(event_n))
so deleting, inserting or editing any row breaks verification from that point on.
This ledger is append-only: no service method updates or deletes rows.
"""
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.crypto.chain import GENESIS_HASH, compute_chained_hash
from app.db.models import PlatformEvent, utc_now_iso


class PlatformAuditService:
    CATEGORIES = {"GOVERNANCE", "AUTH", "AUTHZ"}

    @staticmethod
    def _payload(e: PlatformEvent) -> Dict[str, Any]:
        return {
            "event_id": e.event_id,
            "sequence": e.sequence,
            "category": e.category,
            "actor": e.actor,
            "actor_role": e.actor_role,
            "action": e.action,
            "target": e.target,
            "result": e.result,
            "details": json.loads(e.details_json or "{}"),
            "request_id": e.request_id,
            "timestamp": e.timestamp,
            "previous_event_hash": e.previous_event_hash,
        }

    @staticmethod
    def record(
        db: Session,
        category: str,
        actor: str,
        action: str,
        result: str = "SUCCESS",
        actor_role: Optional[str] = None,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> PlatformEvent:
        # Column limits are enforced by PostgreSQL (not by SQLite). Values such as a
        # submitted username on a failed login are attacker-controlled, so clip them.
        actor = (actor or "anonymous")[:128]
        target = target[:128] if target else target
        action = action[:64]
        last = db.query(PlatformEvent).order_by(PlatformEvent.sequence.desc()).first()
        prev_hash = last.event_hash if last else GENESIS_HASH
        seq = (last.sequence + 1) if last else 1
        ev = PlatformEvent(
            event_id=f"PEV-{uuid.uuid4().hex[:12].upper()}",
            sequence=seq,
            category=category,
            actor=actor,
            actor_role=actor_role,
            action=action,
            target=target,
            result=result,
            details_json=json.dumps(details or {}, sort_keys=True),
            request_id=request_id,
            timestamp=utc_now_iso(),
            previous_event_hash=prev_hash,
            event_hash="",
        )
        ev.event_hash = compute_chained_hash(prev_hash, PlatformAuditService._payload(ev))
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def list_events(
        db: Session,
        categories: Optional[List[str]] = None,
        limit: int = 200,
    ) -> List[PlatformEvent]:
        q = db.query(PlatformEvent)
        if categories:
            q = q.filter(PlatformEvent.category.in_(categories))
        return q.order_by(PlatformEvent.sequence.desc()).limit(limit).all()

    @staticmethod
    def verify(db: Session) -> Dict[str, Any]:
        events = db.query(PlatformEvent).order_by(PlatformEvent.sequence.asc()).all()
        expected_prev = GENESIS_HASH
        for idx, e in enumerate(events):
            if e.previous_event_hash != expected_prev:
                return {
                    "status": "BROKEN",
                    "verified_count": idx,
                    "total": len(events),
                    "failure_sequence": e.sequence,
                    "reason": "previous_event_hash does not link to the prior event",
                }
            recomputed = compute_chained_hash(e.previous_event_hash, PlatformAuditService._payload(e))
            if recomputed != e.event_hash:
                return {
                    "status": "BROKEN",
                    "verified_count": idx,
                    "total": len(events),
                    "failure_sequence": e.sequence,
                    "reason": "event content does not match its recorded hash",
                }
            expected_prev = e.event_hash
        return {
            "status": "VALID",
            "verified_count": len(events),
            "total": len(events),
            "head_hash": expected_prev,
        }

    @staticmethod
    def serialize(e: PlatformEvent) -> Dict[str, Any]:
        d = PlatformAuditService._payload(e)
        d["event_hash"] = e.event_hash
        return d
