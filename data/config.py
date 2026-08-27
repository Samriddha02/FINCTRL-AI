from decimal import Decimal
from pathlib import Path

# Random Seed for Reproducibility
SEED = 42

# Dataset Scale
NUM_CASES = 100
NUM_CUSTOMERS = 80

# Currency & Financial Defaults
CURRENCY = "INR"
DEFAULT_TAX_RATE = Decimal("0.18")  # 18% GST
DEFAULT_GATEWAY_FEE_RATE = Decimal("0.02")  # 2.0% gateway fee

# Date Range for Timestamps
START_DATE = "2026-01-01"
END_DATE = "2026-08-15"

# Anomaly Distribution for 100 cases (proportional scaling used for other case counts)
ANOMALY_DISTRIBUTION = {
    "EXACT_MATCH": 35,
    "PARTIAL_REFUND": 10,
    "FEE_DIFFERENCE": 10,
    "TIMING_DIFFERENCE": 8,
    "MISSING_SETTLEMENT": 8,
    "DUPLICATE_TRANSACTION": 7,
    "AMOUNT_MISMATCH": 7,
    "TAX_MISMATCH": 5,
    "UNKNOWN_ADJUSTMENT": 4,
    "CONFLICTING_RECORDS": 3,
    "AMBIGUOUS_CASE": 3,
}

# File Paths
DATA_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DATA_DIR / "output"
LOGS_DIR = DATA_DIR / "logs"

OUTPUT_FILES = {
    "customers": OUTPUT_DIR / "customers.csv",
    "orders": OUTPUT_DIR / "orders.csv",
    "payments": OUTPUT_DIR / "payments.csv",
    "refunds": OUTPUT_DIR / "refunds.csv",
    "settlements": OUTPUT_DIR / "settlements.csv",
    "bank_transactions": OUTPUT_DIR / "bank_transactions.csv",
    "invoices": OUTPUT_DIR / "invoices.csv",
    "tax_records": OUTPUT_DIR / "tax_records.csv",
    "ground_truth": OUTPUT_DIR / "ground_truth.csv",
}

LOG_FILE = LOGS_DIR / "generation.log"
