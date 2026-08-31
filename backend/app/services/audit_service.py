import uuid
import datetime
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent


def log_audit_event(
    db: Session,
    case_id: str,
    event_type: str,
    actor_type: str = "SYSTEM",
    actor_id: Optional[str] = None,
    investigation_id: Optional[str] = None,
    review_id: Optional[str] = None,
    previous_state: Optional[str] = None,
    new_state: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    result: Optional[str] = None
) -> AuditEvent:
    """Logs an immutable audit event to database."""
    audit_event_id = f"AUD-{uuid.uuid4().hex[:10].upper()}"
    details_str = json.dumps(details) if isinstance(details, (dict, list)) else details

    event = AuditEvent(
        audit_event_id=audit_event_id,
        timestamp=datetime.datetime.utcnow(),
        case_id=case_id,
        investigation_id=investigation_id,
        review_id=review_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        previous_state=previous_state,
        new_state=new_state,
        details=details_str,
        result=result
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_audit_trail(
    db: Session,
    case_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100
) -> List[AuditEvent]:
    """Retrieves immutable audit trail chronologically."""
    query = db.query(AuditEvent)
    if case_id:
        query = query.filter(AuditEvent.case_id == case_id)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    return query.order_by(AuditEvent.timestamp.asc()).limit(limit).all()
