"""
tests/test_audit.py — Phase 8 Audit Trail Tests
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
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.audit_event import AuditEvent
from app.models.human_review import HumanReview
from app.models.agent_run import AgentRun, SystemMetric
from app.services.audit_service import log_audit_event, get_audit_trail


@pytest.fixture
def db():
    """In-memory SQLite DB for audit tests."""
    engine = create_engine("sqlite:///:memory:")
    # Import all Phase 3 + Phase 8 models so metadata is complete
    from app.models import (Customer, Order, Payment, Refund, Settlement,
                           BankTransaction, Invoice, TaxRecord)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ============================================================
# 1. Audit Event Creation
# ============================================================

def test_audit_event_created(db):
    """log_audit_event should insert a record to the database."""
    event = log_audit_event(
        db=db,
        case_id="CASE-00001",
        event_type="RECONCILIATION_COMPLETED",
        actor_type="SYSTEM",
        details={"status": "MATCHED"}
    )
    assert event.audit_event_id.startswith("AUD-")
    assert event.case_id == "CASE-00001"
    assert event.event_type == "RECONCILIATION_COMPLETED"


def test_audit_event_has_timestamp(db):
    """Audit event must have a valid timestamp."""
    import datetime
    event = log_audit_event(db, "CASE-00001", "INVESTIGATION_STARTED")
    assert event.timestamp is not None
    assert isinstance(event.timestamp, datetime.datetime)


def test_audit_event_state_transition(db):
    """Audit event should record previous and new state."""
    event = log_audit_event(
        db=db,
        case_id="CASE-00001",
        event_type="HUMAN_APPROVED",
        actor_type="HUMAN_REVIEWER",
        actor_id="reviewer_01",
        previous_state="PENDING",
        new_state="APPROVED"
    )
    assert event.previous_state == "PENDING"
    assert event.new_state == "APPROVED"
    assert event.actor_id == "reviewer_01"


def test_audit_details_serialized(db):
    """Audit event details should store JSON-serialized dict."""
    details = {"confidence": 0.85, "risk_level": "HIGH"}
    event = log_audit_event(db, "CASE-00001", "POLICY_EVALUATED", details=details)
    # Details are stored as JSON string in DB
    assert event.details is not None
    parsed = json.loads(event.details)
    assert parsed["confidence"] == 0.85


# ============================================================
# 2. Audit Trail Retrieval & Ordering
# ============================================================

def test_audit_trail_chronological(db):
    """Audit events should be returned in chronological order."""
    log_audit_event(db, "CASE-00001", "CASE_CREATED")
    log_audit_event(db, "CASE-00001", "RECONCILIATION_COMPLETED")
    log_audit_event(db, "CASE-00001", "INVESTIGATION_COMPLETED")

    events = get_audit_trail(db, case_id="CASE-00001")
    event_types = [e.event_type for e in events]
    assert event_types.index("CASE_CREATED") < event_types.index("RECONCILIATION_COMPLETED")
    assert event_types.index("RECONCILIATION_COMPLETED") < event_types.index("INVESTIGATION_COMPLETED")


def test_audit_trail_filtered_by_case(db):
    """Filter by case_id returns only matching events."""
    log_audit_event(db, "CASE-00001", "RECONCILIATION_COMPLETED")
    log_audit_event(db, "CASE-00002", "RECONCILIATION_COMPLETED")

    events = get_audit_trail(db, case_id="CASE-00001")
    assert all(e.case_id == "CASE-00001" for e in events)


def test_audit_trail_filtered_by_event_type(db):
    """Filter by event_type returns only matching events."""
    log_audit_event(db, "CASE-00001", "HUMAN_APPROVED")
    log_audit_event(db, "CASE-00001", "CASE_ESCALATED")
    log_audit_event(db, "CASE-00001", "HUMAN_APPROVED")

    events = get_audit_trail(db, case_id="CASE-00001", event_type="HUMAN_APPROVED")
    assert len(events) == 2
    assert all(e.event_type == "HUMAN_APPROVED" for e in events)


# ============================================================
# 3. Audit Immutability
# ============================================================

def test_audit_no_update_possible_through_service(db):
    """The audit_service must not expose any update/delete method."""
    from app.services import audit_service
    import inspect
    members = [m for m in dir(audit_service) if not m.startswith("_")]
    write_ops = [m for m in members if any(w in m.lower() for w in ("update", "delete", "remove", "modify", "edit"))]
    assert len(write_ops) == 0, f"Audit service exposes write operations: {write_ops}"


def test_audit_records_cannot_be_overwritten(db):
    """Once created, an audit event's ID should not be changed."""
    event = log_audit_event(db, "CASE-00001", "CASE_CREATED")
    original_id = event.audit_event_id

    # Reload from DB
    reloaded = db.query(AuditEvent).filter(AuditEvent.audit_event_id == original_id).first()
    assert reloaded is not None
    assert reloaded.audit_event_id == original_id
    assert reloaded.event_type == "CASE_CREATED"


