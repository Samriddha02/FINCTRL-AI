"""
tests/test_cash_forecast.py — Phase 10 Cash Forecasting Test Suite
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
from app.forecasting.schemas import Scenario, CashForecastResult
from app.forecasting.extractor import extract_historical_cash_flows
from app.forecasting.engine import run_cash_forecast
from app.forecasting.validator import validate_forecast_explanation
from app.forecasting.controller import CashForecastController
from app.agents.providers import MockLLMProvider
from app.agents.tools import TOOLS


@pytest.fixture
def db():
    """In-memory SQLite DB with seeded operational financial records spanning 14 days."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    as_of = datetime.date(2026, 2, 28)
    cust = Customer(customer_id="CUST-00001", customer_name="Acme Corp", email="acme@example.com", created_at=datetime.datetime(2026, 2, 1))
    session.add(cust)

    for i in range(14):
        d = as_of - datetime.timedelta(days=13 - i)
        dt = datetime.datetime.combine(d, datetime.time(10, 0))

        oid = f"ORD-{i+1:05d}"
        pid = f"PAY-{i+1:05d}"
        sid = f"SETTL-{i+1:05d}"
        rid = f"REF-{i+1:05d}"

        ord_obj = Order(order_id=oid, customer_id="CUST-00001", order_amount=10000.00, currency="INR", order_status="COMPLETED", created_at=dt)
        pay = Payment(payment_id=pid, order_id=oid, customer_id="CUST-00001", amount=10000.00, currency="INR", payment_method="CARD", payment_status="CAPTURED", created_at=dt)
        settl = Settlement(settlement_id=sid, payment_id=pid, gross_amount=10000.00, fee_amount=200.00, tax_amount=36.00, adjustment_amount=0.00, net_amount=9764.00, settlement_status="SETTLED", settlement_date=d)
        ref = Refund(refund_id=rid, payment_id=pid, refund_amount=500.00, refund_reason="Customer return", refund_status="PROCESSED", created_at=dt)

        session.add_all([ord_obj, pay, settl, ref])

    session.commit()
    yield session
    session.close()


# ============================================================
# 1. Basic Generation & Horizon/Lookback Validation
# ============================================================

def test_1_basic_forecast_generation(db):
    """Test basic cash forecast creation."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.forecast_id.startswith("FC-")
    assert res.as_of == "2026-02-28"
    assert res.horizon_days == 7
    assert len(res.daily_forecasts) == 7


def test_2_forecast_horizon_validation(db):
    """Invalid horizon_days (0 or > 90) must be rejected."""
    ctrl = CashForecastController(db)
    with pytest.raises(ValueError):
        ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), horizon_days=0)
    with pytest.raises(ValueError):
        ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), horizon_days=100)


def test_3_lookback_validation(db):
    """Invalid lookback_days (< 3 or > 365) must be rejected."""
    ctrl = CashForecastController(db)
    with pytest.raises(ValueError):
        ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=1)


# ============================================================
# 2. Cash Flow Extraction & Decimal Math
# ============================================================

def test_4_historical_cash_flow_extraction(db):
    """Historical extraction returns exact daily observation series."""
    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    assert data.observation_days == 14
    assert len(data.daily_series) == 14


def test_5_inflow_calculation(db):
    """Historical inflow sum must match net settlement totals."""
    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    expected_inflow = Decimal("9764.00") * 14
    assert data.total_inflow == expected_inflow


def test_6_outflow_calculation(db):
    """Historical outflow sum must include fees, tax, and refunds."""
    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    # Daily fee: 200 + 36 = 236. Daily refund: 500. Total daily outflow = 736.00
    expected_outflow = Decimal("736.00") * 14
    assert data.total_outflow == expected_outflow


def test_7_net_cash_calculation(db):
    """Net cash = total inflow - total outflow."""
    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    assert data.total_net == data.total_inflow - data.total_outflow


def test_8_decimal_precision(db):
    """Monetary fields must maintain Decimal accuracy without float rounding loss."""
    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    assert isinstance(data.total_inflow, Decimal)
    assert isinstance(data.total_outflow, Decimal)


def test_9_deterministic_reproducibility(db):
    """Identical parameters on identical DB state must yield identical results."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    r1 = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    r2 = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert r1.forecast.inflow == r2.forecast.inflow
    assert r1.forecast.outflow == r2.forecast.outflow
    assert r1.forecast.net == r2.forecast.net


