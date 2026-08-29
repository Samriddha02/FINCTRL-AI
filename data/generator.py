import argparse
import os
import sys
import random
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.config import (
    SEED,
    NUM_CASES,
    NUM_CUSTOMERS,
    CURRENCY,
    DEFAULT_TAX_RATE,
    DEFAULT_GATEWAY_FEE_RATE,
    START_DATE,
    END_DATE,
    ANOMALY_DISTRIBUTION,
    OUTPUT_DIR,
    LOGS_DIR,
    OUTPUT_FILES,
    LOG_FILE,
)
from data.models import (
    Customer,
    Order,
    Payment,
    Refund,
    Settlement,
    BankTransaction,
    Invoice,
    TaxRecord,
    GroundTruth,
)
from data.validators import validate_dataset


def setup_logging(log_dir: Optional[Path] = None):
    target_log_dir = log_dir or LOGS_DIR
    target_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_log_dir / "generation.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)
            handler.close()
    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    root.addHandler(file_handler)


def round_curr(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FinancialDataGenerator:

    def __init__(
        self,
        seed: int = SEED,
        num_cases: int = NUM_CASES,
        num_customers: int = NUM_CUSTOMERS,
        output_dir: Optional[Path] = None,
    ):
        self.seed = seed
        self.num_cases = num_cases
        self.num_customers = num_customers
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR

        # Set deterministic random seeds
        random.seed(self.seed)
        np.random.seed(self.seed)

        self.customers: list[Customer] = []
        self.orders: list[Order] = []
        self.payments: list[Payment] = []
        self.refunds: list[Refund] = []
        self.settlements: list[Settlement] = []
        self.bank_txns: list[BankTransaction] = []
        self.invoices: list[Invoice] = []
        self.tax_records: list[TaxRecord] = []
        self.ground_truth: list[GroundTruth] = []

    def generate_customers(self):
        first_names = [
            "Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Neha", "Rahul", "Sneha",
            "Aditya", "Pooja", "Siddharth", "Kavya", "Amit", "Riya", "Manish"
        ]
        last_names = [
            "Sharma", "Verma", "Patel", "Deshmukh", "Iyer", "Nair", "Reddy", "Gupta",
            "Chowdhury", "Mehta", "Joshi", "Kulkarni", "Bhat", "Rao", "Singh"
        ]
        companies = [
            "Apex Solutions", "Kaveri Retailers", "TechPulse Systems", "BlueSky Enterprises",
            "Zenith Logistics", "Nova Software", "Vanguard Financial", "Nexus Traders",
            "Omicron Media", "Starlight Exports", "Solstice Tech", "Hyperion Global"
        ]

        start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")

        for i in range(1, self.num_customers + 1):
            cust_id = f"CUST-{i:04d}"
            if i % 3 == 0:
                name = f"{random.choice(companies)} Pvt Ltd"
                email = f"finance@{name.lower().replace(' ', '').replace('pvtltd', '')}.in"
            else:
                fname, lname = random.choice(first_names), random.choice(last_names)
                name = f"{fname} {lname}"
                email = f"{fname.lower()}.{lname.lower()}{i}@synthmail.com"

            created_days = random.randint(0, 30)
            created_at = (start_dt - timedelta(days=created_days)).strftime("%Y-%m-%d %H:%M:%S")

            self.customers.append(
                Customer(
                    customer_id=cust_id,
                    customer_name=name,
                    email=email,
                    created_at=created_at,
                )
            )

    def _get_anomaly_plan(self) -> list[str]:
        if self.num_cases == 100:
            plan = []
            for status, count in ANOMALY_DISTRIBUTION.items():
                plan.extend([status] * count)
            random.shuffle(plan)
            return plan

        # Scale proportionally for other case counts
        plan = []
        total_base = sum(ANOMALY_DISTRIBUTION.values())
        for status, count in ANOMALY_DISTRIBUTION.items():
            scaled = int(round(count * (self.num_cases / total_base)))
            plan.extend([status] * scaled)

        while len(plan) < self.num_cases:
            plan.append("EXACT_MATCH")
        plan = plan[: self.num_cases]
        random.shuffle(plan)
        return plan

    def generate_cases(self):
        anomaly_plan = self._get_anomaly_plan()
        base_amounts = [
            Decimal("500.00"), Decimal("1250.00"), Decimal("2499.00"), Decimal("4999.00"),
            Decimal("7499.00"), Decimal("12000.00"), Decimal("25000.00"), Decimal("48500.00"),
            Decimal("120000.00"), Decimal("550000.00")
        ]

        start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
        end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
        time_span = int((end_dt - start_dt).total_seconds())

        for idx in range(1, self.num_cases + 1):
            case_id = f"CASE-{idx:05d}"
            anomaly = anomaly_plan[idx - 1]
            cust = self.customers[(idx - 1) % len(self.customers)]

            # Base amount
            base_amt = random.choice(base_amounts)
            cent_offset = Decimal(str(random.randint(0, 99))) / Decimal("100")
            order_amount = base_amt + cent_offset

            # Timestamps
            offset_sec = random.randint(0, time_span)
            order_dt = start_dt + timedelta(seconds=offset_sec)
            order_time_str = order_dt.strftime("%Y-%m-%d %H:%M:%S")

            pay_dt = order_dt + timedelta(minutes=random.randint(1, 10))
            pay_time_str = pay_dt.strftime("%Y-%m-%d %H:%M:%S")

            inv_dt = order_dt + timedelta(minutes=random.randint(0, 5))
            inv_date_str = inv_dt.strftime("%Y-%m-%d")

            settle_dt = pay_dt + timedelta(days=2)  # Normal T+2
            settle_date_str = settle_dt.strftime("%Y-%m-%d")

            bank_dt = settle_dt + timedelta(days=1)
            bank_date_str = bank_dt.strftime("%Y-%m-%d")

            tax_dt = inv_dt + timedelta(hours=random.randint(1, 3))
            tax_time_str = tax_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Entity IDs
            order_id = f"ORD-{idx:05d}"
            payment_id = f"PAY-{idx:05d}"
            settlement_id = f"SETTL-{idx:05d}"
            bank_txn_id = f"BTXN-{idx:05d}"
            invoice_id = f"INV-{idx:05d}"
            tax_id = f"TAX-{idx:05d}"

            # Calculate normal subtotal & tax
            tax_rate = DEFAULT_TAX_RATE
            subtotal = round_curr(order_amount / (Decimal("1.00") + tax_rate))
            invoice_tax_amt = round_curr(order_amount - subtotal)

            # Standard gateway fee
            fee_rate = DEFAULT_GATEWAY_FEE_RATE
            fee_amt = round_curr(order_amount * fee_rate)
            fee_tax = round_curr(fee_amt * DEFAULT_TAX_RATE)

            # Default attributes
            order_status = "COMPLETED"
            payment_status = "SUCCESS"
            payment_method = random.choice(["UPI", "CREDIT_CARD", "NET_BANKING", "RAZORPAY"])
            invoice_status = "ISSUED"

            refund_record: Optional[Refund] = None
            settlement_record: Optional[Settlement] = None
            bank_record: Optional[BankTransaction] = None
            tax_record: Optional[TaxRecord] = None

            # Anomaly specific variations
            if anomaly == "EXACT_MATCH":
                net_amt = round_curr(order_amount - fee_amt - fee_tax)
                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="EXACT_MATCH",
                    ground_truth_root_cause="All financial records match perfectly across all systems.",
                    ground_truth_expected_amount=net_amt,
                    ground_truth_actual_amount=net_amt,
                    ground_truth_should_auto_resolve=True,
                )

            elif anomaly == "PARTIAL_REFUND":
                refund_id = f"REF-{idx:05d}"
                refund_amt = round_curr(order_amount * Decimal("0.20"))  # 20% partial refund
                refund_dt = pay_dt + timedelta(hours=12)
                refund_record = Refund(
                    refund_id=refund_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    refund_amount=refund_amt,
                    refund_reason="Customer requested partial item return",
                    refund_status="COMPLETED",
                    created_at=refund_dt.strftime("%Y-%m-%d %H:%M:%S"),
                )
                net_amt = round_curr(order_amount - fee_amt - fee_tax - refund_amt)
                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id} (Net of Refund)",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="PARTIAL_REFUND",
                    ground_truth_root_cause=f"Valid partial refund of INR {refund_amt} processed cleanly.",
                    ground_truth_expected_amount=net_amt,
                    ground_truth_actual_amount=net_amt,
                    ground_truth_should_auto_resolve=True,
                )

            elif anomaly == "FEE_DIFFERENCE":
                # Charged 3.5% fee instead of contracted 2.0%
                actual_fee_amt = round_curr(order_amount * Decimal("0.035"))
                actual_fee_tax = round_curr(actual_fee_amt * DEFAULT_TAX_RATE)
                actual_net_amt = round_curr(order_amount - actual_fee_amt - actual_fee_tax)
                expected_net_amt = round_curr(order_amount - fee_amt - fee_tax)

                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=actual_fee_amt,
                    tax_amount=actual_fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=actual_net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=actual_net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="FEE_DIFFERENCE",
                    ground_truth_root_cause="Gateway fee charged at 3.5% instead of contracted 2.0%.",
                    ground_truth_expected_amount=expected_net_amt,
                    ground_truth_actual_amount=actual_net_amt,
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "TIMING_DIFFERENCE":
                net_amt = round_curr(order_amount - fee_amt - fee_tax)
                delayed_bank_dt = settle_dt + timedelta(days=15)
                bank_date_str = delayed_bank_dt.strftime("%Y-%m-%d")

                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Delayed Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="TIMING_DIFFERENCE",
                    ground_truth_root_cause="Bank transaction posted 15 days after settlement date.",
                    ground_truth_expected_amount=net_amt,
                    ground_truth_actual_amount=net_amt,
                    ground_truth_should_auto_resolve=True,
                )

            elif anomaly == "MISSING_SETTLEMENT":
                # Settlement and bank transaction missing
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="MISSING_SETTLEMENT",
                    ground_truth_root_cause="Payment captured in gateway but missing from settlement report.",
                    ground_truth_expected_amount=order_amount,
                    ground_truth_actual_amount=Decimal("0.00"),
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "DUPLICATE_TRANSACTION":
                net_amt = round_curr(order_amount - fee_amt - fee_tax)
                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                # Primary bank transaction
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                # Duplicate bank transaction record
                dup_bank_record = BankTransaction(
                    bank_txn_id=f"BTXN-DUP-{idx:05d}",
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id} (DUPLICATE ENTRY)",
                    transaction_date=bank_date_str,
                )
                self.bank_txns.append(dup_bank_record)

                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="DUPLICATE_TRANSACTION",
                    ground_truth_root_cause="Duplicate credit entry posted to bank ledger for single settlement.",
                    ground_truth_expected_amount=net_amt,
                    ground_truth_actual_amount=net_amt * Decimal("2.00"),
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "AMOUNT_MISMATCH":
                # Settlement gross amount is 95% of payment amount
                actual_gross = round_curr(order_amount * Decimal("0.95"))
                actual_net_amt = round_curr(actual_gross - fee_amt - fee_tax)
                expected_net_amt = round_curr(order_amount - fee_amt - fee_tax)

                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=actual_gross,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=actual_net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=actual_net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="AMOUNT_MISMATCH",
                    ground_truth_root_cause=f"Settlement gross amount ({actual_gross}) does not match payment amount ({order_amount}).",
                    ground_truth_expected_amount=expected_net_amt,
                    ground_truth_actual_amount=actual_net_amt,
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "TAX_MISMATCH":
                net_amt = round_curr(order_amount - fee_amt - fee_tax)
                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                # Disagreeing tax record (12% instead of 18%)
                mismatched_tax_amt = round_curr(subtotal * Decimal("0.12"))
                tax_record = TaxRecord(
                    tax_id=tax_id,
                    case_id=case_id,
                    invoice_id=invoice_id,
                    tax_type="GST_OUTPUT",
                    taxable_amount=subtotal,
                    tax_rate=Decimal("0.12"),
                    tax_amount=mismatched_tax_amt,
                    filing_period=inv_dt.strftime("%Y-%m"),
                    recorded_at=tax_time_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="TAX_MISMATCH",
                    ground_truth_root_cause=f"Tax record tax amount ({mismatched_tax_amt}) disagrees with invoice tax ({invoice_tax_amt}).",
                    ground_truth_expected_amount=invoice_tax_amt,
                    ground_truth_actual_amount=mismatched_tax_amt,
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "UNKNOWN_ADJUSTMENT":
                adj_amt = Decimal("-450.00")
                net_amt_with_adj = round_curr(order_amount - fee_amt - fee_tax + adj_amt)
                net_amt_no_adj = round_curr(order_amount - fee_amt - fee_tax)

                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=adj_amt,
                    net_amount=net_amt_with_adj,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt_with_adj,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id} (Unexplained Adj)",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="UNKNOWN_ADJUSTMENT",
                    ground_truth_root_cause="Settlement includes unexplained negative adjustment of -450.00.",
                    ground_truth_expected_amount=net_amt_no_adj,
                    ground_truth_actual_amount=net_amt_with_adj,
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "CONFLICTING_RECORDS":
                order_status = "CANCELLED"
                payment_status = "SUCCESS"
                net_amt = round_curr(order_amount - fee_amt - fee_tax)

                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id=settlement_id,
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description=f"Razorpay Payout Ref {settlement_id}",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="CONFLICTING_RECORDS",
                    ground_truth_root_cause="Order status is CANCELLED but payment succeeded and was settled without refund.",
                    ground_truth_expected_amount=Decimal("0.00"),
                    ground_truth_actual_amount=order_amount,
                    ground_truth_should_auto_resolve=False,
                )

            elif anomaly == "AMBIGUOUS_CASE":
                net_amt = round_curr(order_amount - fee_amt - fee_tax)
                settlement_record = Settlement(
                    settlement_id=settlement_id,
                    case_id=case_id,
                    payment_id=payment_id,
                    gross_amount=order_amount,
                    fee_amount=fee_amt,
                    tax_amount=fee_tax,
                    adjustment_amount=Decimal("0.00"),
                    net_amount=net_amt,
                    settlement_status="SETTLED",
                    settlement_date=settle_date_str,
                )
                bank_record = BankTransaction(
                    bank_txn_id=bank_txn_id,
                    case_id=case_id,
                    reference_id="PG_BULK_TRANSFER_BATCH",
                    amount=net_amt,
                    transaction_type="CREDIT",
                    description="Razorpay Bulk Transfer Batch (Ref Vague)",
                    transaction_date=bank_date_str,
                )
                gt = GroundTruth(
                    case_id=case_id,
                    ground_truth_status="AMBIGUOUS_CASE",
                    ground_truth_root_cause="Bank transaction references vague bulk transfer batch ID matching multiple candidates.",
                    ground_truth_expected_amount=net_amt,
                    ground_truth_actual_amount=net_amt,
                    ground_truth_should_auto_resolve=False,
                )

            # Common Tax Record if not explicitly set by anomaly
            if tax_record is None:
                tax_record = TaxRecord(
                    tax_id=tax_id,
                    case_id=case_id,
                    invoice_id=invoice_id,
                    tax_type="GST_OUTPUT",
                    taxable_amount=subtotal,
                    tax_rate=DEFAULT_TAX_RATE,
                    tax_amount=invoice_tax_amt,
                    filing_period=inv_dt.strftime("%Y-%m"),
                    recorded_at=tax_time_str,
                )

            # Create Order, Payment, Invoice
            order_record = Order(
                order_id=order_id,
                case_id=case_id,
                customer_id=cust.customer_id,
                order_amount=order_amount,
                currency=CURRENCY,
                order_status=order_status,
                created_at=order_time_str,
            )
            payment_record = Payment(
                payment_id=payment_id,
                case_id=case_id,
                order_id=order_id,
                customer_id=cust.customer_id,
                amount=order_amount,
                currency=CURRENCY,
                payment_method=payment_method,
                payment_status=payment_status,
                created_at=pay_time_str,
            )
            invoice_record = Invoice(
                invoice_id=invoice_id,
                case_id=case_id,
                order_id=order_id,
                customer_id=cust.customer_id,
                subtotal=subtotal,
                tax_rate=DEFAULT_TAX_RATE,
                tax_amount=invoice_tax_amt,
                total_amount=order_amount,
                invoice_status=invoice_status,
                invoice_date=inv_date_str,
            )

            # Append records
            self.orders.append(order_record)
            self.payments.append(payment_record)
            if refund_record:
                self.refunds.append(refund_record)
            if settlement_record:
                self.settlements.append(settlement_record)
            if bank_record:
                self.bank_txns.append(bank_record)
            self.invoices.append(invoice_record)
            self.tax_records.append(tax_record)
            self.ground_truth.append(gt)

    def generate_all(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        setup_logging(self.output_dir / "logs" if self.output_dir != OUTPUT_DIR else None)
        logging.info(f"Starting data generation with seed={self.seed}, num_cases={self.num_cases}")
        self.generate_customers()
        self.generate_cases()

        # Convert to dicts
        cust_dicts = [c.to_dict() for c in self.customers]
        ord_dicts = [o.to_dict() for o in self.orders]
        pay_dicts = [p.to_dict() for p in self.payments]
        ref_dicts = [r.to_dict() for r in self.refunds]
        set_dicts = [s.to_dict() for s in self.settlements]
        btx_dicts = [b.to_dict() for b in self.bank_txns]
        inv_dicts = [i.to_dict() for i in self.invoices]
        tax_dicts = [t.to_dict() for t in self.tax_records]
        gt_dicts = [g.to_dict() for g in self.ground_truth]

        # Validate dataset
        validate_dataset(
            customers=cust_dicts,
            orders=ord_dicts,
            payments=pay_dicts,
            refunds=ref_dicts,
            settlements=set_dicts,
            bank_txns=btx_dicts,
            invoices=inv_dicts,
            tax_records=tax_dicts,
            ground_truth=gt_dicts,
            expected_case_count=self.num_cases,
            expected_distribution=ANOMALY_DISTRIBUTION,
        )

        # Write to CSV files
        pd.DataFrame(cust_dicts).to_csv(self.output_dir / "customers.csv", index=False)
        pd.DataFrame(ord_dicts).to_csv(self.output_dir / "orders.csv", index=False)
        pd.DataFrame(pay_dicts).to_csv(self.output_dir / "payments.csv", index=False)
        pd.DataFrame(ref_dicts).to_csv(self.output_dir / "refunds.csv", index=False)
        pd.DataFrame(set_dicts).to_csv(self.output_dir / "settlements.csv", index=False)
        pd.DataFrame(btx_dicts).to_csv(self.output_dir / "bank_transactions.csv", index=False)
        pd.DataFrame(inv_dicts).to_csv(self.output_dir / "invoices.csv", index=False)
        pd.DataFrame(tax_dicts).to_csv(self.output_dir / "tax_records.csv", index=False)
        pd.DataFrame(gt_dicts).to_csv(self.output_dir / "ground_truth.csv", index=False)

        logging.info(f"All CSV files written successfully to {self.output_dir}")
        self.print_summary()

    def print_summary(self):
        print("FINCTRL AI Synthetic Data Generator\n")
        print(f"Seed: {self.seed}")
        print(f"Cases: {self.num_cases}\n")
        print(f"Customers: {len(self.customers)}")
        print(f"Orders: {len(self.orders)}")
        print(f"Payments: {len(self.payments)}")
        print(f"Refunds: {len(self.refunds)}")
        print(f"Settlements: {len(self.settlements)}")
        print(f"Bank Transactions: {len(self.bank_txns)}")
        print(f"Invoices: {len(self.invoices)}")
        print(f"Tax Records: {len(self.tax_records)}\n")

        print("Anomalies:")
        actual_dist: dict[str, int] = {}
        for gt in self.ground_truth:
            status = gt.ground_truth_status
            actual_dist[status] = actual_dist.get(status, 0) + 1
        for k, v in actual_dist.items():
            print(f"  {k}: {v}")

        print("\nValidation: PASS")
        print(f"\nOutput directory:\n  {self.output_dir}\n")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="FINCTRL AI synthetic financial dataset generator")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed (default: 42)")
    parser.add_argument("--cases", type=int, default=NUM_CASES, help="Number of cases to generate")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/output). Use a separate path for evaluation datasets.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    generator = FinancialDataGenerator(
        seed=args.seed,
        num_cases=args.cases,
        output_dir=args.output_dir,
    )
    generator.generate_all()
