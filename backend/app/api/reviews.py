from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.controller import AgentInvestigationController, investigations_by_case
from app.agents.policy import evaluate_confidence_and_risk
from app.services.review_service import (
    create_or_get_review,
    get_review,
    list_reviews,
    approve_review,
    reject_review,
    request_more_investigation,
)
from app.api.schemas_phase8 import HumanReviewSchema, DecisionRequest
from app.agents.tools import validate_id

router = APIRouter(prefix="/api/reviews", tags=["Human Review"])


@router.post("/{case_id}", response_model=HumanReviewSchema)
def create_review_for_case(case_id: str, db: Session = Depends(get_db)) -> HumanReviewSchema:
    """Creates a human review for a case. Runs investigation if not already done."""
    try:
        validate_id(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for existing investigation or run one
    runs = investigations_by_case.get(case_id)
    if runs:
        investigation = runs[-1]
    else:
        controller = AgentInvestigationController(db)
        investigation = controller.run_investigation(case_id)

    review = create_or_get_review(db, case_id, investigation)
    return HumanReviewSchema.from_model(review)


@router.get("", response_model=List[HumanReviewSchema])
def list_all_reviews(
    status: Optional[str] = Query(None, description="Filter by status"),
    case_id: Optional[str] = Query(None, description="Filter by case_id"),
    db: Session = Depends(get_db)
) -> List[HumanReviewSchema]:
    """List all human review records, optionally filtered."""
    reviews = list_reviews(db, status_filter=status, case_id=case_id)
    return [HumanReviewSchema.from_model(r) for r in reviews]


@router.get("/{review_id}", response_model=HumanReviewSchema)
def get_review_by_id(review_id: str, db: Session = Depends(get_db)) -> HumanReviewSchema:
    """Get a specific human review by review_id."""
    try:
        validate_id(review_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    review = get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found.")
    return HumanReviewSchema.from_model(review)


@router.post("/{review_id}/approve", response_model=Dict[str, Any])
def approve_human_review(
    review_id: str,
    decision_req: DecisionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Approve a human review recommendation."""
    try:
        validate_id(review_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return approve_review(db, review_id, decision_req.reviewer_id, decision_req.reason)


@router.post("/{review_id}/reject", response_model=Dict[str, Any])
def reject_human_review(
    review_id: str,
    decision_req: DecisionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Reject a human review recommendation."""
    try:
        validate_id(review_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return reject_review(db, review_id, decision_req.reviewer_id, decision_req.reason)


@router.post("/{review_id}/request-more-investigation", response_model=Dict[str, Any])
def request_more_investigation_endpoint(
    review_id: str,
    decision_req: DecisionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Request more investigation for a case under review."""
    try:
        validate_id(review_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return request_more_investigation(db, review_id, decision_req.reviewer_id, decision_req.reason)
