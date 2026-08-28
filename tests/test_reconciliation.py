import sys
from pathlib import Path
from decimal import Decimal
import pytest
import pandas as pd

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.database import SessionLocal
from app.reconciliation.engine import reconcile_case, reconcile_all_cases
from app.reconciliation.models import ReconciliationStatus, ReasonCode
from app.reconciliation.constants import amounts_equal, amount_diff, AMOUNT_TOLERANCE, TIMING_TOLERANCE_DAYS
from data.generator import FinancialDataGenerator

GROUND_TRUTH_CSV = project_root / "data" / "output" / "ground_truth.csv"


@pytest.fixture(scope="module")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def ground_truth_map():
    df = pd.read_csv(GROUND_TRUTH_CSV)
    return {r["case_id"]: r["ground_truth_status"] for _, r in df.iterrows()}


def test_amount_and_timing_tolerances():
    assert amounts_equal(Decimal("100.00"), Decimal("100.005"))
    assert not amounts_equal(Decimal("100.00"), Decimal("100.02"))
    assert amount_diff(Decimal("105.00"), Decimal("100.00")) == Decimal("5.00")
    assert AMOUNT_TOLERANCE == Decimal("0.01")
    assert TIMING_TOLERANCE_DAYS == 3


def test_benchmark_100_cases_accuracy(db_session, ground_truth_map):
    results = reconcile_all_cases(db_session)
    assert len(results) == 100

    correct = 0
    for res in results:
        gt_status = ground_truth_map[res.case_id]
        if res.reason_code.value == gt_status:
            correct += 1

    accuracy = (correct / len(results)) * 100.0
    assert accuracy >= 90.0, f"Accuracy {accuracy}% is below 90%"


def test_reconciliation_anomaly_types(db_session, ground_truth_map):
    results = reconcile_all_cases(db_session)
    res_by_reason = {}
    for r in results:
        res_by_reason.setdefault(r.reason_code.value, []).append(r)

    # Verify key anomaly classifications
    assert "EXACT_MATCH" in res_by_reason
    assert "PARTIAL_REFUND" in res_by_reason
    assert "FEE_DIFFERENCE" in res_by_reason
    assert "TIMING_DIFFERENCE" in res_by_reason
    assert "MISSING_SETTLEMENT" in res_by_reason
    assert "DUPLICATE_TRANSACTION" in res_by_reason
    assert "AMOUNT_MISMATCH" in res_by_reason
    assert "TAX_MISMATCH" in res_by_reason
    assert "UNKNOWN_ADJUSTMENT" in res_by_reason
    assert "CONFLICTING_RECORDS" in res_by_reason
    assert "AMBIGUOUS_CASE" in res_by_reason

    # Verify exact match properties
    exact_res = res_by_reason["EXACT_MATCH"][0]
    assert exact_res.status == ReconciliationStatus.MATCHED
    assert exact_res.confidence == 1.00
    assert exact_res.needs_investigation is False
    assert exact_res.auto_resolvable is True

    # Verify fee difference properties
    fee_res = res_by_reason["FEE_DIFFERENCE"][0]
    assert fee_res.status == ReconciliationStatus.MISMATCH
    assert fee_res.needs_investigation is True
    assert fee_res.auto_resolvable is False

    # Verify missing settlement properties
    missing_res = res_by_reason["MISSING_SETTLEMENT"][0]
    assert missing_res.status == ReconciliationStatus.MISSING
    assert missing_res.needs_investigation is True


def test_evidence_and_rule_evaluations(db_session):
    res = reconcile_case(db_session, "CASE-00001")
    assert len(res.evidence) >= 1
    assert len(res.rule_evaluations) >= 1
    assert isinstance(res.expected_amount, Decimal)
    assert isinstance(res.actual_amount, Decimal)


def test_ground_truth_isolation():
    # Production modules must not import ground_truth
    import app.reconciliation.engine as eng
    import app.reconciliation.rules as rls
    import app.reconciliation.calculators as calc

    for mod in [eng, rls, calc]:
        mod_src = open(mod.__file__, "r", encoding="utf-8").read()
        assert "ground_truth.csv" not in mod_src
        assert "ground_truth_status" not in mod_src


def test_generalization_on_fresh_seed():
    """Generalization test evaluating the engine against a fresh seed (SEED = 123)."""
    gen = FinancialDataGenerator(seed=123, num_cases=100)
    gen.generate_customers()
    gen.generate_cases()

    gt_map = {gt.case_id: gt.ground_truth_status for gt in gen.ground_truth}

    # Evaluate using in-memory generated records via rules engine
    from app.reconciliation.rules import evaluate_reconciliation_case

    correct = 0
    for idx in range(1, 101):
        c_id = f"CASE-{idx:05d}"
        cust = gen.customers[(idx - 1) % len(gen.customers)]
        order = [o for o in gen.orders if o.case_id == c_id][0]
        payment = [p for p in gen.payments if p.case_id == c_id][0]
        refunds = [r for r in gen.refunds if r.case_id == c_id]
        settlements = [s for s in gen.settlements if s.case_id == c_id]
        settlement = settlements[0] if settlements else None
        bank_txns = [b for b in gen.bank_txns if b.case_id == c_id]
        invoices = [i for i in gen.invoices if i.case_id == c_id]
        invoice = invoices[0] if invoices else None
        tax_records = [t for t in gen.tax_records if t.case_id == c_id]
        tax_record = tax_records[0] if tax_records else None

        ctx = {
            "customer": cust,
            "order": order,
            "payment": payment,
            "refunds": refunds,
            "settlement": settlement,
            "bank_transactions": bank_txns,
            "invoice": invoice,
            "tax_record": tax_record,
        }

        res = evaluate_reconciliation_case(ctx, c_id)
        if res.reason_code.value == gt_map[c_id]:
            correct += 1

    generalization_accuracy = (correct / 100.0) * 100.0
    assert generalization_accuracy >= 90.0, f"Generalization accuracy {generalization_accuracy}% < 90%"
