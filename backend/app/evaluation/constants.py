from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
DEV_DATASET_DIR = PROJECT_ROOT / "data" / "output"
EVAL_DATASET_ROOT = PROJECT_ROOT / "data" / "evaluation"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

ALL_ANOMALY_CLASSES = [
    "EXACT_MATCH",
    "PARTIAL_REFUND",
    "FEE_DIFFERENCE",
    "TIMING_DIFFERENCE",
    "MISSING_SETTLEMENT",
    "DUPLICATE_TRANSACTION",
    "AMOUNT_MISMATCH",
    "TAX_MISMATCH",
    "UNKNOWN_ADJUSTMENT",
    "CONFLICTING_RECORDS",
    "AMBIGUOUS_CASE",
]

ALL_STATUS_CLASSES = [
    "MATCHED",
    "MISMATCH",
    "MISSING",
    "DUPLICATE",
    "AMBIGUOUS",
    "ERROR",
]

# Ground truth CSV stores reason codes, not operational statuses.
# Expected status is derived from engine semantics (not from production predictions).
EXPECTED_STATUS_BY_REASON = {
    "EXACT_MATCH": "MATCHED",
    "PARTIAL_REFUND": "MATCHED",
    "FEE_DIFFERENCE": "MISMATCH",
    "TIMING_DIFFERENCE": "MATCHED",
    "MISSING_SETTLEMENT": "MISSING",
    "DUPLICATE_TRANSACTION": "DUPLICATE",
    "AMOUNT_MISMATCH": "MISMATCH",
    "TAX_MISMATCH": "MISMATCH",
    "UNKNOWN_ADJUSTMENT": "MISMATCH",
    "CONFLICTING_RECORDS": "MISMATCH",
    "AMBIGUOUS_CASE": "AMBIGUOUS",
}

DEFAULT_SEEDS = [42, 123, 7, 21, 99]
EXTENDED_SEEDS = [314, 2026, 999]
ALL_BENCHMARK_SEEDS = DEFAULT_SEEDS + EXTENDED_SEEDS

TARGET_ACCURACY = 90.0
ZERO_DIVISION_VALUE = 0.0

# Dedicated PostgreSQL schema so benchmarks never mutate the development `public` schema.
EVAL_SCHEMA = "finctrl_eval"

OPERATIONAL_CSV_FILES = [
    "customers.csv",
    "orders.csv",
    "payments.csv",
    "refunds.csv",
    "settlements.csv",
    "bank_transactions.csv",
    "invoices.csv",
    "tax_records.csv",
]

GROUND_TRUTH_FILENAME = "ground_truth.csv"

PRODUCTION_PACKAGES = (
    "app.reconciliation",
    "app.services",
    "app.api",
    "app.models",
    "app.core",
    "app.main",
)
