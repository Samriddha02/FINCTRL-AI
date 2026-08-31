import uuid
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.human_review import HumanReview
from app.agents.policy import evaluate_confidence_and_risk, PolicyDecision
from app.services.audit_service import log_audit_event
from app.services.verification_service import verify_resolution


ALLOWED_STATE_TRANSITIONS = {
    "PENDING": ["IN_REVIEW", "APPROVED", "REJECTED", "MORE_INVESTIGATION_REQUIRED", "ESCALATED"],
    "IN_REVIEW": ["APPROVED", "REJECTED", "MORE_INVESTIGATION_REQUIRED", "ESCALATED"],
    "ESCALATED": ["IN_REVIEW", "APPROVED", "REJECTED", "MORE_INVESTIGATION_REQUIRED"],
    "MORE_INVESTIGATION_REQUIRED": ["PENDING", "IN_REVIEW"],
    "APPROVED": ["COMPLETED"],
    "REJECTED": [],
    "COMPLETED": []
}


def create_or_get_review(
    db: Session,
    case_id: str,
    investigation_result: Any
) -> HumanReview:
    """Creates a persistent human review requirement or updates existing pending review."""
    # Evaluate policy
    policy_res = evaluate_confidence_and_risk(investigation_result)

    # Check for existing active review for this case
    existing = (
        db.query(HumanReview)
        .filter(HumanReview.case_id == case_id)
        .filter(HumanReview.status.in_(["PENDING", "IN_REVIEW", "ESCALATED"]))
        .first()
    )
    if existing:
        # Update existing review with latest investigation
        existing.investigation_id = str(getattr(investigation_result, "investigation_id", existing.investigation_id))
        existing.confidence = float(getattr(investigation_result, "root_cause_confidence", existing.confidence))
        existing.policy_decision = policy_res.policy_decision.value
        existing.risk_level = policy_res.risk_level.value
        existing.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Extract recommended action text
    actions = getattr(investigation_result, "recommended_actions", [])
    rec_text = actions[0].action if actions else "Manual review required for reconciliation discrepancy."
    summary = str(getattr(investigation_result, "summary", "Review required."))

    review_id = f"REV-{uuid.uuid4().hex[:10].upper()}"
    review_status = "ESCALATED" if policy_res.policy_decision == PolicyDecision.ESCALATION_REQUIRED else "PENDING"

    review = HumanReview(
        review_id=review_id,
        case_id=case_id,
        investigation_id=str(getattr(investigation_result, "investigation_id", "")),
        status=review_status,
        review_reason=summary,
        confidence=float(getattr(investigation_result, "root_cause_confidence", 0.0)),
        risk_level=policy_res.risk_level.value,
        recommended_action=rec_text,
        policy_decision=policy_res.policy_decision.value,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Log audit event
    log_audit_event(
        db=db,
        case_id=case_id,
        investigation_id=review.investigation_id,
        review_id=review.review_id,
        event_type="HUMAN_REVIEW_CREATED",
        actor_type="SYSTEM",
        new_state=review.status,
        details={
            "risk_level": review.risk_level,
            "policy_decision": review.policy_decision,
            "confidence": float(review.confidence)
        }
    )

    return review


def get_review(db: Session, review_id: str) -> Optional[HumanReview]:
    """Retrieve review by review_id."""
    return db.query(HumanReview).filter(HumanReview.review_id == review_id).first()


def list_reviews(
    db: Session,
    status_filter: Optional[str] = None,
    case_id: Optional[str] = None
) -> List[HumanReview]:
    """List human review records."""
    query = db.query(HumanReview)
    if status_filter:
        query = query.filter(HumanReview.status == status_filter)
    if case_id:
        query = query.filter(HumanReview.case_id == case_id)
    return query.order_by(HumanReview.created_at.desc()).all()


def approve_review(
    db: Session,
    review_id: str,
    reviewer_id: str = "human_reviewer",
    decision_reason: str = "Approved after reviewing evidence"
) -> Dict[str, Any]:
    """Approve a human review workflow decision."""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' not found."
        )

    # State transition validation
    if review.status in ["APPROVED", "COMPLETED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: Review '{review_id}' is already in terminal state '{review.status}'."
        )
    if review.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: Rejected review cannot be approved."
        )
    if not decision_reason or not decision_reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision reason is required for approval."
        )

    prev_state = review.status
    now = datetime.datetime.utcnow()

    # Update review decision
    review.status = "APPROVED"
    review.decision = "APPROVE"
    review.decision_reason = decision_reason.strip()
    review.assigned_to = reviewer_id
    review.decided_at = now
    review.updated_at = now
    db.commit()

    # Audit log
    log_audit_event(
        db=db,
        case_id=review.case_id,
        investigation_id=review.investigation_id,
        review_id=review.review_id,
        event_type="HUMAN_APPROVED",
        actor_type="HUMAN_REVIEWER",
        actor_id=reviewer_id,
        previous_state=prev_state,
        new_state="APPROVED",
        details={"decision_reason": decision_reason}
    )

    # Action execution check (Safe Read-Only Workflow Mode)
    # Record workflow decision; financial mutations are marked NOT_EXECUTED for safety
    log_audit_event(
        db=db,
        case_id=review.case_id,
        review_id=review.review_id,
        event_type="ACTION_REQUESTED",
        actor_type="HUMAN_REVIEWER",
        actor_id=reviewer_id,
        details={"action": review.recommended_action}
    )

    log_audit_event(
        db=db,
        case_id=review.case_id,
        review_id=review.review_id,
        event_type="ACTION_NOT_EXECUTED",
        actor_type="SYSTEM",
        details={
            "action": review.recommended_action,
            "reason": "Safe read-only workflow mode: direct financial mutations require explicit core bank integration."
        },
        result="NOT_EXECUTED"
    )

    # Post-action verification
    verify_res = verify_resolution(db, review.case_id, review_id=review.review_id, action_type="WORKFLOW_APPROVAL")

    review.status = "COMPLETED" if verify_res["verified"] else "ESCALATED"
    review.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(review)

    log_audit_event(
        db=db,
        case_id=review.case_id,
        review_id=review.review_id,
        event_type="CASE_COMPLETED" if verify_res["verified"] else "CASE_ESCALATED",
        actor_type="SYSTEM",
        previous_state="APPROVED",
        new_state=review.status,
        result=review.status
    )

    return {
        "review_id": review.review_id,
        "case_id": review.case_id,
        "status": review.status,
        "decision": review.decision,
        "decision_reason": review.decision_reason,
        "execution_status": "NOT_EXECUTED",
        "execution_reason": "Safe read-only workflow mode: direct financial mutations require explicit core bank integration.",
        "verification": verify_res
    }


