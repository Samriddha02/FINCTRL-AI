# Phase 10 — Cash Forecasting Architecture

## Overview
Phase 10 introduces a transparent, deterministic, and auditable Cash Forecasting Engine for FINCTRL AI. It extracts actual operational cash-flow behavior from database records, applies deterministic baseline calculations and risk adjustments, calculates uncertainty bounds and data quality metrics, and produces grounded natural-language explanations.

```
Operational Financial Data (Settlements, Payments, Refunds)
                     │
                     ▼
       Historical Cash-Flow Extraction
  ├── Configurable lookback_days (default: 30 days)
  └── Strict as_of Date Boundary (Eliminates Look-Ahead Bias)
                     │
                     ▼
  Reconciliation-Aware Data Quality & Risk Engine
  ├── Consumes Phase 4 Reconciliation Discrepancies
  └── Calculates Data Quality Score (0.0 to 1.0) & Risk Factors
                     │
                     ▼
     Deterministic Forecast Engine
  ├── Computes Baseline Daily Inflows, Outflows & Net Cash (Decimal)
  ├── Applies Scenarios (BASELINE, CONSERVATIVE, OPTIMISTIC)
  └── Calculates Uncertainty Interval (95% CI bounds based on Std Dev)
                     │
                     ▼
     Explanation & Validation Layer
  ├── Formats Grounded Explanation (LLMProvider / MockLLMProvider)
  └── Validates Numeric Claims (validate_forecast_explanation)
                     │
                     ▼
         Audit Trail Event Logging
  └── CASH_FORECAST_GENERATED event
```

## 1. Cash-Flow Definitions
* **Cash Inflows**: Settlement `net_amount` payouts (when settled) or fallback payment `amount` when settlement records are missing.
* **Cash Outflows**: Processed refund amounts (`refund_amount`) + gateway fees and tax charges (`fee_amount` + `tax_amount`).
* **Net Cash**: `Decimal(inflow) - Decimal(outflow)`.

## 2. Historical Lookback & Forecast Horizon
* **Historical Lookback**: Configurable `lookback_days` (default: 30 days, min: 3, max: 365).
* **Forecast Horizon**: Configurable `horizon_days` (default: 7 days, min: 1, max: 90).
* **Cutoff Boundary (`as_of`)**: Only operational records with timestamp/date `<= as_of_date` are included in historical statistics. No future records are used for baseline estimation.

## 3. Forecasting Method & Scenarios
* **Baseline Calculation**: Evaluates mean daily cash inflows, outflows, and net cash flows over the lookback window using Python `Decimal` precision.
* **Scenarios**:
  - `BASELINE`: Historical daily trend continuation.
  - `CONSERVATIVE`: 10% discount on projected inflows, 10% buffer on projected outflows.
  - `OPTIMISTIC`: 10% premium on projected inflows, 5% reduction on projected outflows.

## 4. Uncertainty & Confidence Scoring
* **Uncertainty**: Standard deviation (`std_dev`) and margin of error (`1.96 * std_dev`) calculated over historical daily net cash flows. Each daily projected item includes explicit `lower_bound` and `upper_bound`.
* **Confidence**: Deterministic confidence score incorporating historical sample size, volatility ratio, data quality score, and active reconciliation risk factors.

## 5. Reconciliation Integration & Data Quality
* Queries Phase 4 Reconciliation Engine to detect active operational discrepancy types (`MISSING_SETTLEMENT`, `TIMING_DIFFERENCE`, `DUPLICATE_TRANSACTION`, `AMOUNT_MISMATCH`, `TAX_MISMATCH`).
* Discrepancies generate risk factors and lower the deterministic `DataQualityReport` score.

## 6. API & Audit Integration
* `GET /api/forecast/cash`: Generates cash forecast snapshot based on query parameters (`as_of`, `horizon_days`, `lookback_days`, `scenario`).
* `GET /api/forecast/cash/{forecast_id}`: Retrieves persistent in-memory forecast snapshot.
* Audit events: `CASH_FORECAST_REQUESTED`, `CASH_FORECAST_GENERATED`, `CASH_FORECAST_VALIDATION_FAILED`.
