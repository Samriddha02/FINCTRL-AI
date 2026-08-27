from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models import (
    Customer,
    Order,
    Payment,
    Refund,
    Settlement,
    BankTransaction,
    Invoice,
    TaxRecord,
)


def get_customer(db: Session, customer_id: str) -> Optional[Customer]:
    """Retrieve customer by business customer_id."""
    return db.query(Customer).filter(Customer.customer_id == customer_id).first()


def get_order(db: Session, order_id: str) -> Optional[Order]:
    """Retrieve order by business order_id."""
    return db.query(Order).filter(Order.order_id == order_id).first()


def get_payment(db: Session, payment_id: str) -> Optional[Payment]:
    """Retrieve payment by business payment_id."""
    return db.query(Payment).filter(Payment.payment_id == payment_id).first()


def get_refunds(db: Session, payment_id: str) -> List[Refund]:
    """Retrieve all refunds associated with a payment_id."""
    return db.query(Refund).filter(Refund.payment_id == payment_id).all()


def get_settlement(db: Session, payment_id: str) -> Optional[Settlement]:
    """Retrieve settlement associated with a payment_id."""
    return db.query(Settlement).filter(Settlement.payment_id == payment_id).first()


def get_bank_transactions(db: Session, reference_id: str) -> List[BankTransaction]:
    """Retrieve bank transactions matching reference_id (usually settlement_id)."""
    return db.query(BankTransaction).filter(BankTransaction.reference_id == reference_id).all()


def get_invoice(db: Session, invoice_id: str) -> Optional[Invoice]:
    """Retrieve invoice by business invoice_id."""
    return db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()


def get_invoice_by_order(db: Session, order_id: str) -> Optional[Invoice]:
    """Retrieve invoice by order_id."""
    return db.query(Invoice).filter(Invoice.order_id == order_id).first()


def get_tax_record(db: Session, invoice_id: str) -> Optional[TaxRecord]:
    """Retrieve tax record associated with an invoice_id."""
    return db.query(TaxRecord).filter(TaxRecord.invoice_id == invoice_id).first()


def get_payment_context(db: Session, payment_id: str) -> Dict[str, Any]:
    """Retrieves all raw operational records linked to a payment for future reconciliation.

    NOTE: Does NOT perform matching, discrepancy detection, or reconciliation logic.
    """
    payment = get_payment(db, payment_id)
    if not payment:
        return {"payment": None}

    order = get_order(db, payment.order_id)
    customer = get_customer(db, payment.customer_id)
    refunds = get_refunds(db, payment.payment_id)
    settlement = get_settlement(db, payment.payment_id)

    bank_txns = []
    if settlement:
        bank_txns = get_bank_transactions(db, settlement.settlement_id)

    invoice = get_invoice_by_order(db, payment.order_id)
    tax_record = get_tax_record(db, invoice.invoice_id) if invoice else None

    return {
        "customer": customer,
        "order": order,
        "payment": payment,
        "refunds": refunds,
        "settlement": settlement,
        "bank_transactions": bank_txns,
        "invoice": invoice,
        "tax_record": tax_record,
    }
