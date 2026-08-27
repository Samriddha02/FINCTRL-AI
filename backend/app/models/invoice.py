from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False, index=True)
    subtotal = Column(Numeric(18, 2), nullable=False)
    tax_rate = Column(Numeric(18, 4), nullable=False)
    tax_amount = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)
    invoice_status = Column(String(50), nullable=False)
    invoice_date = Column(Date, nullable=False)
