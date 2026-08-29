import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import pandas as pd

# Add project root and backend directory to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal
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
TRUNCATE_SQL = (
    "TRUNCATE TABLE tax_records, invoices, bank_transactions, settlements, "
    "refunds, payments, orders, customers RESTART IDENTITY CASCADE"
)


def parse_datetime(val):
    if pd.isna(val) or not str(val).strip():
        return None
    return datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M:%S")


def parse_date(val):
    if pd.isna(val) or not str(val).strip():
        return None
    return datetime.strptime(str(val).strip(), "%Y-%m-%d").date()


def parse_decimal(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    return Decimal(str(val).strip())


def parse_str(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s != "" else None


def truncate_operational_tables(db: Session) -> None:
    """Remove operational rows only. Does not drop the database, schema, or table definitions."""
    db.execute(text(TRUNCATE_SQL))
    db.flush()


def seed_from_directory(db: Session, data_dir, replace: bool = False) -> None:
    """Load the eight operational CSVs into an existing session.

    Ground truth is never ingested. When replace=True, operational tables are truncated first.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory {data_dir} does not exist.")
    if replace:
        truncate_operational_tables(db)
    _load_operational_csvs(db, data_dir)


def _load_operational_csvs(db: Session, data_dir: Path) -> None:
    print(f"Starting database seeding from {data_dir}...")

    try:
        # 1. Customers
        customers_csv = data_dir / "customers.csv"
        if customers_csv.exists():
            existing_custs = {c[0] for c in db.query(Customer.customer_id).all()}
            df_cust = pd.read_csv(customers_csv)
            new_custs = []
            for _, r in df_cust.iterrows():
                cid = parse_str(r["customer_id"])
                if cid not in existing_custs:
                    new_custs.append(
                        Customer(
                            customer_id=cid,
                            customer_name=parse_str(r["customer_name"]),
                            email=parse_str(r["email"]),
                            created_at=parse_datetime(r["created_at"]),
                        )
                    )
            if new_custs:
                db.bulk_save_objects(new_custs)
                db.flush()
            print(f"Customers: {len(new_custs)} inserted (Total: {len(existing_custs) + len(new_custs)})")

        # 2. Orders
        orders_csv = data_dir / "orders.csv"
        if orders_csv.exists():
            existing_orders = {o[0] for o in db.query(Order.order_id).all()}
            df_ord = pd.read_csv(orders_csv)
            new_orders = []
            for _, r in df_ord.iterrows():
                oid = parse_str(r["order_id"])
                if oid not in existing_orders:
                    new_orders.append(
                        Order(
                            order_id=oid,
                            customer_id=parse_str(r["customer_id"]),
                            order_amount=parse_decimal(r["order_amount"]),
                            currency=parse_str(r["currency"]),
                            order_status=parse_str(r["order_status"]),
                            created_at=parse_datetime(r["created_at"]),
                        )
                    )
            if new_orders:
                db.bulk_save_objects(new_orders)
                db.flush()
            print(f"Orders: {len(new_orders)} inserted (Total: {len(existing_orders) + len(new_orders)})")

        # 3. Payments
        payments_csv = data_dir / "payments.csv"
        if payments_csv.exists():
            existing_payments = {p[0] for p in db.query(Payment.payment_id).all()}
            df_pay = pd.read_csv(payments_csv)
            new_payments = []
            for _, r in df_pay.iterrows():
                pid = parse_str(r["payment_id"])
                if pid not in existing_payments:
                    new_payments.append(
                        Payment(
                            payment_id=pid,
                            order_id=parse_str(r["order_id"]),
                            customer_id=parse_str(r["customer_id"]),
                            amount=parse_decimal(r["amount"]),
                            currency=parse_str(r["currency"]),
                            payment_method=parse_str(r["payment_method"]),
                            payment_status=parse_str(r["payment_status"]),
                            created_at=parse_datetime(r["created_at"]),
                        )
                    )
            if new_payments:
                db.bulk_save_objects(new_payments)
                db.flush()
            print(f"Payments: {len(new_payments)} inserted (Total: {len(existing_payments) + len(new_payments)})")

        # 4. Refunds
        refunds_csv = data_dir / "refunds.csv"
        if refunds_csv.exists():
            existing_refunds = {r[0] for r in db.query(Refund.refund_id).all()}
            df_ref = pd.read_csv(refunds_csv)
            new_refunds = []
            for _, r in df_ref.iterrows():
                rid = parse_str(r["refund_id"])
                if rid not in existing_refunds:
                    new_refunds.append(
                        Refund(
                            refund_id=rid,
                            payment_id=parse_str(r["payment_id"]),
                            refund_amount=parse_decimal(r["refund_amount"]),
                            refund_reason=parse_str(r["refund_reason"]),
                            refund_status=parse_str(r["refund_status"]),
                            created_at=parse_datetime(r["created_at"]),
                        )
                    )
            if new_refunds:
                db.bulk_save_objects(new_refunds)
                db.flush()
            print(f"Refunds: {len(new_refunds)} inserted (Total: {len(existing_refunds) + len(new_refunds)})")

        # 5. Settlements
        settlements_csv = data_dir / "settlements.csv"
        if settlements_csv.exists():
            existing_settlements = {s[0] for s in db.query(Settlement.settlement_id).all()}
            df_set = pd.read_csv(settlements_csv)
            new_settlements = []
            for _, r in df_set.iterrows():
                sid = parse_str(r["settlement_id"])
                if sid not in existing_settlements:
                    new_settlements.append(
                        Settlement(
                            settlement_id=sid,
                            payment_id=parse_str(r["payment_id"]),
                            gross_amount=parse_decimal(r["gross_amount"]),
                            fee_amount=parse_decimal(r["fee_amount"]),
                            tax_amount=parse_decimal(r["tax_amount"]),
                            adjustment_amount=parse_decimal(r["adjustment_amount"]),
                            net_amount=parse_decimal(r["net_amount"]),
                            settlement_status=parse_str(r["settlement_status"]),
                            settlement_date=parse_date(r["settlement_date"]),
                        )
                    )
            if new_settlements:
                db.bulk_save_objects(new_settlements)
                db.flush()
            print(f"Settlements: {len(new_settlements)} inserted (Total: {len(existing_settlements) + len(new_settlements)})")

        # 6. Bank Transactions
        bank_csv = data_dir / "bank_transactions.csv"
        if bank_csv.exists():
            existing_btxns = {b[0] for b in db.query(BankTransaction.bank_txn_id).all()}
            df_btx = pd.read_csv(bank_csv)
            new_btxns = []
            for _, r in df_btx.iterrows():
                btid = parse_str(r["bank_txn_id"])
                if btid not in existing_btxns:
                    new_btxns.append(
                        BankTransaction(
                            bank_txn_id=btid,
                            reference_id=parse_str(r["reference_id"]),
                            amount=parse_decimal(r["amount"]),
                            transaction_type=parse_str(r["transaction_type"]),
                            description=parse_str(r["description"]),
                            transaction_date=parse_date(r["transaction_date"]),
                        )
                    )
            if new_btxns:
                db.bulk_save_objects(new_btxns)
                db.flush()
            print(f"Bank Transactions: {len(new_btxns)} inserted (Total: {len(existing_btxns) + len(new_btxns)})")

        # 7. Invoices
        invoices_csv = data_dir / "invoices.csv"
        if invoices_csv.exists():
            existing_invoices = {i[0] for i in db.query(Invoice.invoice_id).all()}
            df_inv = pd.read_csv(invoices_csv)
            new_invoices = []
            for _, r in df_inv.iterrows():
                iid = parse_str(r["invoice_id"])
                if iid not in existing_invoices:
                    new_invoices.append(
                        Invoice(
                            invoice_id=iid,
                            order_id=parse_str(r["order_id"]),
                            customer_id=parse_str(r["customer_id"]),
                            subtotal=parse_decimal(r["subtotal"]),
                            tax_rate=parse_decimal(r["tax_rate"]),
                            tax_amount=parse_decimal(r["tax_amount"]),
                            total_amount=parse_decimal(r["total_amount"]),
                            invoice_status=parse_str(r["invoice_status"]),
                            invoice_date=parse_date(r["invoice_date"]),
                        )
                    )
            if new_invoices:
                db.bulk_save_objects(new_invoices)
                db.flush()
            print(f"Invoices: {len(new_invoices)} inserted (Total: {len(existing_invoices) + len(new_invoices)})")

        # 8. Tax Records
        tax_csv = data_dir / "tax_records.csv"
        if tax_csv.exists():
            existing_taxes = {t[0] for t in db.query(TaxRecord.tax_id).all()}
            df_tax = pd.read_csv(tax_csv)
            new_taxes = []
            for _, r in df_tax.iterrows():
                tid = parse_str(r["tax_id"])
                if tid not in existing_taxes:
                    new_taxes.append(
                        TaxRecord(
                            tax_id=tid,
                            invoice_id=parse_str(r["invoice_id"]),
                            tax_type=parse_str(r["tax_type"]),
                            taxable_amount=parse_decimal(r["taxable_amount"]),
                            tax_rate=parse_decimal(r["tax_rate"]),
                            tax_amount=parse_decimal(r["tax_amount"]),
                            filing_period=parse_str(r["filing_period"]),
                            recorded_at=parse_datetime(r["recorded_at"]),
                        )
                    )
            if new_taxes:
                db.bulk_save_objects(new_taxes)
                db.flush()
            print(f"Tax Records: {len(new_taxes)} inserted (Total: {len(existing_taxes) + len(new_taxes)})")

        db.commit()
        print("\nDatabase seeding completed successfully!")

    except Exception:
        db.rollback()
        raise


def seed_database():
    """Seeds the PostgreSQL development database with Phase 2 synthetic financial data."""
    if not DATA_OUTPUT_DIR.exists():
        print(f"ERROR: Data output directory {DATA_OUTPUT_DIR} does not exist.")
        sys.exit(1)

    db = SessionLocal()
    try:
        seed_from_directory(db, DATA_OUTPUT_DIR, replace=False)
    except Exception as e:
        print(f"\nERROR during database seeding: {e}. Transaction rolled back.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
