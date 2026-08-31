from typing import List, Optional, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.audit_service import get_audit_trail
from app.api.schemas_phase8 import AuditEventSchema

router = APIRouter(prefix="/api/audit", tags=["Audit Trail"])


@router.get("", response_model=List[AuditEventSchema])
def list_audit_events(
    case_id: Optional[str] = Query(None, description="Filter by case_id"),
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    limit: int = Query(100, le=500, description="Max events to return"),
    db: Session = Depends(get_db)
) -> List[AuditEventSchema]:
    """List audit trail events (read-only, chronological)."""
    events = get_audit_trail(db, case_id=case_id, event_type=event_type, limit=limit)
    return [AuditEventSchema.from_model(e) for e in events]


@router.get("/{case_id}", response_model=List[AuditEventSchema])
def get_case_audit_trail(
    case_id: str,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
) -> List[AuditEventSchema]:
    """Get immutable audit history for a specific case."""
    events = get_audit_trail(db, case_id=case_id, limit=limit)
    return [AuditEventSchema.from_model(e) for e in events]
