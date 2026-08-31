from decimal import Decimal

# Absolute monetary tolerance for tax amount comparison (INR 0.01)
TAX_AMOUNT_TOLERANCE = Decimal("0.01")

# Tolerance for tax rate comparison (0.0001 = 0.01%)
TAX_RATE_TOLERANCE = Decimal("0.0001")
