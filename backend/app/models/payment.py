from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    payment_method = Column(String(50), nullable=False)
    payment_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
