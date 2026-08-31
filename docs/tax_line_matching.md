# Phase 11 — Tax-Line Matching Architecture

## Overview
Phase 11 introduces a deterministic, auditable Tax-Line Matching (Tax Control) engine for FINCTRL AI. It compares tax-related financial records across existing Invoice and TaxRecord operational entities to identify exact matches, discrepancies, missing records, and duplicate entries.

```
Invoice (subtotal, tax_rate, tax_amount)
            │
            ▼
  Phase 11 Tax Line Matcher
  ├── Fetch linked TaxRecord(s)
  ├── Precedence-based Deterministic Rules (no LLM)
  └── Structured TaxMatchResult
            │
            ▼
 Optional LLM Explanation → Validation → Fallback
            │
            ▼
  Phase 8 Human Review (if mismatch)
  Phase 8 Audit Events
  API Response
```

## 1. Tax Entities Used
- **Invoice**: `invoice_id`, `subtotal` (taxable amount), `tax_rate`, `tax_amount`, `total_amount`, `invoice_status`, `invoice_date`
- **TaxRecord**: `tax_id`, `invoice_id`, `tax_type`, `taxable_amount`, `tax_rate`, `tax_amount`, `filing_period`, `recorded_at`

No new database tables are created. Phase 3 models are reused exclusively.

## 2. Tax Rate Normalization
Database stores rates in decimal fraction form (`0.18` for 18%). The `normalize_tax_rate()` function in `matcher.py` handles both representations:
- If `rate > 1.0`: divides by 100 (`18.0 → 0.18`, `12 → 0.12`)
- If `rate <= 1.0`: used as-is (`0.18 → 0.18`)

## 3. Tolerances
- `TAX_AMOUNT_TOLERANCE = Decimal("0.01")` — Absolute tolerance for monetary amount comparison (INR 0.01)
- `TAX_RATE_TOLERANCE = Decimal("0.0001")` — Absolute tolerance for rate comparison (0.01%)

## 4. Matching Rules (in precedence order)
1. **MISSING_TAX_RECORD**: No TaxRecord linked to the Invoice → `MISSING_TAX_RECORD`
2. **DUPLICATE_TAX_RECORD**: More than one TaxRecord linked → `DUPLICATE_TAX_RECORD`
3. **CALCULATION_MISMATCH**: `abs(tr.tax_amount - (tr.taxable_amount × tr.tax_rate)) > 0.01` → `CALCULATION_MISMATCH`
4. **TAXABLE_AMOUNT_MISMATCH**: `abs(invoice.subtotal - tr.taxable_amount) > 0.01` → `TAXABLE_AMOUNT_MISMATCH`
5. **RATE_MISMATCH**: `abs(normalized_invoice_rate - normalized_tr_rate) > 0.0001` → `RATE_MISMATCH`
6. **AMOUNT_MISMATCH**: `abs(invoice.tax_amount - tr.tax_amount) > 0.01` → `AMOUNT_MISMATCH`
7. **EXACT_MATCH**: All rules pass → `EXACT_MATCH`

## 5. Confidence Semantics
Deterministic certainty scores — NOT probabilistic:
- `1.00`: Complete linked records, all rules pass (EXACT_MATCH or MISSING_TAX_RECORD)
- `0.95`: Single tax amount discrepancy within tolerance
- `0.90`: Rate or taxable amount mismatch
- `0.85`: Internal tax calculation mismatch
- `0.50`: Duplicate tax record ambiguity

## 6. Evidence
Each result contains authoritative evidence items from operational database records. Example:
```json
{"source": "Invoice", "entity_id": "INV-00001", "field": "tax_amount", "value": "18305.17"}
{"source": "TaxRecord", "entity_id": "TAX-00001", "field": "tax_amount", "value": "12203.45"}
```

## 7. Rule Evaluations
Structured rule evaluation logs document each deterministic check:
- `CHECK_TAX_RECORD_EXISTS`
- `CHECK_SINGLE_TAX_RECORD`
- `CHECK_TAX_CALCULATION_ACCURACY`
- `CHECK_TAXABLE_AMOUNT_MATCH`
- `CHECK_TAX_RATE_MATCH`
- `CHECK_TAX_AMOUNT_MATCH`

## 8. Human Review Integration
Mismatched tax lines automatically trigger Phase 8 Human Review records. Statuses triggering review:
- `AMOUNT_MISMATCH`, `RATE_MISMATCH`, `TAXABLE_AMOUNT_MISMATCH`, `CALCULATION_MISMATCH`, `MISSING_TAX_RECORD`, `DUPLICATE_TAX_RECORD`

## 9. Audit Events
- `TAX_MATCH_REQUESTED`: Logged at start of each match
- `TAX_MATCH_COMPLETED`: Logged on successful match with `match_id`, `invoice_id`, `status`, `reason_code`, `difference`
- `TAX_REVIEW_CREATED`: Logged when Phase 8 Human Review is triggered

## 10. API
- `GET /api/tax-matching/{invoice_id}`: Single invoice tax match
- `GET /api/tax-matching`: Batch match across all invoices
- `GET /api/tax-matching/results/{match_id}`: Retrieve previous match result by ID

## 11. Finance Q&A Integration
Tax-related Q&A questions (e.g., "What tax was recorded for INV-00001?", "Does INV-00001 match the tax ledger?") are routed through Phase 9's retriever which now delegates to `TaxMatchController` for authoritative match status and difference facts.

## 12. Security & Ground-Truth Isolation
- ORM parameterization only — no raw SQL
- `validate_id()` enforced on all invoice/tax IDs
- Zero imports of `ground_truth.csv` in production Phase 11 code
- Read-only financial access — no mutations to Invoice, TaxRecord, or any financial table

## 13. Limitations
- In-memory match registry (`tax_matches_by_id`) resets on process restart. Audit events remain persistent in database.
- Batch endpoint fetches all invoices without pagination (acceptable for current scale).
