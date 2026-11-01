from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def q(value: Decimal | int | str) -> Decimal:
    """Round to the nearest dirham (0.01 QAR), halves away from zero."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
