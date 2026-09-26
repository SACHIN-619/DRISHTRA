"""
DRISHTRA Case and Contributor Management Services
"""
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.models import Case, Contributor, utc_now_iso
from app.schemas.all_schemas import CaseCreate, ContributorCreate
from app.services.audit_service import AuditService

class CaseService:
    @staticmethod
    def create_case(db: Session, case_in: CaseCreate, actor: str = "analyst") -> Case:
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        case = Case(
            case_id=case_id,
            name=case_in.name,
            description=case_in.description,
            classification=case_in.classification,
            status="ACTIVE",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso()
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        AuditService.record_event(
            db=db,
            case_id=case_id,
            actor=actor,
            action="CASE_CREATED",
            asset_id=case_id,
            result="SUCCESS",
            reason=f"Initialized sovereign CV assurance case '{case.name}'"
        )
        return case

    @staticmethod
    def get_case(db: Session, case_id: str) -> Optional[Case]:
        return db.query(Case).filter(Case.case_id == case_id).first()

    @staticmethod
    def list_cases(db: Session) -> List[Case]:
        return db.query(Case).order_by(Case.created_at.desc()).all()


class ContributorService:
    @staticmethod
    def register_contributor(db: Session, contrib_in: ContributorCreate, actor: str = "analyst") -> Contributor:
        contrib_id = f"C-{uuid.uuid4().hex[:6].upper()}"
        contributor = Contributor(
            contributor_id=contrib_id,
            case_id=contrib_in.case_id,
            name=contrib_in.name,
            contributor_type=contrib_in.contributor_type,
            public_key=contrib_in.public_key,
            metadata_json=json.dumps(contrib_in.metadata_json or {}),
            registered_at=utc_now_iso()
        )
        db.add(contributor)
        db.commit()
        db.refresh(contributor)

        AuditService.record_event(
            db=db,
            case_id=contrib_in.case_id,
            actor=actor,
            action="CONTRIBUTOR_REGISTERED",
            asset_id=contrib_id,
            result="SUCCESS",
            reason=f"Registered source entity '{contributor.name}' ({contributor.contributor_type})"
        )
        return contributor

    @staticmethod
    def get_contributors_by_case(db: Session, case_id: str) -> List[Contributor]:
        return db.query(Contributor).filter(Contributor.case_id == case_id).all()
