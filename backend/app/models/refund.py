from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.core.database import Base


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    refund_id = Column(String(50), unique=True, nullable=False, index=True)
    payment_id = Column(String(50), ForeignKey("payments.payment_id"), nullable=False, index=True)
    refund_amount = Column(Numeric(18, 2), nullable=False)
    refund_reason = Column(String(255), nullable=True)
    refund_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
