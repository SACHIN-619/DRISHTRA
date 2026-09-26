"""
DRISHTRA Case and Contributor API Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.all_schemas import CaseCreate, CaseResponse, ContributorCreate, ContributorResponse
from app.services.case_service import CaseService, ContributorService

router = APIRouter(prefix="/api/v1", tags=["Cases & Contributors"])

# --- CASES ---
@router.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)):
    return CaseService.create_case(db, case_in)

@router.get("/cases", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db)):
    return CaseService.list_cases(db)

@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = CaseService.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case

# --- CONTRIBUTORS ---
@router.post("/contributors", response_model=ContributorResponse, status_code=status.HTTP_201_CREATED)
def register_contributor(contrib_in: ContributorCreate, db: Session = Depends(get_db)):
    return ContributorService.register_contributor(db, contrib_in)

@router.get("/cases/{case_id}/contributors", response_model=List[ContributorResponse])
def list_contributors(case_id: str, db: Session = Depends(get_db)):
    return ContributorService.get_contributors_by_case(db, case_id)
