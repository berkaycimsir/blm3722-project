"""Unit tests: subscription visit rules (Strategy pattern).

Designed by: <Student name / ID — fill in for the course report>.
"""

from datetime import time

import pytest

from gym_management.domain.subscription.package_factory import create_subscription_package
from gym_management.domain.subscription.schedule_strategy import (
    DailyTimeWindowStrategy,
    FixedWeekdaysStrategy,
    PackageKind,
)


def test_fixed_two_day_package_allows_only_configured_weekdays() -> None:
    pkg = create_subscription_package(
        id=1,
        name="Test 2-day",
        price_amount="100.00",
        kind=PackageKind.FIXED_TWO_DAYS,
        allowed_weekdays=frozenset({0, 3}),
    )
    assert pkg.allows_visit(0, None) is True
    assert pkg.allows_visit(3, None) is True
    assert pkg.allows_visit(2, None) is False


def test_daily_window_requires_time_inside_window() -> None:
    pkg = create_subscription_package(
        id=2,
        name="Test daily",
        price_amount="200.00",
        kind=PackageKind.DAILY_TIME_WINDOW,
        window_start=time(9, 0),
        window_end=time(11, 0),
    )
    assert pkg.allows_visit(2, time(10, 0)) is True
    assert pkg.allows_visit(2, time(8, 59)) is False
    assert pkg.allows_visit(2, None) is False


def test_fixed_weekdays_strategy_rejects_empty_configuration() -> None:
    with pytest.raises(ValueError):
        FixedWeekdaysStrategy(frozenset())


def test_daily_window_strategy_rejects_inverted_range() -> None:
    with pytest.raises(ValueError):
        DailyTimeWindowStrategy(time(12, 0), time(11, 0))
