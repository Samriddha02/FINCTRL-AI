from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
import datetime
from app.core.database import Base


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(String(50), unique=True, nullable=False, index=True)
    case_id = Column(String(50), nullable=False, index=True)
    investigation_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True, default="PENDING")
    assigned_to = Column(String(100), nullable=True)
    review_reason = Column(String(255), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False, default="MEDIUM")
    recommended_action = Column(Text, nullable=False)
    policy_decision = Column(String(50), nullable=False, default="HUMAN_REVIEW_REQUIRED")
    decision = Column(String(50), nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
