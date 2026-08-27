from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False, index=True)
    order_amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    order_status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
