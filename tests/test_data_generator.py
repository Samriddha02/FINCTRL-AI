import sys
from pathlib import Path
import pytest
import pandas as pd
from decimal import Decimal

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from data.generator import FinancialDataGenerator
from data.config import SEED, NUM_CASES, ANOMALY_DISTRIBUTION, OUTPUT_FILES


@pytest.fixture(scope="module")
def generated_dataset():
    gen = FinancialDataGenerator(seed=SEED, num_cases=NUM_CASES)
    gen.generate_all()
    return gen


def test_generator_case_count(generated_dataset):
    assert len(generated_dataset.ground_truth) == 100
    assert len(generated_dataset.orders) == 100
    assert len(generated_dataset.payments) == 100


def test_unique_ids(generated_dataset):
    cust_ids = [c.customer_id for c in generated_dataset.customers]
    assert len(cust_ids) == len(set(cust_ids))

    non_dup_order_ids = [
        o.order_id
        for o in generated_dataset.orders
        if "DUPLICATE_TRANSACTION" not in o.case_id
    ]
    assert len(non_dup_order_ids) == len(set(non_dup_order_ids))


def test_relational_integrity(generated_dataset):
    cust_set = {c.customer_id for c in generated_dataset.customers}
    order_set = {o.order_id for o in generated_dataset.orders}
    payment_set = {p.payment_id for p in generated_dataset.payments}

    for order in generated_dataset.orders:
        assert order.customer_id in cust_set

    for payment in generated_dataset.payments:
        assert payment.customer_id in cust_set
        assert payment.order_id in order_set

    for refund in generated_dataset.refunds:
        assert refund.payment_id in payment_set

    for settlement in generated_dataset.settlements:
        assert settlement.payment_id in payment_set


def test_ground_truth_coverage(generated_dataset):
    case_ids = {o.case_id for o in generated_dataset.orders}
    gt_case_ids = {gt.case_id for gt in generated_dataset.ground_truth}
    assert case_ids == gt_case_ids


def test_reproducibility():
    gen1 = FinancialDataGenerator(seed=42, num_cases=50)
    gen1.generate_customers()
    gen1.generate_cases()

    gen2 = FinancialDataGenerator(seed=42, num_cases=50)
    gen2.generate_customers()
    gen2.generate_cases()

    assert [c.customer_id for c in gen1.customers] == [c.customer_id for c in gen2.customers]
    assert [o.order_amount for o in gen1.orders] == [o.order_amount for o in gen2.orders]
    assert [gt.ground_truth_status for gt in gen1.ground_truth] == [
        gt.ground_truth_status for gt in gen2.ground_truth
    ]


def test_normal_invoice_totals(generated_dataset):
    gt_map = {gt.case_id: gt.ground_truth_status for gt in generated_dataset.ground_truth}
    for inv in generated_dataset.invoices:
        if gt_map[inv.case_id] in ["EXACT_MATCH", "TIMING_DIFFERENCE", "PARTIAL_REFUND"]:
            subtotal = inv.subtotal
            tax_amt = inv.tax_amount
            total = inv.total_amount
            assert abs((subtotal + tax_amt) - total) <= Decimal("0.05")


def test_normal_settlement_calculations(generated_dataset):
    gt_map = {gt.case_id: gt.ground_truth_status for gt in generated_dataset.ground_truth}
    for s in generated_dataset.settlements:
        if gt_map[s.case_id] in ["EXACT_MATCH", "TIMING_DIFFERENCE"]:
            expected_net = s.gross_amount - s.fee_amount - s.tax_amount + s.adjustment_amount
            assert abs(expected_net - s.net_amount) <= Decimal("0.05")


def test_anomaly_distribution(generated_dataset):
    counts = {}
    for gt in generated_dataset.ground_truth:
        status = gt.ground_truth_status
        counts[status] = counts.get(status, 0) + 1

    for status, expected_count in ANOMALY_DISTRIBUTION.items():
        assert counts.get(status, 0) == expected_count


def test_no_ground_truth_leakage_in_financial_csvs():
    financial_files = [
        OUTPUT_FILES["customers"],
        OUTPUT_FILES["orders"],
        OUTPUT_FILES["payments"],
        OUTPUT_FILES["refunds"],
        OUTPUT_FILES["settlements"],
        OUTPUT_FILES["bank_transactions"],
        OUTPUT_FILES["invoices"],
        OUTPUT_FILES["tax_records"],
    ]

    for filepath in financial_files:
        df = pd.read_csv(filepath)
        headers = [col.lower() for col in df.columns]
        for col in headers:
            assert "ground_truth" not in col
            assert "anomaly" not in col
            assert "root_cause" not in col
