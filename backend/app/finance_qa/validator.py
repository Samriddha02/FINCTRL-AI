import re
import logging
from typing import List, Dict, Any, Tuple
from app.finance_qa.schemas import QAFactRecord, QACalculation, QAStatus

logger = logging.getLogger("qa_validator")

# Regex to detect numeric values in answer text (integers and decimals)
NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")

# Regex to detect FINCTRL ID patterns
ID_PATTERN = re.compile(r"\b(CUST|ORD|PAY|REF|SETTL|BTXN|BANK|INV|TAX|CASE|REV|AUD)-\d+\b", re.IGNORECASE)

# Regex to detect ISO date strings (e.g., 2026-08-31)
ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?\b")


def validate_qa_answer(
    answer: str,
    facts: List[QAFactRecord],
    calculations: List[QACalculation]
) -> Tuple[bool, List[str]]:
    """Deterministically validates that numeric claims and IDs in the generated answer match facts."""
    errors: List[str] = []

    # Strip ISO dates and IDs from text before inspecting numbers to avoid false alerts on ID digits or dates
    answer_sans_dates = ISO_DATE_PATTERN.sub("", answer)
    answer_sans_ids_and_dates = ID_PATTERN.sub("", answer_sans_dates)

    # 1. Build set of grounded valid numbers and valid IDs
    valid_numbers = set()
    valid_ids = set()

    for f in facts:
        val = f.value
        if val is not None:
            val_str = str(val).upper()
            if ID_PATTERN.match(val_str):
                valid_ids.add(val_str)
            try:
                num_val = float(val)
                abs_val = abs(num_val)
                valid_numbers.add(round(num_val, 2))
                valid_numbers.add(round(abs_val, 2))
                valid_numbers.add(int(abs_val))
            except (ValueError, TypeError):
                pass

    for c in calculations:
        val = c.value
        if val is not None:
            try:
                num_val = float(val)
                abs_val = abs(num_val)
                valid_numbers.add(round(num_val, 2))
                valid_numbers.add(round(abs_val, 2))
                valid_numbers.add(int(abs_val))
            except (ValueError, TypeError):
                pass

    # 2. Validate IDs in LLM answer
    found_full_ids = [m.group(0).upper() for m in ID_PATTERN.finditer(answer)]
    for fid in found_full_ids:
        if valid_ids and fid not in valid_ids:
            errors.append(f"Grounding error: Answer mentions unverified ID '{fid}' not present in database facts.")

    # 3. Validate numeric claims in LLM answer
    found_numbers = NUMERIC_PATTERN.findall(answer_sans_ids_and_dates)
    for num_str in found_numbers:
        try:
            num_val = float(num_str)
            
            # Ignore small index numbers (0, 1, 2, 3) or 4-digit year numbers (2020..2035)
            if (num_val in (0, 1, 2, 3) and "." not in num_str) or (2020 <= num_val <= 2035 and "." not in num_str):
                continue
            
            rounded_val = round(num_val, 2)
            int_val = int(num_val)

            is_valid = False
            for vn in valid_numbers:
                if abs(vn - num_val) < 0.05 or vn == rounded_val or vn == int_val:
                    is_valid = True
                    break

            if valid_numbers and not is_valid:
                errors.append(f"Fact integrity failure: Answer claims numeric value '{num_str}' not matching authoritative facts.")
        except ValueError:
            pass

    return (len(errors) == 0, errors)


def sanitize_untrusted_text(text: str) -> str:
    """Sanitizes text retrieved from untrusted database fields to prevent prompt injection."""
    if not text:
        return ""
    cleaned = text.replace("```", "").replace("<system>", "").replace("</system>", "")
    return cleaned
