# Phase 8 — Human Review, Resolution & Audit Architecture

## Overview
Phase 8 introduces human oversight, deterministic policy decision-making, post-action verification, and an immutable audit trail to FINCTRL AI. It ensures that AI investigations do not perform autonomous financial modifications without explicit policy checks, human authorization, and complete auditability.

```
Reconciliation Engine (Phase 4)
         │
         ▼
AI Investigation Controller (Phase 6)
         │
         ▼
Deterministic Policy Engine (Phase 8)
  ├── Confidence Policy (HIGH: >=0.85, MED: >=0.70)
  ├── Risk Policy (Amount > 5000.0, High-risk Reason Codes)
  └── Allowed Action Policy (Workflow actions only)
         │
         ├───────────────────────┬────────────────────────┐
         ▼                       ▼                        ▼
  Auto-Resolution Eligible  Human Review Required    Escalation Required
  (Exact Match / Low Risk)   (Pending/In-Review)    (Low Confidence/High Risk)
                                 │
                                 ▼
                         Human Decision
                      (Approve / Reject / More Info)
                                 │
                                 ▼
                         System Execution
                   (Safe Workflow Action Only)
                                 │
                                 ▼
                    Post-Action Verification
                    (verify_resolution)
                                 │
                                 ▼
                     Immutable Audit Trail
                    (audit_events table)
```

## 1. Deterministic Confidence & Risk Policy
Policy evaluations are 100% deterministic (never delegated to LLM decision-making).

### Key Thresholds
* `HIGH_CONFIDENCE_THRESHOLD`: `0.85`
* `MEDIUM_CONFIDENCE_THRESHOLD`: `0.70`
* `HIGH_RISK_AMOUNT_THRESHOLD`: `5000.0`

### Risk & Policy Mapping
* **AUTO_RESOLUTION_ELIGIBLE**: Assigned when `EXACT_MATCH` or high confidence (`>=0.85`) with low risk and zero tool errors.
* **HUMAN_REVIEW_REQUIRED**: Assigned for medium confidence (`0.70 - 0.85`) or high-risk reason codes (`TAX_MISMATCH`, `CONFLICTING_RECORDS`, `AMBIGUOUS_CASE`, `DUPLICATE_TRANSACTION`, `MISSING_SETTLEMENT`, `UNKNOWN_ADJUSTMENT`).
* **ESCALATION_REQUIRED**: Assigned for low confidence (`<0.70`), failed evidence collection, or critical risk errors.
* **NO_ACTION_ALLOWED**: Assigned when invalid inputs or unhandled system exceptions occur.

## 2. Action Policy & Read-Only Safety
FINCTRL AI operates under a **Safe Read-Only Workflow Model**.
* **Allowed Workflow Actions**: `NO_ACTION`, `REQUEST_HUMAN_REVIEW`, `REQUEST_MORE_INVESTIGATION`, `APPROVE_RECOMMENDATION`, `REJECT_RECOMMENDATION`, `VERIFY_RESOLUTION`.
* **Blocked Financial Writes**: `MOVE_MONEY`, `ISSUE_REFUND`, `MODIFY_SETTLEMENT`, `MODIFY_INVOICE`, `MODIFY_TAX_RECORD`, `MODIFY_PAYMENT`, `ALTER_BANK_TRANSACTION`.
* Any recommendation suggesting financial mutation is approved strictly as a workflow decision with `execution_status = "NOT_EXECUTED"` and a clear audit reason.

## 3. Human Review Workflow & State Machine
Human review records are stored persistently in the `human_reviews` table.

### Valid State Transitions
* `PENDING` ➔ `IN_REVIEW`, `APPROVED`, `REJECTED`, `MORE_INVESTIGATION_REQUIRED`, `ESCALATED`
* `IN_REVIEW` ➔ `APPROVED`, `REJECTED`, `MORE_INVESTIGATION_REQUIRED`, `ESCALATED`
* `MORE_INVESTIGATION_REQUIRED` ➔ `PENDING`, `IN_REVIEW`
* `APPROVED` ➔ `COMPLETED`
* `REJECTED` ➔ (Terminal state)
* `COMPLETED` ➔ (Terminal state)

Invalid transitions (e.g. `COMPLETED` ➔ `APPROVED`, `REJECTED` ➔ `APPROVED`) are rejected with `HTTP 400 Bad Request`.

## 4. Post-Action Verification
After a human decision is approved:
1. `verify_resolution` re-evaluates the deterministic reconciliation engine for the target case.
2. Assesses whether post-resolution workflow conditions are satisfied.
3. Assigns outcome `VERIFIED` or `VERIFICATION_FAILED`.
4. Emits `ACTION_VERIFIED` or `VERIFICATION_FAILED` audit events.

## 5. Immutable Audit Trail
All state transitions, tool invocations, policy evaluations, and human decisions emit append-only events to the `audit_events` database table.
* **Event Types**: `CASE_CREATED`, `RECONCILIATION_COMPLETED`, `INVESTIGATION_STARTED`, `INVESTIGATION_COMPLETED`, `INVESTIGATION_ESCALATED`, `TOOL_EXECUTED`, `EVIDENCE_RETRIEVED`, `RECOMMENDATION_CREATED`, `POLICY_EVALUATED`, `HUMAN_REVIEW_CREATED`, `HUMAN_REVIEW_STARTED`, `HUMAN_APPROVED`, `HUMAN_REJECTED`, `MORE_INVESTIGATION_REQUESTED`, `ACTION_REQUESTED`, `ACTION_EXECUTED`, `ACTION_NOT_EXECUTED`, `ACTION_VERIFIED`, `VERIFICATION_FAILED`, `CASE_ESCALATED`, `CASE_COMPLETED`.
* **Immutability Guarantee**: No `UPDATE` or `DELETE` endpoints are exposed via normal application APIs. Any correction generates a new event.

## 6. Ground-Truth & Security Guarantees
* **Ground Truth Isolation**: Phase 8 modules do not import or access `ground_truth.csv`.
* **Security Validation**: All `case_id`, `review_id`, and tool parameters are validated via `validate_id` to block SQL injection and path traversal attempts.
