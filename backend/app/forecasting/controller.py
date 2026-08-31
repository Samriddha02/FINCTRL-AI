import datetime
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Payment, Settlement
from app.agents.providers import get_llm_provider, LLMProvider
from app.forecasting.schemas import CashForecastResult, Scenario
from app.forecasting.engine import run_cash_forecast
from app.forecasting.validator import validate_forecast_explanation
from app.services.audit_service import log_audit_event

logger = logging.getLogger("forecast_controller")

forecasts_by_id: Dict[str, CashForecastResult] = {}

SYSTEM_FORECAST_PROMPT = """
You are the FINCTRL Cash Forecasting Specialist.
Your job is to explain the deterministic cash-flow forecast concisely and accurately.

RULES:
1. Reference historical cash flows, projected inflows/outflows/net, confidence score, and risk factors accurately.
2. Never invent, alter, or calculate forecast numbers. Use only the provided forecast facts.
3. Keep the explanation professional, factual, and concise.
"""


class CashForecastController:
    """Orchestrates Cash Forecasting generation, LLM explanation, validation, and audit logging."""

    def __init__(self, db: Session, provider: Optional[LLMProvider] = None):
        self.db = db
        self.provider = provider or get_llm_provider()

    def generate_forecast(
        self,
        as_of_date: Optional[datetime.date] = None,
        lookback_days: int = 30,
        horizon_days: int = 7,
        scenario: Scenario = Scenario.BASELINE
    ) -> CashForecastResult:
        # Determine default as_of_date from latest operational database date if not provided
        if not as_of_date:
            as_of_date = self._get_latest_operational_date()

        # Audit event for request
        log_audit_event(
            db=self.db,
            case_id="FORECAST",
            event_type="CASH_FORECAST_REQUESTED",
            actor_type="SYSTEM",
            details={
                "as_of": as_of_date.isoformat(),
                "lookback_days": lookback_days,
                "horizon_days": horizon_days,
                "scenario": scenario.value
            }
        )

        # 1. Execute Deterministic Forecasting Engine
        forecast_res: CashForecastResult = run_cash_forecast(
            db=self.db,
            as_of_date=as_of_date,
            lookback_days=lookback_days,
            horizon_days=horizon_days,
            scenario=scenario
        )

        # 2. Generate LLM Explanation
        prompt = self._build_explanation_prompt(forecast_res)
        explanation_text = ""
        try:
            explanation_text = self.provider.generate_text(prompt=prompt, system_prompt=SYSTEM_FORECAST_PROMPT)
        except Exception as e:
            logger.warning(f"LLM explanation generation failed: {e}. Falling back to deterministic explanation.")
            explanation_text = self._build_deterministic_explanation(forecast_res)

        if "mock text response" in explanation_text.lower() or not explanation_text.strip():
            explanation_text = self._build_deterministic_explanation(forecast_res)

        # 3. Validate Explanation
        is_valid, errors = validate_forecast_explanation(explanation_text, forecast_res)
        if not is_valid:
            logger.warning(f"Forecast explanation failed validation: {errors}")
            forecast_res.warnings.extend(errors)
            explanation_text = self._build_deterministic_explanation(forecast_res)
            log_audit_event(
                db=self.db,
                case_id="FORECAST",
                event_type="CASH_FORECAST_VALIDATION_FAILED",
                actor_type="SYSTEM",
                details={"errors": errors},
                result="VALIDATION_FAILED"
            )

        forecast_res.explanation = explanation_text

        # 4. Save and Audit Log
        forecasts_by_id[forecast_res.forecast_id] = forecast_res

        log_audit_event(
            db=self.db,
            case_id="FORECAST",
            event_type="CASH_FORECAST_GENERATED",
            actor_type="SYSTEM",
            details={
                "forecast_id": forecast_res.forecast_id,
                "as_of": forecast_res.as_of,
                "horizon_days": forecast_res.horizon_days,
                "confidence": forecast_res.confidence,
                "forecast_net": forecast_res.forecast.net,
                "scenario": forecast_res.scenario.value
            },
            result="SUCCESS"
        )

        return forecast_res

    def _get_latest_operational_date(self) -> datetime.date:
        """Finds the maximum date recorded in operational payments/settlements."""
        max_pay_date = self.db.query(func.max(Payment.created_at)).scalar()
        max_settl_date = self.db.query(func.max(Settlement.settlement_date)).scalar()

        dates = []
        if max_pay_date:
            dates.append(max_pay_date.date())
        if max_settl_date:
            dates.append(max_settl_date)

        if dates:
            return max(dates)
        return datetime.date.today()

    def _build_explanation_prompt(self, res: CashForecastResult) -> str:
        return f"""
EXPLAIN THE FOLLOWING DETERMINISTIC CASH FORECAST:

Forecast ID: {res.forecast_id}
As Of Date: {res.as_of}
Scenario: {res.scenario.value}
Horizon Days: {res.horizon_days}

HISTORICAL CASH FLOWS ({res.historical.start_date} to {res.historical.end_date}):
Inflow: INR {res.historical.inflow}
Outflow: INR {res.historical.outflow}
Net: INR {res.historical.net}

PROJECTED FORECAST ({res.forecast.start_date} to {res.forecast.end_date}):
Projected Inflow: INR {res.forecast.inflow}
Projected Outflow: INR {res.forecast.outflow}
Projected Net Cash: INR {res.forecast.net}

CONFIDENCE & UNCERTAINTY:
Confidence Score: {res.confidence}
Daily Std Dev: INR {res.uncertainty.std_dev}
Data Quality Score: {res.data_quality.score}

RISK FACTORS & ISSUES:
{res.risk_factors}

Provide a concise 3-4 sentence explanation highlighting projected net cash, confidence level, key risk drivers, and assumptions.
"""

    def _build_deterministic_explanation(self, res: CashForecastResult) -> str:
        """Generates a facts-backed natural language explanation without using LLM generation."""
        scenario_str = res.scenario.value.lower()
        explanation = (
            f"Over the projected {res.horizon_days}-day horizon ({res.forecast.start_date} to {res.forecast.end_date}) under the {scenario_str} scenario, "
            f"expected cash inflow is INR {res.forecast.inflow:,.2f} against projected outflows of INR {res.forecast.outflow:,.2f}, yielding a net projected cash flow of INR {res.forecast.net:,.2f}. "
            f"Historical lookback over {res.lookback_days} days produced a baseline standard deviation of INR {res.uncertainty.std_dev:,.2f}. "
            f"Overall forecast confidence is rated at {int(res.confidence * 100)}% with a data quality score of {res.data_quality.score:.2f}."
        )
        if res.risk_factors:
            explanation += f" Primary risk factors include: {'; '.join(res.risk_factors[:2])}."
        return explanation
