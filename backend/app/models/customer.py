from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String(50), unique=True, nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
