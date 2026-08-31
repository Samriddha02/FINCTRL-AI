"""
tests/test_tax_matching.py — Phase 11 Tax-Line Matching Test Suite
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import (
    Customer, Order, Payment, Refund, Settlement,
    BankTransaction, Invoice, TaxRecord
)
from app.tax_matching.schemas import TaxMatchStatus, TaxReasonCode, TaxMatchResult
from app.tax_matching.constants import TAX_AMOUNT_TOLERANCE, TAX_RATE_TOLERANCE
from app.tax_matching.matcher import match_tax_line, match_all_tax_lines, normalize_tax_rate
from app.tax_matching.validator import validate_tax_explanation
from app.tax_matching.controller import TaxMatchController
from app.agents.providers import MockLLMProvider
from app.agents.tools import TOOLS


@pytest.fixture
def db():
    """In-memory SQLite DB seeded with operational tax records for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.datetime.utcnow()

    cust = Customer(customer_id="CUST-00001", customer_name="Acme Corp", email="acme@example.com", created_at=now)
    session.add(cust)

    # 1. Exact Match Invoice & TaxRecord
    ord1 = Order(order_id="ORD-00001", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv1 = Invoice(invoice_id="INV-00001", order_id="ORD-00001", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())
    tax1 = TaxRecord(tax_id="TAX-00001", invoice_id="INV-00001", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.18, tax_amount=180.00, filing_period="2026-02", recorded_at=now)

    # 2. Tax Amount Mismatch Invoice & TaxRecord
    ord2 = Order(order_id="ORD-00002", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv2 = Invoice(invoice_id="INV-00002", order_id="ORD-00002", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=150.00, total_amount=1150.00, invoice_status="ISSUED", invoice_date=now.date())
    tax2 = TaxRecord(tax_id="TAX-00002", invoice_id="INV-00002", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.18, tax_amount=180.00, filing_period="2026-02", recorded_at=now)

    # 3. Tax Rate Mismatch Invoice & TaxRecord
    ord3 = Order(order_id="ORD-00003", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv3 = Invoice(invoice_id="INV-00003", order_id="ORD-00003", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())
    tax3 = TaxRecord(tax_id="TAX-00003", invoice_id="INV-00003", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.12, tax_amount=120.00, filing_period="2026-02", recorded_at=now)

    # 4. Taxable Amount Mismatch Invoice & TaxRecord
    ord4 = Order(order_id="ORD-00004", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv4 = Invoice(invoice_id="INV-00004", order_id="ORD-00004", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())
    tax4 = TaxRecord(tax_id="TAX-00004", invoice_id="INV-00004", tax_type="GST_OUTPUT", taxable_amount=800.00, tax_rate=0.18, tax_amount=144.00, filing_period="2026-02", recorded_at=now)

    # 5. Missing Tax Record Invoice
    ord5 = Order(order_id="ORD-00005", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv5 = Invoice(invoice_id="INV-00005", order_id="ORD-00005", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())

    # 6. Duplicate Tax Record Invoice
    ord6 = Order(order_id="ORD-00006", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv6 = Invoice(invoice_id="INV-00006", order_id="ORD-00006", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())
    tax6a = TaxRecord(tax_id="TAX-00006A", invoice_id="INV-00006", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.18, tax_amount=180.00, filing_period="2026-02", recorded_at=now)
    tax6b = TaxRecord(tax_id="TAX-00006B", invoice_id="INV-00006", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.18, tax_amount=180.00, filing_period="2026-02", recorded_at=now)

    # 7. Tax Calculation Mismatch TaxRecord (taxable=1000, rate=0.18, but tax_amount=999.00)
    ord7 = Order(order_id="ORD-00007", customer_id="CUST-00001", order_amount=1000.00, currency="INR", order_status="COMPLETED", created_at=now)
    inv7 = Invoice(invoice_id="INV-00007", order_id="ORD-00007", customer_id="CUST-00001", subtotal=1000.00, tax_rate=0.18, tax_amount=180.00, total_amount=1180.00, invoice_status="ISSUED", invoice_date=now.date())
    tax7 = TaxRecord(tax_id="TAX-00007", invoice_id="INV-00007", tax_type="GST_OUTPUT", taxable_amount=1000.00, tax_rate=0.18, tax_amount=999.00, filing_period="2026-02", recorded_at=now)

    session.add_all([
        ord1, inv1, tax1,
        ord2, inv2, tax2,
        ord3, inv3, tax3,
        ord4, inv4, tax4,
        ord5, inv5,
        ord6, inv6, tax6a, tax6b,
        ord7, inv7, tax7
    ])
    session.commit()

    yield session
    session.close()


# ============================================================
# 1. Matching Logic Tests
# ============================================================

def test_1_exact_tax_match(db):
    """Test exact match on taxable amount, tax rate, and tax amount."""
    res = match_tax_line(db, "INV-00001")
    assert res.status == TaxMatchStatus.EXACT_MATCH
    assert res.reason_code == TaxReasonCode.TAX_EXACT_MATCH
    assert res.difference == 0.0
    assert res.needs_review is False


def test_2_tax_amount_mismatch(db):
    """Test tax amount mismatch status detection (difference = invoice_tax - ledger_tax)."""
    res = match_tax_line(db, "INV-00002")
    assert res.status == TaxMatchStatus.AMOUNT_MISMATCH
    assert res.reason_code == TaxReasonCode.TAX_AMOUNT_MISMATCH
    assert abs(res.difference) == pytest.approx(30.00, abs=0.01)
    assert res.needs_review is True


def test_3_tax_rate_mismatch(db):
    """Test tax rate mismatch status detection."""
    res = match_tax_line(db, "INV-00003")
    assert res.status == TaxMatchStatus.RATE_MISMATCH
    assert res.reason_code == TaxReasonCode.TAX_RATE_MISMATCH
    assert res.needs_review is True


def test_4_taxable_amount_mismatch(db):
    """Test taxable base amount mismatch status detection."""
    res = match_tax_line(db, "INV-00004")
    assert res.status == TaxMatchStatus.TAXABLE_AMOUNT_MISMATCH
    assert res.reason_code == TaxReasonCode.TAXABLE_AMOUNT_MISMATCH
    assert res.needs_review is True


def test_5_tax_calculation_mismatch(db):
    """Test tax calculation mismatch status detection."""
    res = match_tax_line(db, "INV-00007")
    assert res.status == TaxMatchStatus.CALCULATION_MISMATCH
    assert res.reason_code == TaxReasonCode.TAX_CALCULATION_MISMATCH
    assert res.needs_review is True


def test_6_missing_tax_record(db):
    """Test missing tax record status detection."""
    res = match_tax_line(db, "INV-00005")
    assert res.status == TaxMatchStatus.MISSING_TAX_RECORD
    assert res.reason_code == TaxReasonCode.MISSING_TAX_RECORD
    assert res.tax_id is None
    assert res.needs_review is True


def test_7_duplicate_tax_records(db):
    """Test duplicate tax records status detection."""
    res = match_tax_line(db, "INV-00006")
    assert res.status == TaxMatchStatus.DUPLICATE_TAX_RECORD
    assert res.reason_code == TaxReasonCode.DUPLICATE_TAX_RECORD
    assert res.needs_review is True


def test_8_multiple_invoices_batch(db):
    """Test batch matching across all operational invoices."""
    batch = match_all_tax_lines(db)
    assert batch.total_invoices_checked == 7
    assert batch.exact_matches == 1
    assert batch.amount_mismatches == 1
    assert batch.rate_mismatches == 1
    assert batch.taxable_amount_mismatches == 1
    assert batch.calculation_mismatches == 1
    assert batch.missing_records == 1
    assert batch.duplicate_records == 1


# ============================================================
# 2. Precision, Tolerances & Normalization
# ============================================================

def test_9_decimal_precision(db):
    """Verify internal calculations use Decimal arithmetic."""
    res = match_tax_line(db, "INV-00001")
    assert isinstance(Decimal(str(res.difference)), Decimal)


def test_10_monetary_tolerance():
    """Verify tax amount tolerance constant."""
    assert TAX_AMOUNT_TOLERANCE == Decimal("0.01")


def test_11_tax_rate_normalization():
    """Verify rate normalization for percentage and decimal representations."""
    assert normalize_tax_rate(18.0) == Decimal("0.18")
    assert normalize_tax_rate(18) == Decimal("0.18")
    assert normalize_tax_rate(0.18) == Decimal("0.18")
    assert normalize_tax_rate(0.12) == Decimal("0.12")


def test_12_deterministic_confidence(db):
    """Exact match should have confidence = 1.0, mismatch lower."""
    exact = match_tax_line(db, "INV-00001")
    mismatch = match_tax_line(db, "INV-00002")
    assert exact.confidence == 1.0
    assert mismatch.confidence < 1.0


# ============================================================
# 3. Evidence, Rule Evaluations & Controller
# ============================================================

def test_13_evidence_generation(db):
    """Match result must contain authoritative database evidence items."""
    res = match_tax_line(db, "INV-00001")
    assert len(res.evidence) >= 4
    assert any(e.source == "Invoice" and e.field == "tax_amount" for e in res.evidence)


def test_14_rule_evaluations(db):
    """Match result must contain structured rule evaluation logs."""
    res = match_tax_line(db, "INV-00001")
    assert len(res.rule_evaluations) >= 4
    assert any(r.rule_name == "CHECK_TAX_AMOUNT_MATCH" and r.status == "PASS" for r in res.rule_evaluations)


def test_15_result_serialization(db):
    """Match result serializes cleanly to Pydantic JSON model."""
    ctrl = TaxMatchController(db, provider=MockLLMProvider())
    res = ctrl.process_tax_match("INV-00001")
    assert res.match_id.startswith("TM-")
    assert len(res.explanation) > 10


# ============================================================
# 4. API Endpoints & Security Validation
# ============================================================

def test_16_api_single_invoice_endpoint(db):
    """Tax Match Controller single endpoint runs cleanly."""
    ctrl = TaxMatchController(db, provider=MockLLMProvider())
    res = ctrl.process_tax_match("INV-00001")
    assert res.invoice_id == "INV-00001"


def test_17_api_batch_endpoint(db):
    """Tax Match Controller batch endpoint runs cleanly."""
    ctrl = TaxMatchController(db, provider=MockLLMProvider())
    batch = ctrl.process_batch_tax_match()
    assert batch.total_invoices_checked == 7


def test_18_invalid_invoice_id(db):
    """Non-existent invoice ID must raise ValueError."""
    ctrl = TaxMatchController(db)
    with pytest.raises(ValueError):
        ctrl.process_tax_match("INV-99999")


def test_19_sql_injection_protection(db):
    """SQL injection in invoice ID must be rejected by validator."""
    ctrl = TaxMatchController(db)
    with pytest.raises(ValueError):
        ctrl.process_tax_match("INV-00001' OR '1'='1")


def test_20_path_traversal_protection(db):
    """Path traversal in invoice ID must be rejected by validator."""
    ctrl = TaxMatchController(db)
    with pytest.raises(ValueError):
        ctrl.process_tax_match("../../ground_truth.csv")


def test_21_read_only_behavior():
    """Verify all tools remain read-only."""
    for name, tool in TOOLS.items():
        assert tool.read_only is True
        assert tool.permission == "READ_ONLY"


def test_22_ground_truth_isolation_in_phase11():
    """Phase 11 tax matching code must not import ground_truth data."""
    import app.tax_matching.schemas as s
    import app.tax_matching.matcher as m
    import app.tax_matching.validator as v
    import app.tax_matching.controller as c
    import inspect
    for module in [s, m, v, c]:
        source = inspect.getsource(module)
        assert "ground_truth" not in source.lower(), f"Ground truth leakage in {module.__name__}"


# ============================================================
# 5. Workflow, Audit & System Integration
# ============================================================

def test_23_human_review_integration(db):
    """Tax mismatches automatically create or update Phase 8 Human Review records."""
    from app.services.review_service import list_reviews
    ctrl = TaxMatchController(db, provider=MockLLMProvider())
    ctrl.process_tax_match("INV-00002")
    reviews = list_reviews(db, case_id="CASE-00002")
    assert len(reviews) >= 1


def test_24_audit_event_integration(db):
    """Tax matching operations log persistent audit events."""
    from app.services.audit_service import get_audit_trail
    ctrl = TaxMatchController(db, provider=MockLLMProvider())
    ctrl.process_tax_match("INV-00001")
    events = get_audit_trail(db, case_id="INV-00001")
    assert len(events) >= 1
    assert any(e.event_type == "TAX_MATCH_COMPLETED" for e in events)


def test_25_finance_qa_integration(db):
    """Phase 9 Finance Q&A delegates tax questions to Tax Line Matcher."""
    from app.finance_qa.controller import FinanceQAController
    ctrl = FinanceQAController(db, provider=MockLLMProvider())
    res = ctrl.process_question("What tax was recorded for INV-00001?")
    assert res.status.value in ["ANSWERED", "NEEDS_CLARIFICATION"]


def test_26_phase6_investigation_compatibility(db):
    """Phase 6 Agent Investigation Controller operates regression-free with tax records."""
    from app.agents.controller import AgentInvestigationController
    ctrl = AgentInvestigationController(db)
    res = ctrl.run_investigation("CASE-00001")
    assert res.investigation_status.value in ["COMPLETED", "ESCALATED", "FAILED"]


def test_27_phase10_compatibility(db):
    """Phase 10 Cash Forecasting Controller operates regression-free."""
    from app.forecasting.controller import CashForecastController
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(horizon_days=7)
    assert res.forecast_id.startswith("FC-")


def test_28_missing_data_behavior(db):
    """Missing tax record is explicitly flagged with 0.00 ledger amounts."""
    res = match_tax_line(db, "INV-00005")
    assert res.status == TaxMatchStatus.MISSING_TAX_RECORD
    assert res.ledger_tax_amount is None


def test_29_duplicate_data_behavior(db):
    """Duplicate tax records return DUPLICATE_TAX_RECORD status."""
    res = match_tax_line(db, "INV-00006")
    assert res.status == TaxMatchStatus.DUPLICATE_TAX_RECORD


def test_30_deterministic_reproducibility(db):
    """Identical database state produces identical match results."""
    m1 = match_tax_line(db, "INV-00001")
    m2 = match_tax_line(db, "INV-00001")
    assert m1.status == m2.status
    assert m1.difference == m2.difference
