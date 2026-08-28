from decimal import Decimal, ROUND_HALF_UP

# Monetary & Timing Constants
MONEY_QUANTUM = Decimal("0.01")
AMOUNT_TOLERANCE = Decimal("0.01")
TIMING_TOLERANCE_DAYS = 3

# Fee & Tax Policy Constants
EXPECTED_FEE_RATE = Decimal("0.02")  # 2.0% gateway fee
DEFAULT_TAX_RATE = Decimal("0.18")   # 18.0% GST tax rate on fees & invoices


def round_currency(val: Decimal) -> Decimal:
    """Quantizes a Decimal value to standard 2-decimal monetary precision (INR)."""
    if val is None:
        return Decimal("0.00")
    return val.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def round_rate(val: Decimal) -> Decimal:
    """Quantizes a tax/fee rate Decimal value to 4-decimal precision."""
    if val is None:
        return Decimal("0.0000")
    return val.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def amounts_equal(expected: Decimal, actual: Decimal) -> bool:
    """Centralized amount comparison using AMOUNT_TOLERANCE (0.01 INR)."""
    if expected is None or actual is None:
        return False
    return abs(expected - actual) <= AMOUNT_TOLERANCE


def amount_diff(actual: Decimal, expected: Decimal) -> Decimal:
    """Calculates actual - expected monetary difference."""
    if actual is None:
        actual = Decimal("0.00")
    if expected is None:
        expected = Decimal("0.00")
    return round_currency(actual - expected)
