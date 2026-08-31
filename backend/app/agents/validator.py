import logging
from typing import Dict, Any, List
from app.agents.schemas import InvestigationResult, FactRecord

logger = logging.getLogger("investigation_validator")

# Define reason codes that ALWAYS require human review
RISKY_REASON_CODES = {
    "PARTIAL_REFUND",
    "FEE_DIFFERENCE",
    "AMOUNT_MISMATCH",
    "MISSING_SETTLEMENT",
    "DUPLICATE_TRANSACTION",
    "TAX_MISMATCH",
    "UNKNOWN_ADJUSTMENT",
    "CONFLICTING_RECORDS",
    "AMBIGUOUS_CASE"
}

def validate_facts_and_safety(
    result: InvestigationResult,
    context: Dict[str, Any]
) -> List[str]:
    """Validates the LLM-generated facts, confidence, actions, and safety parameters.

    Returns a list of error strings. If empty, the result is valid.
    """
    errors: List[str] = []

    # 1. Check root cause confidence range
    if not (0.0 <= result.root_cause_confidence <= 1.0):
        errors.append(f"Invalid root_cause_confidence: {result.root_cause_confidence}. Must be [0.0, 1.0].")

    # 2. Check that objective numerical facts are consistent with deterministic values
    expected_amount = context.get("expected_amount")
    actual_amount = context.get("actual_amount")
    difference = context.get("difference")

    for fact in result.facts:
        key_lower = fact.key.lower()
        val = fact.value
        
        # Strip currency symbols if present or try to convert value to float
        try:
            float_val = float(val) if val is not None else None
        except (ValueError, TypeError):
            float_val = None

        if float_val is not None:
            if "payment" in key_lower or "expected" in key_lower:
                if expected_amount is not None and abs(float_val - expected_amount) > 0.01:
                    errors.append(f"Fact integrity mismatch: '{fact.key}' is {float_val} but deterministic value is {expected_amount}.")
            elif "settlement" in key_lower or "actual" in key_lower:
                if actual_amount is not None and abs(float_val - actual_amount) > 0.01:
                    errors.append(f"Fact integrity mismatch: '{fact.key}' is {float_val} but deterministic value is {actual_amount}.")
            elif "diff" in key_lower:
                if difference is not None and abs(float_val - difference) > 0.01:
                    errors.append(f"Fact integrity mismatch: '{fact.key}' is {float_val} but deterministic value is {difference}.")

    # 3. Verify claimed evidence IDs exist in supplied evidence
    evidence_records = context.get("evidence_records", [])
    valid_ids = set()
    for item in evidence_records:
        rec = item.get("record", {})
        if not rec:
            continue
        # Collect any potential IDs present in the evidence dictionaries
        for field in ["payment_id", "order_id", "refund_id", "settlement_id", "bank_transaction_id", "invoice_id", "tax_id"]:
            if field in rec and rec[field]:
                valid_ids.add(str(rec[field]).lower())

    # Validate facts/inferences do not reference fictitious IDs
    for fact in result.facts:
        val_str = str(fact.value).lower()
        # If value looks like an ID, check if it's in the valid set
        if any(prefix in val_str for prefix in ["pay-", "ord-", "set-", "inv-", "tax-", "bt-"]):
            if val_str not in valid_ids:
                errors.append(f"Grounding error: Fact mentions fictitious ID '{fact.value}' not present in evidence.")

    # 4. Check recommended actions structure and safety
    for action in result.recommended_actions:
        # All actions in Phase 6 MUST require human approval since agent is advisory
        if not action.requires_human_approval:
            errors.append(f"Action '{action.action}' must set requires_human_approval = True.")
        
        # Check if the description claims the action has already been executed
        desc_lower = action.action.lower()
        if any(past_phrase in desc_lower for past_phrase in ["refunded payment", "updated database", "executed transfer", "completed refund"]):
            errors.append(f"Safety Violation: Action description '{action.action}' claims execution. Recommendations must be advisory only.")

    # 5. Enforce human review requirement for risky cases
    reason_code = context.get("deterministic_reason_code")
    if reason_code in RISKY_REASON_CODES:
        if not result.requires_human_review:
            logger.warning(f"Overriding requires_human_review to True for risky reason_code: {reason_code}")
            result.requires_human_review = True

    return errors
