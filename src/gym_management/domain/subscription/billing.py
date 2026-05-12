"""Billing expectations for subscriptions (faturalama dönemi sayısı)."""

from datetime import date
from decimal import Decimal
import math


def subscription_billing_period_count(start: date, end: date, cycle_months: int = 1) -> int:
    """How many faturalama dönemi fit between start and end (inclusive month span).

    ``cycle_months``: each invoice covers this many calendar months (1 = aylık, 3 = üç aylık, 12 = yıllık).
    ``price_amount`` on the package is the amount due *per such period*.
    """
    if end < start:
        return 1
    month_span = (end.year - start.year) * 12 + (end.month - start.month) + 1
    month_span = max(1, month_span)
    cycle = max(1, int(cycle_months))
    return max(1, math.ceil(month_span / cycle))


def subscription_expected_total(
    price_amount: str, start: date, end: date, cycle_months: int = 1
) -> tuple[int, str]:
    periods = subscription_billing_period_count(start, end, cycle_months)
    unit = Decimal(price_amount)
    total = (unit * periods).quantize(Decimal("0.01"))
    return periods, str(total)
