from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.reconciliation.engine import reconcile_case, reconcile_all_cases
from app.reconciliation.models import ReconciliationResult

router = APIRouter(prefix="/api/reconciliation", tags=["Reconciliation"])


@router.get("/{case_id}", response_model=Dict[str, Any])
def get_case_reconciliation(case_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieves deterministic reconciliation result for a specific case_id."""
    result: ReconciliationResult = reconcile_case(db, case_id)
    if result.status.value == "ERROR":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reconciliation case '{case_id}' not found in operational database."
        )
    return result.to_dict()


@router.get("", response_model=Dict[str, Any])
def get_batch_reconciliation(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Runs batch reconciliation across all operational database cases and returns summary statistics."""
    results: List[ReconciliationResult] = reconcile_all_cases(db)

    breakdown: Dict[str, int] = {}
    reason_breakdown: Dict[str, int] = {}

    for r in results:
        st = r.status.value
        rc = r.reason_code.value
        breakdown[st] = breakdown.get(st, 0) + 1
        reason_breakdown[rc] = reason_breakdown.get(rc, 0) + 1

    return {
        "total_cases": len(results),
        "status_breakdown": breakdown,
        "reason_code_breakdown": reason_breakdown,
        "cases": [r.to_dict() for r in results],
    }
