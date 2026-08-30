from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.controller import AgentInvestigationController, investigations_by_case
from app.agents.schemas import InvestigationResult

router = APIRouter(prefix="/api/investigations", tags=["AI Investigations"])


@router.post("/{case_id}", response_model=InvestigationResult)
def start_case_investigation(case_id: str, db: Session = Depends(get_db)) -> InvestigationResult:
    """Triggers an AI-powered read-only investigation on the reconciliation case."""
    try:
        controller = AgentInvestigationController(db)
        result: InvestigationResult = controller.run_investigation(case_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed to initialize: {str(e)}"
        )


@router.get("/{case_id}", response_model=InvestigationResult)
def get_case_investigation(case_id: str) -> InvestigationResult:
    """Retrieves the latest completed/escalated AI investigation result for a specific case_id."""
    runs = investigations_by_case.get(case_id)
    if not runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No investigation history found for case_id '{case_id}'."
        )
    # Return the latest run
    return runs[-1]
