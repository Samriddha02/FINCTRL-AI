import math
import datetime
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import Order
from app.reconciliation.engine import reconcile_case
from app.forecasting.schemas import (
    CashForecastResult,
    Scenario,
    DailyForecastItem,
    HistoricalSummary,
    ForecastSummary,
    UncertaintyMetrics,
    DataQualityReport
)
from app.forecasting.extractor import HistoricalCashFlowData, extract_historical_cash_flows

logger = logging.getLogger("forecast_engine")


def run_cash_forecast(
    db: Session,
    as_of_date: datetime.date,
    lookback_days: int = 30,
    horizon_days: int = 7,
    scenario: Scenario = Scenario.BASELINE
) -> CashForecastResult:
    """Executes deterministic cash forecasting pipeline using Decimal arithmetic."""
    # 1. Validation of parameters
    if horizon_days <= 0 or horizon_days > 90:
        raise ValueError(f"Invalid horizon_days '{horizon_days}'. Must be between 1 and 90 days.")
    if lookback_days < 3 or lookback_days > 365:
        raise ValueError(f"Invalid lookback_days '{lookback_days}'. Must be between 3 and 365 days.")

    # 2. Historical Cash-Flow Extraction (strictly as_of date boundary)
    hist_data: HistoricalCashFlowData = extract_historical_cash_flows(db, as_of_date, lookback_days)

    # 3. Calculate Historical Aggregates
    n_days = len(hist_data.daily_series)
    if n_days == 0:
        avg_inflow_dec = Decimal("0.00")
        avg_outflow_dec = Decimal("0.00")
        avg_net_dec = Decimal("0.00")
        std_dev_float = 0.0
    else:
        avg_inflow_dec = hist_data.total_inflow / Decimal(str(n_days))
        avg_outflow_dec = hist_data.total_outflow / Decimal(str(n_days))
        avg_net_dec = hist_data.total_net / Decimal(str(n_days))

        # Calculate standard deviation of historical daily net cash
        net_values = [float(p.net) for p in hist_data.daily_series]
        mean_net = float(avg_net_dec)
        variance = sum((x - mean_net) ** 2 for x in net_values) / float(n_days if n_days > 1 else 1)
        std_dev_float = math.sqrt(variance)

    # 4. Integrate with Phase 4 Reconciliation Engine for Risk & Data Quality
    recon_issues, unresolved_cases_count = _evaluate_reconciliation_risks(db, as_of_date, lookback_days)

    # 5. Calculate Data Quality & Confidence Scores
    dq_issues = []
    dq_score = 1.0

    if hist_data.missing_settlement_count > 0:
        dq_issues.append(f"{hist_data.missing_settlement_count} payment(s) missing matching settlement records.")
        dq_score -= min(0.2, hist_data.missing_settlement_count * 0.02)

    if unresolved_cases_count > 0:
        dq_issues.append(f"{unresolved_cases_count} unresolved reconciliation case(s) in historical window.")
        dq_score -= min(0.3, unresolved_cases_count * 0.05)

    if n_days < 7:
        dq_issues.append(f"Small historical sample size ({n_days} days).")
        dq_score -= 0.15

    dq_score = max(0.2, min(1.0, round(dq_score, 2)))

    data_quality_report = DataQualityReport(
        score=dq_score,
        issues=dq_issues + recon_issues,
        missing_settlement_count=hist_data.missing_settlement_count,
        unresolved_reconciliation_count=unresolved_cases_count
    )

    # Deterministic Overall Confidence Score
    base_confidence = 0.90
    if std_dev_float > float(abs(avg_net_dec)) * 0.5 and float(abs(avg_net_dec)) > 0:
        base_confidence -= 0.10
    base_confidence *= dq_score
    overall_confidence = max(0.30, min(0.95, round(base_confidence, 2)))

    # 6. Apply Scenario Multipliers & Deterministic Forecasting
    inflow_mult = Decimal("1.00")
    outflow_mult = Decimal("1.00")
    assumptions = [
        f"Historical lookback window: {lookback_days} days ({hist_data.start_date_str} to {hist_data.end_date_str}).",
        f"Baseline daily projected inflow: INR {avg_inflow_dec:.2f}, outflow: INR {avg_outflow_dec:.2f}.",
        "Monetary values calculated with Decimal precision."
    ]

    if scenario == Scenario.CONSERVATIVE:
        inflow_mult = Decimal("0.90")  # 10% discount on inflows
        outflow_mult = Decimal("1.10")  # 10% buffer on outflows
        assumptions.append("Conservative scenario: 10% inflow discount and 10% outflow buffer applied.")
    elif scenario == Scenario.OPTIMISTIC:
        inflow_mult = Decimal("1.10")  # 10% premium on inflows
        outflow_mult = Decimal("0.95")  # 5% reduction on outflows
        assumptions.append("Optimistic scenario: 10% inflow premium and 5% outflow reduction applied.")
    else:
        assumptions.append("Baseline scenario: Expected historical trend continuation.")

    # Generate Daily Forecast Items for horizon_days
    daily_forecasts: List[DailyForecastItem] = []
    proj_total_inflow = Decimal("0.00")
    proj_total_outflow = Decimal("0.00")
    proj_total_net = Decimal("0.00")

    forecast_start_date = as_of_date + datetime.timedelta(days=1)
    margin_of_error = round(1.96 * std_dev_float, 2)

    for i in range(horizon_days):
        target_date = forecast_start_date + datetime.timedelta(days=i)
        
        # Day-of-week multiplier if weekday variation exists
        day_inflow = avg_inflow_dec * inflow_mult
        day_outflow = avg_outflow_dec * outflow_mult
        day_net = day_inflow - day_outflow

        lower = round(float(day_net) - margin_of_error, 2)
        upper = round(float(day_net) + margin_of_error, 2)

        proj_total_inflow += day_inflow
        proj_total_outflow += day_outflow
        proj_total_net += day_net

        daily_forecasts.append(DailyForecastItem(
            date=target_date.isoformat(),
            expected_inflow=round(float(day_inflow), 2),
            expected_outflow=round(float(day_outflow), 2),
            expected_net=round(float(day_net), 2),
            lower_bound=lower,
            upper_bound=upper,
            confidence=round(overall_confidence * (1.0 - (i * 0.015)), 2)
        ))

    forecast_end_date = forecast_start_date + datetime.timedelta(days=horizon_days - 1)

    historical_summary = HistoricalSummary(
        start_date=hist_data.start_date_str,
        end_date=hist_data.end_date_str,
        inflow=round(float(hist_data.total_inflow), 2),
        outflow=round(float(hist_data.total_outflow), 2),
        net=round(float(hist_data.total_net), 2)
    )

    forecast_summary = ForecastSummary(
        start_date=forecast_start_date.isoformat(),
        end_date=forecast_end_date.isoformat(),
        inflow=round(float(proj_total_inflow), 2),
        outflow=round(float(proj_total_outflow), 2),
        net=round(float(proj_total_net), 2)
    )

    uncertainty = UncertaintyMetrics(
        std_dev=round(std_dev_float, 2),
        margin_of_error=margin_of_error,
        confidence_interval_percent=95.0,
        method="Historical Net Cash Flow Standard Deviation (95% CI)"
    )

    import uuid
    forecast_id = f"FC-{uuid.uuid4().hex[:10].upper()}"

    risk_factors = list(set(recon_issues))
    if hist_data.missing_settlement_count > 0:
        risk_factors.append(f"{hist_data.missing_settlement_count} payment(s) without matching settlement records.")

    return CashForecastResult(
        forecast_id=forecast_id,
        as_of=as_of_date.isoformat(),
        lookback_days=lookback_days,
        horizon_days=horizon_days,
        scenario=scenario,
        historical=historical_summary,
        forecast=forecast_summary,
        daily_forecasts=daily_forecasts,
        confidence=overall_confidence,
        uncertainty=uncertainty,
        data_quality=data_quality_report,
        assumptions=assumptions,
        risk_factors=risk_factors,
        warnings=[]
    )


