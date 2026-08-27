from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.core.database import Base


class TaxRecord(Base):
    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    tax_id = Column(String(50), unique=True, nullable=False, index=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id"), nullable=False, index=True)
    tax_type = Column(String(50), nullable=False)
    taxable_amount = Column(Numeric(18, 2), nullable=False)
    tax_rate = Column(Numeric(18, 4), nullable=False)
    tax_amount = Column(Numeric(18, 2), nullable=False)
    filing_period = Column(String(20), nullable=False)
    recorded_at = Column(DateTime, nullable=False)
