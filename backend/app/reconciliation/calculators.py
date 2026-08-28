from decimal import Decimal
from typing import List, Tuple, Any
from app.reconciliation.constants import (
    round_currency,
    EXPECTED_FEE_RATE,
    DEFAULT_TAX_RATE,
)


def calculate_expected_fee_and_tax(
    gross_amount: Decimal,
    fee_rate: Decimal = EXPECTED_FEE_RATE,
    tax_rate: Decimal = DEFAULT_TAX_RATE,
) -> Tuple[Decimal, Decimal]:
    """Calculates expected gateway fee and tax on fee for a given gross amount."""
    if gross_amount is None:
        return Decimal("0.00"), Decimal("0.00")
    expected_fee = round_currency(gross_amount * fee_rate)
    expected_tax = round_currency(expected_fee * tax_rate)
    return expected_fee, expected_tax


def calculate_total_refund_amount(refunds: List[Any]) -> Decimal:
    """Sums all completed/valid refund amounts for a payment."""
    if not refunds:
        return Decimal("0.00")
    total = Decimal("0.00")
    for r in refunds:
        # Check refund status if available
        status = getattr(r, "refund_status", "COMPLETED")
        if status in ["COMPLETED", "SUCCESS"]:
            total += getattr(r, "refund_amount", Decimal("0.00"))
    return round_currency(total)


def calculate_expected_settlement_net(
    gross_amount: Decimal,
    fee_amount: Decimal,
    tax_amount: Decimal,
    refund_amount: Decimal = Decimal("0.00"),
    adjustment_amount: Decimal = Decimal("0.00"),
) -> Decimal:
    """Calculates expected net settlement payout: gross - fee - tax - refunds + adjustments."""
    gross = gross_amount if gross_amount is not None else Decimal("0.00")
    fee = fee_amount if fee_amount is not None else Decimal("0.00")
    tax = tax_amount if tax_amount is not None else Decimal("0.00")
    ref = refund_amount if refund_amount is not None else Decimal("0.00")
    adj = adjustment_amount if adjustment_amount is not None else Decimal("0.00")
    return round_currency(gross - fee - tax - ref + adj)


def calculate_invoice_breakdown(
    total_amount: Decimal,
    tax_rate: Decimal = DEFAULT_TAX_RATE,
) -> Tuple[Decimal, Decimal]:
    """Calculates expected subtotal and tax_amount from invoice total_amount and tax_rate."""
    if total_amount is None:
        return Decimal("0.00"), Decimal("0.00")
    subtotal = round_currency(total_amount / (Decimal("1.00") + tax_rate))
    tax_amount = round_currency(total_amount - subtotal)
    return subtotal, tax_amount
