from typing import List, Any, Optional
from datetime import date, datetime


def match_bank_transactions_for_settlement(
    settlement_id: str, bank_transactions: List[Any]
) -> List[Any]:
    """Finds bank transaction records linked to a settlement_id by reference_id."""
    if not settlement_id or not bank_transactions:
        return []
    return [b for b in bank_transactions if getattr(b, "reference_id", None) == settlement_id]


def check_posting_delay(settlement_date_val: Any, bank_date_val: Any) -> int:
    """Calculates posting delay in days between settlement_date and bank_transaction_date."""
    if not settlement_date_val or not bank_date_val:
        return 0

    s_date = (
        settlement_date_val
        if isinstance(settlement_date_val, date)
        else datetime.strptime(str(settlement_date_val)[:10], "%Y-%m-%d").date()
    )
    b_date = (
        bank_date_val
        if isinstance(bank_date_val, date)
        else datetime.strptime(str(bank_date_val)[:10], "%Y-%m-%d").date()
    )

    return (b_date - s_date).days
