import datetime
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_INVESTIGATION_REQUIRED = "MORE_INVESTIGATION_REQUIRED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


class ReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INVESTIGATION = "REQUEST_MORE_INVESTIGATION"


class HumanReviewSchema(BaseModel):
    review_id: str
    case_id: str
    investigation_id: str
    status: str
    assigned_to: Optional[str] = None
    review_reason: str
    confidence: float
    risk_level: str
    recommended_action: str
    policy_decision: str
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    created_at: str
    updated_at: str
    decided_at: Optional[str] = None

    @classmethod
    def from_model(cls, review: Any) -> "HumanReviewSchema":
        return cls(
            review_id=review.review_id,
            case_id=review.case_id,
            investigation_id=review.investigation_id,
            status=review.status,
            assigned_to=review.assigned_to,
            review_reason=review.review_reason,
            confidence=float(review.confidence),
            risk_level=review.risk_level,
            recommended_action=review.recommended_action,
            policy_decision=review.policy_decision,
            decision=review.decision,
            decision_reason=review.decision_reason,
            created_at=review.created_at.isoformat() if review.created_at else "",
            updated_at=review.updated_at.isoformat() if review.updated_at else "",
            decided_at=review.decided_at.isoformat() if review.decided_at else None
        )


class DecisionRequest(BaseModel):
    reviewer_id: str = Field(default="human_reviewer", description="ID of the reviewer making the decision")
    reason: str = Field(description="Required reason or comment for the decision")


class AuditEventSchema(BaseModel):
    audit_event_id: str
    timestamp: str
    case_id: str
    investigation_id: Optional[str] = None
    review_id: Optional[str] = None
    event_type: str
    actor_type: str
    actor_id: Optional[str] = None
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    details: Optional[Any] = None
    result: Optional[str] = None

    @classmethod
    def from_model(cls, event: Any) -> "AuditEventSchema":
        details = event.details
        if details and isinstance(details, str):
            try:
                import json
                details = json.loads(details)
            except Exception:
                pass
        return cls(
            audit_event_id=event.audit_event_id,
            timestamp=event.timestamp.isoformat() if event.timestamp else "",
            case_id=event.case_id,
            investigation_id=event.investigation_id,
            review_id=event.review_id,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            previous_state=event.previous_state,
            new_state=event.new_state,
            details=details,
            result=event.result
        )
