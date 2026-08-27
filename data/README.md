# Synthetic Financial Dataset Generator

## Purpose
This package generates realistic, reproducible synthetic financial datasets for FINCTRL AI. It simulates multi-system financial records (orders, gateway payments, refunds, settlements, bank statements, invoices, tax ledgers) with controlled financial anomalies to test and evaluate AI reconciliation and investigation capabilities.

> **CRITICAL ARCHITECTURAL REQUIREMENT:**
> `ground_truth.csv` is evaluation-only metadata and must **NEVER** be provided to the AI/agent or API endpoints during evaluation or runtime.

---

## Dataset Entities

1. **Customers (`customers.csv`)**: Synthetic customer demographics (B2B companies & B2C individuals).
2. **Orders (`orders.csv`)**: E-commerce / POS order records with amounts in INR (₹).
3. **Payments (`payments.csv`)**: Payment gateway transaction records (UPI, Cards, Net Banking, Razorpay).
4. **Refunds (`refunds.csv`)**: Partial and full refund transaction records.
5. **Settlements (`settlements.csv`)**: Gateway payout settlements detailing gross amount, fees, gateway taxes, adjustments, and net payout.
6. **Bank Transactions (`bank_transactions.csv`)**: Bank statement credit records with realistic posting delays and batch reference IDs.
7. **Invoices (`invoices.csv`)**: Sales tax invoices breaking down subtotal, tax rate (GST 18%), and total amount.
8. **Tax Records (`tax_records.csv`)**: Tax ledger compliance entries filed for tax authority reconciliation.
9. **Ground Truth (`ground_truth.csv`)**: Hidden benchmark ground-truth metadata detailing root cause explanations, expected values, actual values, and auto-resolution flags.

---

## Anomaly Types (11 Total)

- `EXACT_MATCH`: Perfect alignment across all 8 entity ledgers (Expected: MATCHED).
- `PARTIAL_REFUND`: Partial refund issued and accounted for in settlement net (Expected: PARTIAL_REFUND).
- `FEE_DIFFERENCE`: Gateway fee charged at 3.5% instead of contracted 2.0% (Expected: FEE_DIFFERENCE).
- `TIMING_DIFFERENCE`: Bank credit posted 15 days late outside standard T+2 window (Expected: TIMING_DIFFERENCE).
- `MISSING_SETTLEMENT`: Gateway captured payment but omitted settlement entry (Expected: MISSING_SETTLEMENT).
- `DUPLICATE_TRANSACTION`: Duplicate bank credit entry posted for single settlement (Expected: DUPLICATE_TRANSACTION).
- `AMOUNT_MISMATCH`: Settlement gross is lower than captured payment (Expected: AMOUNT_MISMATCH).
- `TAX_MISMATCH`: Tax record amount disagrees with invoice tax calculation (Expected: TAX_MISMATCH).
- `UNKNOWN_ADJUSTMENT`: Unexplained negative/positive gateway adjustment code (Expected: UNKNOWN_ADJUSTMENT).
- `CONFLICTING_RECORDS`: Order status `CANCELLED` but payment captured & settled (Expected: CONFLICTING_RECORDS).
- `AMBIGUOUS_CASE`: Vague transaction reference matching multiple candidate orders (Expected: AMBIGUOUS_CASE).

---

## Running the Generator

Execute the generator from the project root:

```bash
python data/generator.py
```

### Reproducibility
The generator uses a deterministic seed (`SEED = 42` by default). Re-running the command with the same seed guarantees byte-for-byte identical CSV output.

### Scaling the Dataset
To change the scale of generated cases (e.g., scale from 100 cases to 1,000 cases), modify `NUM_CASES` in `data/config.py`:

```python
NUM_CASES = 1000
```
Or pass arguments dynamically in code:

```python
from data.generator import FinancialDataGenerator

generator = FinancialDataGenerator(seed=42, num_cases=1000)
generator.generate_all()
```

---

## Dataset Validation

The generator automatically validates relational integrity, non-negative amounts, monetary arithmetic, ground truth coverage, and anomaly distribution using `data/validators.py`. 

Validation failures raise explicit `ValueError` exceptions and halt generation.
