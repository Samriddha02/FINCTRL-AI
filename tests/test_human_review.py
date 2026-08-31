"""
tests/test_human_review.py — Phase 8 Human Review, Confidence & Risk Policy Tests
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import MagicMock, patch
from app.agents.policy import (
    evaluate_confidence_and_risk,
    PolicyDecision,
    RiskLevel,
    AllowedAction,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    HIGH_RISK_AMOUNT_THRESHOLD,
)
from app.agents.schemas import (
    InvestigationResult,
    InvestigationStatus,
    AnalysisSource,
    FactRecord,
    RecommendedAction,
    ActionPriority,
)


def make_investigation(
    reason_code: str = "TAX_MISMATCH",
    confidence: float = 0.9,
    status: str = "ESCALATED",
    requires_human_review: bool = True,
    warnings=None
) -> InvestigationResult:
    """Build a minimal InvestigationResult for policy testing."""
    return InvestigationResult(
        investigation_id="test-inv-001",
        case_id="CASE-00001",
        investigation_status=InvestigationStatus.ESCALATED,
        deterministic_status=status if status == "MATCHED" else "MISMATCH",
        deterministic_reason_code=reason_code,
        summary="Test investigation",
        root_cause="Test root cause",
        root_cause_confidence=confidence,
        facts=[
            FactRecord(key="difference", value=100.0, source="Calculation"),
        ],
        requires_human_review=requires_human_review,
        warnings=warnings or [],
        analysis_source=AnalysisSource.DETERMINISTIC,
    )


# ============================================================
# 1. Confidence Policy Tests
# ============================================================

def test_policy_exact_match_low_risk():
    """EXACT_MATCH should yield AUTO_RESOLUTION_ELIGIBLE with LOW risk."""
    inv = make_investigation(
        reason_code="EXACT_MATCH",
        confidence=1.0,
        status="MATCHED",
        requires_human_review=False
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision == PolicyDecision.AUTO_RESOLUTION_ELIGIBLE
    assert result.risk_level == RiskLevel.LOW
    assert result.auto_resolution_eligible is True
    assert result.requires_human_review is False


def test_policy_high_confidence_medium_risk():
    """FEE_DIFFERENCE with high confidence should require HUMAN_REVIEW."""
    inv = make_investigation(
        reason_code="FEE_DIFFERENCE",
        confidence=0.9,
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision == PolicyDecision.HUMAN_REVIEW_REQUIRED
    assert result.requires_human_review is True
    assert AllowedAction.APPROVE_RECOMMENDATION in result.allowed_actions


def test_policy_low_confidence_escalation():
    """Low confidence below MEDIUM threshold should force ESCALATION."""
    inv = make_investigation(
        reason_code="AMOUNT_MISMATCH",
        confidence=0.4,
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision == PolicyDecision.ESCALATION_REQUIRED
    assert result.requires_human_review is True
    assert result.auto_resolution_eligible is False


def test_policy_high_risk_reason_code():
    """TAX_MISMATCH is a high-risk code and should require human review."""
    inv = make_investigation(
        reason_code="TAX_MISMATCH",
        confidence=0.92,
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision == PolicyDecision.HUMAN_REVIEW_REQUIRED
    assert result.risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM)
    assert result.requires_human_review is True


def test_policy_high_risk_ambiguous():
    """AMBIGUOUS_CASE with warnings should be ESCALATION_REQUIRED or HUMAN_REVIEW."""
    inv = make_investigation(
        reason_code="AMBIGUOUS_CASE",
        confidence=0.65,
        warnings=["Failed evidence collection"]
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision in (PolicyDecision.ESCALATION_REQUIRED, PolicyDecision.HUMAN_REVIEW_REQUIRED)
    assert result.requires_human_review is True


def test_policy_no_escalation_for_exact_match():
    """EXACT_MATCH should never escalate."""
    inv = make_investigation(
        reason_code="EXACT_MATCH",
        confidence=1.0,
        status="MATCHED",
        requires_human_review=False
    )
    result = evaluate_confidence_and_risk(inv)
    assert result.policy_decision != PolicyDecision.ESCALATION_REQUIRED


def test_policy_allowed_actions_escalation():
    """Escalated policy should only allow review/investigation requests."""
    inv = make_investigation(confidence=0.3, warnings=["Failed: required tool missing"])
    result = evaluate_confidence_and_risk(inv)
    assert AllowedAction.REQUEST_MORE_INVESTIGATION in result.allowed_actions
    # Should NOT include approve
    assert AllowedAction.APPROVE_RECOMMENDATION not in result.allowed_actions


# ============================================================
# 2. Review Service State Machine Tests (using DB fixture)
# ============================================================

@pytest.fixture
def db():
    """Create test DB session using SQLite in-memory."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.models.human_review import HumanReview
    from app.models.audit_event import AuditEvent
    from app.models.agent_run import AgentRun, SystemMetric

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def create_test_review(db, case_id="CASE-00001", confidence=0.85, warnings=None):
    """Helper to create a review via service."""
    from app.services.review_service import create_or_get_review
    inv = make_investigation(confidence=confidence, warnings=warnings or [])
    return create_or_get_review(db, case_id, inv)