def reject_review(
    db: Session,
    review_id: str,
    reviewer_id: str = "human_reviewer",
    decision_reason: str = "Rejected recommendation"
) -> Dict[str, Any]:
    """Reject a human review recommendation."""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' not found."
        )

    if review.status in ["COMPLETED", "REJECTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: Review '{review_id}' is already in terminal state '{review.status}'."
        )
    if not decision_reason or not decision_reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision reason is required for rejection."
        )

    prev_state = review.status
    now = datetime.datetime.utcnow()

    review.status = "REJECTED"
    review.decision = "REJECT"
    review.decision_reason = decision_reason.strip()
    review.assigned_to = reviewer_id
    review.decided_at = now
    review.updated_at = now
    db.commit()
    db.refresh(review)

    log_audit_event(
        db=db,
        case_id=review.case_id,
        investigation_id=review.investigation_id,
        review_id=review.review_id,
        event_type="HUMAN_REJECTED",
        actor_type="HUMAN_REVIEWER",
        actor_id=reviewer_id,
        previous_state=prev_state,
        new_state="REJECTED",
        details={"decision_reason": decision_reason}
    )

    log_audit_event(
        db=db,
        case_id=review.case_id,
        review_id=review.review_id,
        event_type="CASE_COMPLETED",
        actor_type="SYSTEM",
        previous_state=prev_state,
        new_state="REJECTED",
        result="REJECTED"
    )

    return {
        "review_id": review.review_id,
        "case_id": review.case_id,
        "status": review.status,
        "decision": review.decision,
        "decision_reason": review.decision_reason
    }


def request_more_investigation(
    db: Session,
    review_id: str,
    reviewer_id: str = "human_reviewer",
    decision_reason: str = "Requested additional evidence and investigation"
) -> Dict[str, Any]:
    """Request more investigation for a case."""
    review = get_review(db, review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review '{review_id}' not found."
        )

    if review.status in ["COMPLETED", "APPROVED", "REJECTED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transition: Review '{review_id}' is in terminal state '{review.status}'."
        )
    if not decision_reason or not decision_reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision reason is required for requesting more investigation."
        )

    prev_state = review.status
    now = datetime.datetime.utcnow()

    review.status = "MORE_INVESTIGATION_REQUIRED"
    review.decision = "REQUEST_MORE_INVESTIGATION"
    review.decision_reason = decision_reason.strip()
    review.assigned_to = reviewer_id
    review.decided_at = now
    review.updated_at = now
    db.commit()

    log_audit_event(
        db=db,
        case_id=review.case_id,
        investigation_id=review.investigation_id,
        review_id=review.review_id,
        event_type="MORE_INVESTIGATION_REQUESTED",
        actor_type="HUMAN_REVIEWER",
        actor_id=reviewer_id,
        previous_state=prev_state,
        new_state="MORE_INVESTIGATION_REQUIRED",
        details={"decision_reason": decision_reason}
    )

    # Re-run Phase 6 Agent Investigation Controller
    from app.agents.controller import AgentInvestigationController
    controller = AgentInvestigationController(db)
    new_investigation = controller.run_investigation(review.case_id)

    # Create new review linked to new investigation
    new_review = create_or_get_review(db, review.case_id, new_investigation)

    return {
        "previous_review_id": review.review_id,
        "new_review_id": new_review.review_id,
        "case_id": review.case_id,
        "status": new_review.status,
        "new_investigation": new_investigation
    }
