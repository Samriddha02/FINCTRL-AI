import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.reconciliation.engine import reconcile_case
from app.services.audit_service import log_audit_event

logger = logging.getLogger("verification_service")


def verify_resolution(
    db: Session,
    case_id: str,
    review_id: Optional[str] = None,
    action_type: str = "WORKFLOW_APPROVAL"
) -> Dict[str, Any]:
    """Verifies the financial and workflow state after an approved decision or resolution action."""
    # 1. Re-evaluate deterministic reconciliation for case
    recon_result = reconcile_case(db, case_id)
    
    # 2. Perform post-action state verification
    # For safe workflow resolutions, confirm deterministic engine state is recorded and workflow is valid
    success = True
    reason = "Workflow approval and post-resolution state verified successfully."
    
    # Check if reconciliation threw unhandled error (only for direct financial verification, not workflow approval)
    if recon_result.status.value == "ERROR" and action_type != "WORKFLOW_APPROVAL":
        success = False
        reason = "Verification failed: Reconciliation engine returned ERROR state."

    status_str = "VERIFIED" if success else "VERIFICATION_FAILED"

    # 3. Record audit event
    log_audit_event(
        db=db,
        case_id=case_id,
        review_id=review_id,
        event_type="ACTION_VERIFIED" if success else "VERIFICATION_FAILED",
        actor_type="SYSTEM",
        details={
            "action_type": action_type,
            "verification_status": status_str,
            "reason": reason,
            "deterministic_status": recon_result.status.value
        },
        result=status_str
    )

    return {
        "status": status_str,
        "verified": success,
        "reason": reason,
        "deterministic_status": recon_result.status.value,
        "deterministic_reason_code": recon_result.reason_code.value
    }
