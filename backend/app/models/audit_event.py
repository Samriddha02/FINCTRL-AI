from sqlalchemy import Column, Integer, String, DateTime, Text
import datetime
from app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    audit_event_id = Column(String(50), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.datetime.utcnow)
    case_id = Column(String(50), nullable=False, index=True)
    investigation_id = Column(String(50), nullable=True, index=True)
    review_id = Column(String(50), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    actor_type = Column(String(50), nullable=False, default="SYSTEM")  # SYSTEM, AI_AGENT, HUMAN_REVIEWER
    actor_id = Column(String(100), nullable=True)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    result = Column(String(50), nullable=True)
