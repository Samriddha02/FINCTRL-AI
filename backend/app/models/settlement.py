from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from app.core.database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(Integer, primary_key=True, index=True)
    settlement_id = Column(String(50), unique=True, nullable=False, index=True)
    payment_id = Column(String(50), ForeignKey("payments.payment_id"), nullable=False, index=True)
    gross_amount = Column(Numeric(18, 2), nullable=False)
    fee_amount = Column(Numeric(18, 2), nullable=False)
    tax_amount = Column(Numeric(18, 2), nullable=False)
    adjustment_amount = Column(Numeric(18, 2), nullable=False)
    net_amount = Column(Numeric(18, 2), nullable=False)
    settlement_status = Column(String(50), nullable=False)
    settlement_date = Column(Date, nullable=False)