def test_create_review(db):
    """Review should be created in PENDING or ESCALATED state."""
    review = create_test_review(db)
    assert review.review_id.startswith("REV-")
    assert review.case_id == "CASE-00001"
    assert review.status in ("PENDING", "ESCALATED", "IN_REVIEW")


def test_create_review_idempotent(db):
    """Creating a review for the same case should return the existing one."""
    r1 = create_test_review(db)
    r2 = create_test_review(db)
    assert r1.review_id == r2.review_id


def test_approve_review(db):
    """Approving a pending review should produce COMPLETED status."""
    from app.services.review_service import approve_review
    review = create_test_review(db)
    result = approve_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Evidence reviewed and validated.")
    assert result["decision"] == "APPROVE"
    assert result["status"] in ("COMPLETED", "ESCALATED")
    assert result["execution_status"] == "NOT_EXECUTED"


def test_approve_requires_reason(db):
    """Approval without a reason should raise 400."""
    from app.services.review_service import approve_review
    from fastapi import HTTPException
    review = create_test_review(db)
    with pytest.raises(HTTPException) as exc_info:
        approve_review(db, review.review_id, decision_reason="")
    assert exc_info.value.status_code == 400


def test_reject_review(db):
    """Rejecting a review should produce REJECTED status."""
    from app.services.review_service import reject_review
    review = create_test_review(db)
    result = reject_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Insufficient evidence for approval.")
    assert result["decision"] == "REJECT"
    assert result["status"] == "REJECTED"


def test_reject_requires_reason(db):
    """Rejection without a reason should raise 400."""
    from app.services.review_service import reject_review
    from fastapi import HTTPException
    review = create_test_review(db)
    with pytest.raises(HTTPException) as exc_info:
        reject_review(db, review.review_id, decision_reason="")
    assert exc_info.value.status_code == 400


def test_cannot_approve_completed_review(db):
    """A completed review should not be approved again."""
    from app.services.review_service import approve_review
    from fastapi import HTTPException
    review = create_test_review(db)
    approve_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="First approval.")
    with pytest.raises(HTTPException) as exc_info:
        approve_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Double approval attempt.")
    assert exc_info.value.status_code == 400


def test_cannot_approve_rejected_review(db):
    """A rejected review cannot be approved."""
    from app.services.review_service import reject_review, approve_review
    from fastapi import HTTPException
    review = create_test_review(db)
    reject_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Rejected due to policy.")
    with pytest.raises(HTTPException) as exc_info:
        approve_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Attempting to override rejection.")
    assert exc_info.value.status_code == 400


