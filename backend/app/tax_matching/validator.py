import re
import logging
from typing import List, Tuple
from app.tax_matching.schemas import TaxMatchResult

logger = logging.getLogger("tax_validator")

NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
ID_PATTERN = re.compile(r"\b(CUST|ORD|PAY|REF|SETTL|BTXN|BANK|INV|TAX|CASE|REV|AUD|TM)-\d+\b", re.IGNORECASE)


def validate_tax_explanation(explanation: str, match_result: TaxMatchResult) -> Tuple[bool, List[str]]:
    """Deterministically validates that numeric claims and IDs in the explanation match authoritative tax facts."""
    errors = []
    if not explanation or not explanation.strip():
        return (True, [])

    # Gather valid numbers and IDs
    valid_numbers = set()
    valid_ids = {match_result.invoice_id.upper()}
    if match_result.tax_id:
        valid_ids.add(match_result.tax_id.upper())

    for val in [
        match_result.invoice_taxable_amount, match_result.ledger_taxable_amount,
        match_result.invoice_tax_amount, match_result.ledger_tax_amount,
        match_result.invoice_tax_rate, match_result.ledger_tax_rate,
        match_result.expected_tax_amount, match_result.difference,
        match_result.confidence
    ]:
        if val is not None:
            try:
                num = float(val)
                abs_num = abs(num)
                valid_numbers.add(round(num, 2))
                valid_numbers.add(round(abs_num, 2))
                valid_numbers.add(int(abs_num))
            except (ValueError, TypeError):
                pass

    # Check IDs
    found_ids = [m.group(0).upper() for m in ID_PATTERN.finditer(explanation)]
    for fid in found_ids:
        if valid_ids and fid not in valid_ids and not fid.startswith("TM-"):
            errors.append(f"Tax Grounding Error: Explanation mentions unverified ID '{fid}'.")

    # Check Numbers
    found_numbers = NUMERIC_PATTERN.findall(explanation)
    for num_str in found_numbers:
        try:
            num_val = float(num_str)
            if num_val in (0, 1, 2, 3) and "." not in num_str:
                continue

            rounded_val = round(num_val, 2)
            int_val = int(num_val)

            is_valid = False
            for vn in valid_numbers:
                if abs(vn - num_val) < 0.05 or vn == rounded_val or vn == int_val:
                    is_valid = True
                    break

            if valid_numbers and not is_valid:
                errors.append(f"Tax Fact Integrity Error: Explanation claims numeric value '{num_str}' not matching authoritative tax facts.")
        except ValueError:
            pass

    return (len(errors) == 0, errors)
