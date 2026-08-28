# FINCTRL AI Deterministic Reconciliation Engine

## 1. Purpose
The Deterministic Reconciliation Engine processes raw operational financial records (orders, gateway payments, refunds, gateway settlements, bank statements, invoices, and tax ledgers) into structured reconciliation results. 

It establishes objective financial facts without probabilistic AI models or non-deterministic assumptions, serving as the foundational facts layer for future AI investigation agents.

---

## 2. Architecture & Pipeline

```
+------------------------------------+
|        PostgreSQL Database         |
|   (finctrl / 8 Operational Tables) |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|       Database Service Layer       |
| (app.services.database_service)    |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
| Deterministic Reconciliation Engine|
|   (app.reconciliation.engine)      |
+------------------------------------+
                  │
                  ▼
+------------------------------------+
|    Structured Result & Evidence    |
|   (ReconciliationResult Pydantic)  |
+------------------------------------+
                  │
                  ▼ [NOT IMPLEMENTED YET]
+------------------------------------+
|       Future AI Investigator       |
|    (LLM Root Cause & Q&A Agent)    |
+------------------------------------+
```

---

## 3. Core Engine Components

- **`constants.py`**: Centralized financial tolerances (`AMOUNT_TOLERANCE = 0.01 INR`, `TIMING_TOLERANCE_DAYS = 3`), fee policy rates (`EXPECTED_FEE_RATE = 0.02`), tax rates (`DEFAULT_TAX_RATE = 0.18`), and currency quantization functions (`Decimal("0.01")`).
- **`models.py`**: Strongly-typed `ReconciliationStatus` enum (`MATCHED`, `MISMATCH`, `MISSING`, `DUPLICATE`, `AMBIGUOUS`, `ERROR`), `ReasonCode` enum, `EvidenceItem`, `RuleEvaluation`, and `ReconciliationResult`.
- **`calculators.py`**: Pure `Decimal` financial arithmetic functions for expected net settlement, gateway fee/tax, invoice subtotal breakdown, and refund summation.
- **`matchers.py`**: Reference ID and date proximity matching for bank statement entries.
- **`rules.py`**: Implementation of the 11 deterministic rule evaluations and precedence hierarchy.
- **`evidence.py`**: Collector for structured evidence bundles and audit rule evaluations.
- **`engine.py`**: Single-case and batch case reconciliation orchestrator.

---

## 4. Financial Formulas & Tolerances

### Amount Tolerance
- **`AMOUNT_TOLERANCE = Decimal("0.01")`**
- Two monetary values are considered equal if `abs(expected - actual) <= AMOUNT_TOLERANCE`.

### Timing Tolerance
- **`TIMING_TOLERANCE_DAYS = 3`**
- Posting delay between `settlement_date` and `bank_transaction_date` within 3 days is considered normal T+2 settlement timing.

### Net Settlement Formula
$$\text{Expected Net} = \text{Payment Amount} - \text{Total Refunds} - \text{Gateway Fee} - \text{Tax on Fee} + \text{Adjustment Amount}$$

### Expected Gateway Fee & Tax
$$\text{Expected Fee} = \text{round\_currency}(\text{Gross Amount} \times 0.02)$$
$$\text{Expected Tax} = \text{round\_currency}(\text{Expected Fee} \times 0.18)$$

---

## 5. Rule Priority Hierarchy

When multiple conditions exist, rules are evaluated in strict deterministic order:

1. **`CONFLICTING_RECORDS`**: Order status `CANCELLED` with captured/settled payment, or refund exceeding payment.
2. **`MISSING_SETTLEMENT`**: Captured payment exists but no settlement record.
3. **`DUPLICATE_TRANSACTION`**: Multiple bank transactions linked to single settlement.
4. **`AMBIGUOUS_CASE`**: Bank transaction reference is vague (`PG_BULK_TRANSFER_BATCH`).
5. **`AMOUNT_MISMATCH`**: Settlement gross amount != captured payment amount.
6. **`PARTIAL_REFUND`**: Valid refund processed, settlement net correctly reflects refund.
7. **`FEE_DIFFERENCE`**: Gateway fee charged != expected 2.0% rate.
8. **`TAX_MISMATCH`**: Invoice tax != filed tax record.
9. **`UNKNOWN_ADJUSTMENT`**: Non-zero settlement adjustment amount.
10. **`TIMING_DIFFERENCE`**: Bank transaction posting delayed > 3 days.
11. **`EXACT_MATCH`**: Perfect end-to-end alignment.

---

## 6. Confidence & Auto-Resolution Policy

| Reason Code | Status | Confidence | Needs Investigation | Auto-Resolvable |
| :--- | :--- | :---: | :---: | :---: |
| `EXACT_MATCH` | `MATCHED` | 1.00 | False | **True** |
| `TIMING_DIFFERENCE` | `MATCHED` | 1.00 | False | **True** |
| `PARTIAL_REFUND` | `MATCHED` | 1.00 | False | **True** |
| `FEE_DIFFERENCE` | `MISMATCH` | 0.95 | True | **False** |
| `MISSING_SETTLEMENT` | `MISSING` | 0.95 | True | **False** |
| `DUPLICATE_TRANSACTION` | `DUPLICATE` | 0.95 | True | **False** |
| `AMOUNT_MISMATCH` | `MISMATCH` | 0.95 | True | **False** |
| `TAX_MISMATCH` | `MISMATCH` | 0.95 | True | **False** |
| `UNKNOWN_ADJUSTMENT` | `MISMATCH` | 0.95 | True | **False** |
| `CONFLICTING_RECORDS` | `MISMATCH` | 0.95 | True | **False** |
| `AMBIGUOUS_CASE` | `AMBIGUOUS` | 0.70 | True | **False** |

---

## 7. Ground Truth Isolation & Benchmark Results

### Isolation Confirmation
Production reconciliation modules (`app.reconciliation.*`) do **NOT** import, read, or query `ground_truth.csv`.

`ground_truth.csv` is accessed strictly in evaluation benchmark scripts (`backend/scripts/benchmark_reconciliation.py`) and test suites (`tests/test_reconciliation.py`).

### Benchmark Results (100 Cases)
- **Target Accuracy**: $\ge 90\%$
- **Achieved Reason-Code Accuracy**: **100.00%** (100/100 cases correctly classified)
- **Generalization Accuracy (`SEED = 123`)**: **100.00%** (100/100 cases correctly classified)
