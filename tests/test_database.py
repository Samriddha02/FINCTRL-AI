import sys
from pathlib import Path
from decimal import Decimal
import pytest
from sqlalchemy import text, inspect

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine, SessionLocal
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
from app.services.database_service import (
    get_customer,
    get_order,
    get_payment,
    get_refunds,
    get_settlement,
    get_bank_transactions,
    get_invoice,
    get_tax_record,
    get_payment_context,
)
from scripts.seed_database import seed_database


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_db_connection():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1;")).scalar()
        assert res == 1


def test_table_existence():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = [
        "customers",
        "orders",
        "payments",
        "refunds",
        "settlements",
        "bank_transactions",
        "invoices",
        "tax_records",
    ]
    for tbl in expected:
        assert tbl in tables


def test_ground_truth_isolation(db_session):
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "ground_truth" not in tables
    assert "groundtruth" not in tables


def test_row_counts(db_session):
    assert db_session.query(Customer).count() == 80
    assert db_session.query(Order).count() == 100
    assert db_session.query(Payment).count() == 100
    assert db_session.query(Refund).count() == 10
    assert db_session.query(Settlement).count() == 92
    assert db_session.query(BankTransaction).count() == 99
    assert db_session.query(Invoice).count() == 100
    assert db_session.query(TaxRecord).count() == 100


def test_business_id_uniqueness(db_session):
    cust_ids = [c[0] for c in db_session.query(Customer.customer_id).all()]
    assert len(cust_ids) == len(set(cust_ids))

    order_ids = [o[0] for o in db_session.query(Order.order_id).all()]
    assert len(order_ids) == len(set(order_ids))


def test_relational_queries(db_session):
    payment = get_payment(db_session, "PAY-00001")
    assert payment is not None

    order = get_order(db_session, payment.order_id)
    assert order is not None
    assert order.customer_id == payment.customer_id

    customer = get_customer(db_session, payment.customer_id)
    assert customer is not None

    settlement = get_settlement(db_session, payment.payment_id)
    assert settlement is not None
    assert settlement.payment_id == payment.payment_id

    if settlement:
        bank_txns = get_bank_transactions(db_session, settlement.settlement_id)
        assert len(bank_txns) >= 1

    invoice = db_session.query(Invoice).filter(Invoice.order_id == order.order_id).first()
    assert invoice is not None

    tax_rec = get_tax_record(db_session, invoice.invoice_id)
    assert tax_rec is not None


def test_payment_context_retrieval(db_session):
    ctx = get_payment_context(db_session, "PAY-00001")
    assert ctx["payment"] is not None
    assert ctx["order"] is not None
    assert ctx["customer"] is not None
    assert ctx["settlement"] is not None
    assert isinstance(ctx["bank_transactions"], list)


def test_numeric_decimal_money_storage(db_session):
    order = db_session.query(Order).first()
    assert isinstance(order.order_amount, Decimal)

    settlement = db_session.query(Settlement).first()
    assert isinstance(settlement.gross_amount, Decimal)
    assert isinstance(settlement.fee_amount, Decimal)
    assert isinstance(settlement.net_amount, Decimal)


def test_repeated_seeding_idempotency(db_session):
    count_before = db_session.query(Payment).count()
    seed_database()
    count_after = db_session.query(Payment).count()
    assert count_before == count_after


def test_transaction_rollback_on_failure():
    db = SessionLocal()
    try:
        invalid_order = Order(
            order_id="ORD-INVALID-TEST",
            customer_id="NON_EXISTENT_CUST_ID_99999",  # Will fail foreign key constraint
            order_amount=Decimal("100.00"),
            currency="INR",
            order_status="COMPLETED",
            created_at="2026-01-01 00:00:00",
        )
        db.add(invalid_order)
        db.commit()
        pytest.fail("Should have failed foreign key constraint!")
    except Exception:
        db.rollback()
        # Verify invalid order was rolled back
        assert db.query(Order).filter(Order.order_id == "ORD-INVALID-TEST").first() is None
    finally:
        db.close()