def test_audit_event_count_grows_monotonically(db):
    """Audit event count should only grow."""
    initial = db.query(AuditEvent).count()
    log_audit_event(db, "CASE-00001", "TOOL_EXECUTED")
    log_audit_event(db, "CASE-00001", "EVIDENCE_RETRIEVED")
    final = db.query(AuditEvent).count()
    assert final == initial + 2


# ============================================================
# 4. Audit After Human Decision
# ============================================================

def test_audit_on_approval(db):
    """Approving a review should create audit events."""
    from app.services.review_service import create_or_get_review, approve_review
    from tests.test_human_review import make_investigation

    inv = make_investigation(confidence=0.88)
    review = create_or_get_review(db, "CASE-00001", inv)
    approve_review(db, review.review_id, reviewer_id="auditor_01", decision_reason="Evidence complete, approval granted.")

    events = get_audit_trail(db, case_id="CASE-00001")
    event_types = [e.event_type for e in events]
    assert "HUMAN_REVIEW_CREATED" in event_types
    assert "HUMAN_APPROVED" in event_types
    assert "ACTION_NOT_EXECUTED" in event_types


def test_audit_on_rejection(db):
    """Rejecting a review should create audit events."""
    from app.services.review_service import create_or_get_review, reject_review
    from tests.test_human_review import make_investigation

    inv = make_investigation(confidence=0.88)
    review = create_or_get_review(db, "CASE-00002", inv)
    reject_review(db, review.review_id, reviewer_id="auditor_02", decision_reason="Insufficient evidence.")

    events = get_audit_trail(db, case_id="CASE-00002")
    event_types = [e.event_type for e in events]
    assert "HUMAN_REJECTED" in event_types


# ============================================================
# 5. Ground Truth Isolation in Audit
# ============================================================

def test_audit_service_no_ground_truth_access():
    """Audit service must not access ground truth data."""
    import inspect
    from app.services import audit_service
    source = inspect.getsource(audit_service)
    assert "ground_truth" not in source.lower()


# ============================================================
# 6. Verification Service Audit Events
# ============================================================

def test_verification_creates_audit_event(db):
    """verify_resolution should create an audit event."""
    from app.services.verification_service import verify_resolution
    res = verify_resolution(db, "CASE-00001", review_id="REV-TEST001")
    assert res["status"] in ["VERIFIED", "VERIFICATION_FAILED"]
    events = get_audit_trail(db, case_id="CASE-00001")
    assert any(e.event_type in ["ACTION_VERIFIED", "VERIFICATION_FAILED"] for e in events)


def test_verification_service_no_ground_truth_access():
    """Verification service must not access ground truth data."""
    import inspect
    from app.services import verification_service
    source = inspect.getsource(verification_service)
    assert "ground_truth" not in source.lower()