def _evaluate_reconciliation_risks(
    db: Session,
    as_of_date: datetime.date,
    lookback_days: int
) -> Tuple[List[str], int]:
    """Queries Phase 4 Reconciliation Engine to extract operational risk factors in historical window."""
    issues = []
    unresolved_count = 0
    start_date = as_of_date - datetime.timedelta(days=lookback_days - 1)

    # Evaluate cases in historical window
    orders = db.query(Order).all()
    for ord_obj in orders:
        if ord_obj.created_at.date() >= start_date and ord_obj.created_at.date() <= as_of_date:
            case_id = f"CASE-{ord_obj.order_id.replace('ORD-', '')}"
            res = reconcile_case(db, case_id)
            if res.status.value != "ERROR" and res.needs_investigation:
                unresolved_count += 1
                r_code = res.reason_code.value
                if r_code == "MISSING_SETTLEMENT":
                    issues.append("MISSING_SETTLEMENT: Expected settlement cash payouts delayed.")
                elif r_code == "TIMING_DIFFERENCE":
                    issues.append("TIMING_DIFFERENCE: Settlement payout timing variance.")
                elif r_code == "DUPLICATE_TRANSACTION":
                    issues.append("DUPLICATE_TRANSACTION: Potential duplicate payment inflow.")
                elif r_code == "AMOUNT_MISMATCH":
                    issues.append("AMOUNT_MISMATCH: Discrepancy in recorded operational amounts.")
                elif r_code == "TAX_MISMATCH":
                    issues.append("TAX_MISMATCH: Invoice vs ledger tax liability variance.")

    return (issues, unresolved_count)
