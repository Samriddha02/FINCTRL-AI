import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Scenario(str, Enum):
    BASELINE = "BASELINE"
    CONSERVATIVE = "CONSERVATIVE"
    OPTIMISTIC = "OPTIMISTIC"


class DailyForecastItem(BaseModel):
    date: str = Field(description="Target date in YYYY-MM-DD format")
    expected_inflow: float = Field(description="Projected cash inflow amount")
    expected_outflow: float = Field(description="Projected cash outflow amount")
    expected_net: float = Field(description="Projected net cash flow (inflow - outflow)")
    lower_bound: float = Field(description="Uncertainty interval lower bound for net cash")
    upper_bound: float = Field(description="Uncertainty interval upper bound for net cash")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Daily forecast confidence score")


class HistoricalSummary(BaseModel):
    start_date: str = Field(description="Start date of historical lookback window")
    end_date: str = Field(description="End date of historical lookback window")
    inflow: float = Field(description="Total actual cash inflow during lookback")
    outflow: float = Field(description="Total actual cash outflow during lookback")
    net: float = Field(description="Total actual net cash flow during lookback")


class ForecastSummary(BaseModel):
    start_date: str = Field(description="Start date of forecast horizon")
    end_date: str = Field(description="End date of forecast horizon")
    inflow: float = Field(description="Total projected cash inflow for horizon")
    outflow: float = Field(description="Total projected cash outflow for horizon")
    net: float = Field(description="Total projected net cash flow for horizon")


class UncertaintyMetrics(BaseModel):
    std_dev: float = Field(description="Historical daily net cash flow standard deviation")
    margin_of_error: float = Field(description="Margin of error applied to daily bounds")
    confidence_interval_percent: float = Field(default=95.0, description="Confidence interval percentage")
    method: str = Field(default="Historical Standard Deviation & MAD", description="Uncertainty calculation method")


class DataQualityReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Data quality score from 0.0 to 1.0")
    issues: List[str] = Field(default_factory=list, description="List of detected data quality issues")
    missing_settlement_count: int = Field(default=0, description="Number of missing settlement records")
    unresolved_reconciliation_count: int = Field(default=0, description="Number of unresolved reconciliation cases")


class CashForecastResult(BaseModel):
    forecast_id: str = Field(description="Unique forecast identifier (FC-...)")
    as_of: str = Field(description="Cutoff date for historical data (YYYY-MM-DD)")
    lookback_days: int = Field(default=30, description="Number of historical days evaluated")
    horizon_days: int = Field(default=7, description="Number of days projected forward")
    scenario: Scenario = Field(default=Scenario.BASELINE, description="Forecast scenario executed")
    historical: HistoricalSummary = Field(description="Summary of actual historical cash flows")
    forecast: ForecastSummary = Field(description="Summary of projected forecast cash flows")
    daily_forecasts: List[DailyForecastItem] = Field(default_factory=list, description="Daily projected cash flow items")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall forecast confidence score")
    uncertainty: UncertaintyMetrics = Field(description="Uncertainty metrics and error bounds")
    data_quality: DataQualityReport = Field(description="Data quality assessment and issues")
    assumptions: List[str] = Field(default_factory=list, description="Documented forecast assumptions")
    risk_factors: List[str] = Field(default_factory=list, description="Reconciliation and operational risk factors")
    warnings: List[str] = Field(default_factory=list, description="Warnings or execution notes")
    explanation: str = Field(default="", description="Natural-language explanation of the forecast")
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat(), description="ISO timestamp")
