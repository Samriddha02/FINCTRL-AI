import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("policy_engine")

# Explicit Threshold Constants
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.70
HIGH_RISK_AMOUNT_THRESHOLD = 5000.0


class PolicyDecision(str, Enum):
    AUTO_RESOLUTION_ELIGIBLE = "AUTO_RESOLUTION_ELIGIBLE"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    NO_ACTION_ALLOWED = "NO_ACTION_ALLOWED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AllowedAction(str, Enum):
    NO_ACTION = "NO_ACTION"
    REQUEST_HUMAN_REVIEW = "REQUEST_HUMAN_REVIEW"
    REQUEST_MORE_INVESTIGATION = "REQUEST_MORE_INVESTIGATION"
    APPROVE_RECOMMENDATION = "APPROVE_RECOMMENDATION"
    REJECT_RECOMMENDATION = "REJECT_RECOMMENDATION"
    VERIFY_RESOLUTION = "VERIFY_RESOLUTION"


# Disallowed write actions
BLOCKED_FINANCIAL_ACTIONS = {
    "MOVE_MONEY",
    "ISSUE_REFUND",
    "MODIFY_SETTLEMENT",
    "MODIFY_INVOICE",
    "MODIFY_TAX_RECORD",
    "MODIFY_PAYMENT",
    "ALTER_BANK_TRANSACTION"
}

HIGH_RISK_REASON_CODES = {
    "TAX_MISMATCH",
    "CONFLICTING_RECORDS",
    "AMBIGUOUS_CASE",
    "DUPLICATE_TRANSACTION",
    "MISSING_SETTLEMENT",
    "UNKNOWN_ADJUSTMENT"
}

MEDIUM_RISK_REASON_CODES = {
    "PARTIAL_REFUND",
    "FEE_DIFFERENCE",
    "TIMING_DIFFERENCE",
    "AMOUNT_MISMATCH"
}


class PolicyEvaluationResult(BaseModel):
    policy_decision: PolicyDecision
    risk_level: RiskLevel
    risk_reasons: List[str]
    allowed_actions: List[AllowedAction]
    auto_resolution_eligible: bool
    requires_human_review: bool


def evaluate_confidence_and_risk(
    investigation_result: Any,
    recon_result: Optional[Any] = None
) -> PolicyEvaluationResult:
    """Evaluates investigation result deterministically against confidence & risk policies."""
    risk_reasons: List[str] = []
    
    confidence = float(getattr(investigation_result, "root_cause_confidence", 0.0))
    reason_code = str(getattr(investigation_result, "deterministic_reason_code", "UNKNOWN"))
    deterministic_status = str(getattr(investigation_result, "deterministic_status", "UNKNOWN"))
    warnings = getattr(investigation_result, "warnings", [])
    requires_review_flag = bool(getattr(investigation_result, "requires_human_review", True))
    
    # Calculate financial difference magnitude if recon_result available
    diff_magnitude = 0.0
    if recon_result:
        diff_magnitude = abs(float(getattr(recon_result, "difference", 0.0)))
    else:
        # Check facts in investigation_result
        facts = getattr(investigation_result, "facts", [])
        for f in facts:
            key = str(getattr(f, "key", "")).lower()
            if "diff" in key or "amount" in key:
                try:
                    diff_magnitude = max(diff_magnitude, abs(float(getattr(f, "value", 0.0))))
                except (TypeError, ValueError):
                    pass

    # Rule 1: Exact Match / Clean Reconciliation
    if deterministic_status == "MATCHED" or reason_code == "EXACT_MATCH":
        return PolicyEvaluationResult(
            policy_decision=PolicyDecision.AUTO_RESOLUTION_ELIGIBLE,
            risk_level=RiskLevel.LOW,
            risk_reasons=["Transaction reconciled with perfect match."],
            allowed_actions=[AllowedAction.VERIFY_RESOLUTION, AllowedAction.NO_ACTION],
            auto_resolution_eligible=True,
            requires_human_review=False
        )

    # Rule 2: Escalation Required (Low confidence, failed evidence, or critical risk)
    if warnings and any("failed" in str(w).lower() for w in warnings):
        risk_reasons.append("Failed evidence collection or tool execution warnings.")
        
    if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        risk_reasons.append(f"Low AI confidence score ({confidence:.2f} < threshold {MEDIUM_CONFIDENCE_THRESHOLD}).")

    if diff_magnitude > HIGH_RISK_AMOUNT_THRESHOLD:
        risk_reasons.append(f"High financial difference amount ({diff_magnitude:.2f} > threshold {HIGH_RISK_AMOUNT_THRESHOLD}).")

    if reason_code in HIGH_RISK_REASON_CODES:
        risk_reasons.append(f"High-risk anomaly reason code: '{reason_code}'.")

    # Determine decision & risk level based on risk accumulation
    if confidence < MEDIUM_CONFIDENCE_THRESHOLD or (warnings and any("failed" in str(w).lower() for w in warnings)):
        return PolicyEvaluationResult(
            policy_decision=PolicyDecision.ESCALATION_REQUIRED,
            risk_level=RiskLevel.CRITICAL if diff_magnitude > HIGH_RISK_AMOUNT_THRESHOLD else RiskLevel.HIGH,
            risk_reasons=risk_reasons,
            allowed_actions=[AllowedAction.REQUEST_HUMAN_REVIEW, AllowedAction.REQUEST_MORE_INVESTIGATION],
            auto_resolution_eligible=False,
            requires_human_review=True
        )

    # Rule 3: High Risk or Medium Confidence requires Human Review
    if (
        confidence < HIGH_CONFIDENCE_THRESHOLD or
        reason_code in HIGH_RISK_REASON_CODES or
        reason_code in MEDIUM_RISK_REASON_CODES or
        diff_magnitude > HIGH_RISK_AMOUNT_THRESHOLD or
        requires_review_flag
    ):
        level = RiskLevel.HIGH if (reason_code in HIGH_RISK_REASON_CODES or diff_magnitude > HIGH_RISK_AMOUNT_THRESHOLD) else RiskLevel.MEDIUM
        return PolicyEvaluationResult(
            policy_decision=PolicyDecision.HUMAN_REVIEW_REQUIRED,
            risk_level=level,
            risk_reasons=risk_reasons or [f"Anomaly requiring review: {reason_code}"],
            allowed_actions=[
                AllowedAction.APPROVE_RECOMMENDATION,
                AllowedAction.REJECT_RECOMMENDATION,
                AllowedAction.REQUEST_MORE_INVESTIGATION
            ],
            auto_resolution_eligible=False,
            requires_human_review=True
        )

    # Rule 4: High Confidence & Low Risk -> Auto resolution eligible
    return PolicyEvaluationResult(
        policy_decision=PolicyDecision.AUTO_RESOLUTION_ELIGIBLE,
        risk_level=RiskLevel.LOW,
        risk_reasons=["High confidence with acceptable risk boundaries."],
        allowed_actions=[AllowedAction.VERIFY_RESOLUTION, AllowedAction.NO_ACTION],
        auto_resolution_eligible=True,
        requires_human_review=False
    )
