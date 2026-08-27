from sqlalchemy import Column, Integer, String, Numeric, Date
from app.core.database import Base


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    bank_txn_id = Column(String(50), unique=True, nullable=False, index=True)
    reference_id = Column(String(50), nullable=True, index=True)  # No FK constraint
    amount = Column(Numeric(18, 2), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False)