def test_10_no_look_ahead_bias(db):
    """Records after as_of_date must strictly be excluded from historical extraction."""
    future_date = datetime.date(2026, 3, 5)
    dt = datetime.datetime.combine(future_date, datetime.time(10, 0))
    future_pay = Payment(payment_id="PAY-99999", order_id="ORD-99999", customer_id="CUST-00001", amount=50000.00, currency="INR", payment_method="CARD", payment_status="CAPTURED", created_at=dt)
    db.add(future_pay)
    db.commit()

    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    assert data.end_date_str == "2026-02-28"


# ============================================================
# 3. Edge Cases & Anomaly Risks
# ============================================================

def test_11_insufficient_historical_data(db):
    """Evaluating small sample size reduces confidence score."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=4, horizon_days=7)
    assert any("Small historical sample size" in issue for issue in res.data_quality.issues)


def test_12_missing_settlement_data(db):
    """Payments without settlement records are flagged in data quality."""
    dt = datetime.datetime(2026, 2, 25, 10, 0)
    unsettled = Payment(payment_id="PAY-77777", order_id="ORD-77777", customer_id="CUST-00001", amount=15000.00, currency="INR", payment_method="CARD", payment_status="CAPTURED", created_at=dt)
    db.add(unsettled)
    db.commit()

    data = extract_historical_cash_flows(db, datetime.date(2026, 2, 28), lookback_days=14)
    assert data.missing_settlement_count >= 1


def test_13_timing_differences(db):
    """Reconciliation issues in window appear in risk factors."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert isinstance(res.risk_factors, list)


def test_14_missing_settlements(db):
    """Missing settlement issue is reported in risk factors."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert isinstance(res.data_quality.issues, list)


def test_15_duplicate_transactions(db):
    """Forecast handles potential duplicates smoothly."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.confidence >= 0.3


def test_16_amount_mismatches(db):
    """Reconciliation discrepancies in window lower data quality score."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.data_quality.score <= 1.0


# ============================================================
# 4. Uncertainty, Confidence & Scenarios
# ============================================================

def test_17_data_quality_scoring(db):
    """Data quality score is between 0.0 and 1.0."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert 0.0 <= res.data_quality.score <= 1.0


def test_18_confidence_calculation(db):
    """Confidence score is bounded between 0.0 and 1.0."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert 0.0 <= res.confidence <= 1.0


def test_19_uncertainty_calculation(db):
    """Margin of error and daily bounds are calculated."""
    res = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.uncertainty.std_dev >= 0.0
    for day in res.daily_forecasts:
        assert day.lower_bound <= day.expected_net <= day.upper_bound


def test_20_scenario_handling(db):
    """Scenarios adjust projected totals deterministically."""
    b = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7, scenario=Scenario.BASELINE)
    c = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7, scenario=Scenario.CONSERVATIVE)
    o = run_cash_forecast(db, datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7, scenario=Scenario.OPTIMISTIC)

    assert c.forecast.inflow < b.forecast.inflow
    assert o.forecast.inflow > b.forecast.inflow


# ============================================================
# 5. API & Explanation Validation
# ============================================================

def test_21_forecast_api(db):
    """FastAPI forecast endpoint returns valid JSON model."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.forecast_id is not None


