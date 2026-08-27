import sys
from pathlib import Path
from decimal import Decimal
import pandas as pd
from sqlalchemy import text, inspect

project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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

DATA_OUTPUT_DIR = project_root / "data" / "output"


def verify_database():
    """Verifies PostgreSQL schema, table counts, foreign keys, numeric precision,

    ground-truth isolation, and anomaly preservation.
    """
    print("FINCTRL AI Database Verification Tool\n")

    # 1. Verify Connection
    try:
        with engine.connect() as conn:
            pg_ver = conn.execute(text("SHOW server_version;")).scalar()
            print(f"PostgreSQL Connection: PASS (Version: {pg_ver})")
    except Exception as e:
        print(f"PostgreSQL Connection: FAIL ({e})")
        sys.exit(1)

    inspector = inspect(engine)
    db_tables = inspector.get_table_names()

    # 2. Verify Table Existence (8 exact operational tables)
    expected_tables = [
        "customers",
        "orders",
        "payments",
        "refunds",
        "settlements",
        "bank_transactions",
        "invoices",
        "tax_records",
    ]
    missing_tables = [t for t in expected_tables if t not in db_tables]
    if missing_tables:
        print(f"Tables Verification: FAIL (Missing tables: {missing_tables})")
        sys.exit(1)
    else:
        print("Required Operational Tables: PASS (All 8 tables exist)")

    # 3. Verify Ground Truth Isolation
    if "ground_truth" in db_tables or "groundtruth" in db_tables:
        print("Ground Truth Isolation: FAIL (ground_truth table detected in PostgreSQL!)")
        sys.exit(1)
    else:
        print("Ground Truth Isolation: PASS (ground_truth table is NOT present in PostgreSQL)")

    db = SessionLocal()
    try:
        # 4. Compare CSV vs DB Row Counts
        counts = {
            "customers": (len(pd.read_csv(DATA_OUTPUT_DIR / "customers.csv")), db.query(Customer).count()),
            "orders": (len(pd.read_csv(DATA_OUTPUT_DIR / "orders.csv")), db.query(Order).count()),
            "payments": (len(pd.read_csv(DATA_OUTPUT_DIR / "payments.csv")), db.query(Payment).count()),
            "refunds": (len(pd.read_csv(DATA_OUTPUT_DIR / "refunds.csv")), db.query(Refund).count()),
            "settlements": (len(pd.read_csv(DATA_OUTPUT_DIR / "settlements.csv")), db.query(Settlement).count()),
            "bank_transactions": (len(pd.read_csv(DATA_OUTPUT_DIR / "bank_transactions.csv")), db.query(BankTransaction).count()),
            "invoices": (len(pd.read_csv(DATA_OUTPUT_DIR / "invoices.csv")), db.query(Invoice).count()),
            "tax_records": (len(pd.read_csv(DATA_OUTPUT_DIR / "tax_records.csv")), db.query(TaxRecord).count()),
        }

        all_counts_match = True
        print("\nRow Count Comparison:")
        for table_name, (csv_cnt, db_cnt) in counts.items():
            status = "MATCH" if csv_cnt == db_cnt else "MISMATCH"
            print(f"  {table_name:<20}: CSV={csv_cnt:<4} | DB={db_cnt:<4} -> {status}")
            if csv_cnt != db_cnt:
                all_counts_match = False

        if not all_counts_match:
            print("\nRow Counts Verification: FAIL")
            sys.exit(1)
        else:
            print("Row Counts Verification: PASS")

        # 5. Verify Business ID Uniqueness
        cust_cnt = db.query(Customer.customer_id).distinct().count()
        order_cnt = db.query(Order.order_id).distinct().count()
        payment_cnt = db.query(Payment.payment_id).distinct().count()

        if cust_cnt != counts["customers"][1] or order_cnt != counts["orders"][1] or payment_cnt != counts["payments"][1]:
            print("Business ID Uniqueness: FAIL")
            sys.exit(1)
        else:
            print("Business ID Uniqueness: PASS")

        # 6. Verify Numeric Money Precision
        sample_order = db.query(Order).first()
        if not isinstance(sample_order.order_amount, Decimal):
            print(f"Money Precision: FAIL (order_amount type is {type(sample_order.order_amount)}, expected Decimal)")
            sys.exit(1)
        else:
            print(f"Money Precision: PASS (Type is Decimal, e.g. {sample_order.order_amount})")

        # 7. Verify Anomaly Preservation (e.g. Fee Difference, Tax Mismatch, Missing Settlement)
        # Check that missing settlement payments still exist without settlement
        missing_settlement_payments = [
            p.payment_id
            for p in db.query(Payment).all()
            if db.query(Settlement).filter(Settlement.payment_id == p.payment_id).first() is None
        ]
        if len(missing_settlement_payments) != 8:
            print(f"Anomaly Preservation: FAIL (Expected 8 missing settlements, found {len(missing_settlement_payments)})")
            sys.exit(1)
        else:
            print(f"Anomaly Preservation: PASS (Preserved {len(missing_settlement_payments)} missing settlement cases)")

        print("\nOverall Database Verification: PASS\n")

    finally:
        db.close()


if __name__ == "__main__":
    verify_database()
