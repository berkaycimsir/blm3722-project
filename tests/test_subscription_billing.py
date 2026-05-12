"""Faturalama dönemi (aylık / çok aylık) ile beklenen abonelik tutarı."""

from datetime import date
from decimal import Decimal

from gym_management.domain.subscription.billing import (
    subscription_billing_period_count,
    subscription_expected_total,
)


def test_one_year_span_yearly_cycle_is_single_period() -> None:
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)
    assert subscription_billing_period_count(start, end, 12) == 1
    periods, total = subscription_expected_total("14499.00", start, end, 12)
    assert periods == 1
    assert Decimal(total) == Decimal("14499.00")


def test_monthly_cycle_counts_months_in_span() -> None:
    start = date(2025, 3, 10)
    end = date(2025, 5, 20)
    assert subscription_billing_period_count(start, end, 1) == 3
    periods, total = subscription_expected_total("100.00", start, end, 1)
    assert periods == 3
    assert Decimal(total) == Decimal("300.00")


def test_quarterly_cycle() -> None:
    start = date(2025, 1, 1)
    end = date(2025, 9, 15)
    assert subscription_billing_period_count(start, end, 3) == 3
    periods, total = subscription_expected_total("1000.00", start, end, 3)
    assert periods == 3
    assert Decimal(total) == Decimal("3000.00")