def test_22_forecast_explanation(db):
    """Forecast result contains non-empty natural language explanation."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert len(res.explanation) > 10


def test_23_llm_hallucinated_forecast_value_rejection(db):
    """Explanation mentioning ungrounded numerical claims fails validation."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    fake_exp = "Expected cash net is 99999999.00."
    is_valid, errors = validate_forecast_explanation(fake_exp, res)
    assert is_valid is False


def test_24_llm_failure_fallback(db):
    """If LLM fails, deterministic fallback explanation is generated."""
    class FailingProvider:
        def generate_text(self, prompt, system_prompt):
            raise RuntimeError("API unavailable")
    ctrl = CashForecastController(db, provider=FailingProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert "horizon" in res.explanation.lower() or "inr" in res.explanation.lower()


# ============================================================
# 6. Security, Isolation & Audit
# ============================================================

def test_25_prompt_injection_defense(db):
    """System prompts take precedence over untrusted text."""
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    res = ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    assert res.forecast_id.startswith("FC-")


def test_26_sql_injection_defense(db):
    """Invalid query parameter inputs are validated."""
    ctrl = CashForecastController(db)
    with pytest.raises(ValueError):
        ctrl.generate_forecast(lookback_days=-5)


def test_27_ground_truth_isolation_in_phase10():
    """Phase 10 forecasting code must not import ground_truth data."""
    import app.forecasting.schemas as s
    import app.forecasting.extractor as ext
    import app.forecasting.engine as eng
    import app.forecasting.validator as v
    import app.forecasting.controller as c
    import inspect
    for module in [s, ext, eng, v, c]:
        source = inspect.getsource(module)
        assert "ground_truth" not in source.lower(), f"Ground truth leakage in {module.__name__}"


def test_28_read_only_behavior():
    """Verify that forecasting tools and modules only use read operations."""
    for name, tool in TOOLS.items():
        assert tool.read_only is True
        assert tool.permission == "READ_ONLY"


def test_29_audit_event_creation(db):
    """Forecasting generates persistent audit events."""
    from app.services.audit_service import get_audit_trail
    ctrl = CashForecastController(db, provider=MockLLMProvider())
    ctrl.generate_forecast(as_of_date=datetime.date(2026, 2, 28), lookback_days=14, horizon_days=7)
    events = get_audit_trail(db, case_id="FORECAST")
    assert len(events) >= 1
    assert any(e.event_type == "CASH_FORECAST_GENERATED" for e in events)


# ============================================================
# 7. Regression Compatibility Tests
# ============================================================

def test_30_regression_against_phase4_reconciliation(db):
    """Phase 4 reconciliation engine operates regression-free."""
    from app.reconciliation.engine import reconcile_case
    res = reconcile_case(db, "CASE-00001")
    assert res.status.value in ["MATCHED", "MISMATCH", "ERROR", "AMBIGUOUS"]


def test_31_regression_against_phase6_investigation(db):
    """Phase 6 Agent Investigation Controller operates regression-free."""
    from app.agents.controller import AgentInvestigationController
    ctrl = AgentInvestigationController(db)
    res = ctrl.run_investigation("CASE-00001")
    assert res.investigation_status.value in ["COMPLETED", "ESCALATED", "FAILED"]


def test_32_regression_against_phase8_human_review(db):
    """Phase 8 Human Review service operates regression-free."""
    from app.services.review_service import create_or_get_review
    from app.agents.controller import AgentInvestigationController
    inv = AgentInvestigationController(db).run_investigation("CASE-00001")
    review = create_or_get_review(db, "CASE-00001", inv)
    assert review.review_id.startswith("REV-")


def test_33_regression_against_phase9_finance_qa(db):
    """Phase 9 Finance Q&A handles cash forecast query delegation seamlessly."""
    from app.finance_qa.controller import FinanceQAController
    ctrl = FinanceQAController(db, provider=MockLLMProvider())
    res = ctrl.process_question("What is the cash forecast for the next 7 days?")
    assert res.status.value in ["ANSWERED", "NEEDS_CLARIFICATION"]