def test_cannot_reject_completed_review(db):
    """A completed review cannot be rejected."""
    from app.services.review_service import approve_review, reject_review
    from fastapi import HTTPException
    review = create_test_review(db)
    approve_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Approved.")
    with pytest.raises(HTTPException) as exc_info:
        reject_review(db, review.review_id, reviewer_id="reviewer_01", decision_reason="Late rejection.")
    assert exc_info.value.status_code == 400


def test_review_not_found(db):
    """Non-existent review should raise 404."""
    from app.services.review_service import approve_review
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        approve_review(db, "REV-INVALID99", decision_reason="Should fail.")
    assert exc_info.value.status_code == 404


def test_review_preserves_original_evidence(db):
    """Review must not alter original investigation fields."""
    review = create_test_review(db, confidence=0.9)
    assert float(review.confidence) == pytest.approx(0.9, abs=0.01)
    assert review.investigation_id == "test-inv-001"


# ============================================================
# 3. Security Tests
# ============================================================

def test_valid_finctrl_ids_accepted():
    """Valid FINCTRL IDs must not raise ValueError."""
    from app.agents.tools import validate_id
    valid_ids = ["CASE-00001", "ORD-00001", "PAY-00001", "INV-00001", "TAX-00001",
                 "SETTL-00001", "BTXN-00001", "CUST-00001", "REF-00001"]
    for vid in valid_ids:
        validate_id(vid)  # Should not raise


def test_sql_injection_rejected():
    """SQL injection strings must raise ValueError."""
    from app.agents.tools import validate_id
    injections = [
        "ORD-00001' OR '1'='1",
        "ORD-00001; DROP TABLE orders;",
        "UNION SELECT *",
        "'; SELECT 1--",
    ]
    for bad in injections:
        with pytest.raises(ValueError):
            validate_id(bad)


def test_path_traversal_rejected():
    """Path traversal strings must raise ValueError."""
    from app.agents.tools import validate_id
    paths = [
        "../etc/passwd",
        "..\\windows\\system32",
        "../../ground_truth.csv",
    ]
    for bad in paths:
        with pytest.raises(ValueError):
            validate_id(bad)


# ============================================================
# 4. Ground Truth Isolation
# ============================================================

def test_no_ground_truth_import_in_phase8():
    """Phase 8 service files must not import ground_truth."""
    import app.services.review_service as rs
    import app.services.audit_service as aus
    import app.services.verification_service as vs
    import app.agents.policy as pol
    import inspect
    for module in [rs, aus, vs, pol]:
        source = inspect.getsource(module)
        assert "ground_truth" not in source.lower(), f"Ground truth access found in {module.__name__}"


# ============================================================
# 5. Policy Thresholds
# ============================================================

def test_threshold_constants_are_reasonable():
    """Confidence and risk thresholds should be sensible values."""
    assert 0.5 < MEDIUM_CONFIDENCE_THRESHOLD < HIGH_CONFIDENCE_THRESHOLD < 1.0
    assert HIGH_RISK_AMOUNT_THRESHOLD > 0


# ============================================================
# 6. Unsupported Action Safety
# ============================================================

def test_no_financial_write_tools_exist():
    """Verify no write-capable financial tools are exposed."""
    from app.agents.tools import TOOLS
    for name, tool in TOOLS.items():
        assert tool.read_only is True, f"Tool '{name}' is not read-only!"
        assert tool.permission == "READ_ONLY", f"Tool '{name}' has non-read-only permission!"


def test_blocked_financial_actions():
    """Blocked financial actions should not be in allowed actions for any policy."""
    from app.agents.policy import BLOCKED_FINANCIAL_ACTIONS, AllowedAction
    blocked_as_allowed = set(a.value for a in AllowedAction) & BLOCKED_FINANCIAL_ACTIONS
    assert len(blocked_as_allowed) == 0, f"Blocked actions exposed as allowed: {blocked_as_allowed}"
