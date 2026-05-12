"""
Factory for SubscriptionPackage + strategy wiring (Factory + Strategy composition).

Keeps construction rules in one place so infrastructure seeding/tests stay aligned.
"""

from datetime import time

from gym_management.domain.subscription.schedule_strategy import (
    DailyTimeWindowStrategy,
    FixedWeekdaysStrategy,
    PackageKind,
    VisitScheduleStrategy,
)
from gym_management.domain.subscription.subscription_package import SubscriptionPackage


def build_strategy_for_kind(
    kind: PackageKind,
    *,
    allowed_weekdays: frozenset[int] | None = None,
    window_start: time | None = None,
    window_end: time | None = None,
) -> VisitScheduleStrategy:
    if kind in (PackageKind.FIXED_TWO_DAYS, PackageKind.FIXED_THREE_DAYS):
        if allowed_weekdays is None:
            msg = "allowed_weekdays required for fixed-day packages"
            raise ValueError(msg)
        expected = 2 if kind == PackageKind.FIXED_TWO_DAYS else 3
        if len(allowed_weekdays) != expected:
            msg = f"{kind} requires exactly {expected} weekdays"
            raise ValueError(msg)
        return FixedWeekdaysStrategy(allowed_weekdays)
    if kind == PackageKind.DAILY_TIME_WINDOW:
        if window_start is None or window_end is None:
            msg = "window_start and window_end required for daily window packages"
            raise ValueError(msg)
        return DailyTimeWindowStrategy(window_start, window_end)
    msg = f"unsupported package kind: {kind}"
    raise ValueError(msg)


def create_subscription_package(
    *,
    id: int | None,
    name: str,
    price_amount: str,
    kind: PackageKind,
    billing_cycle_months: int = 1,
    allowed_weekdays: frozenset[int] | None = None,
    window_start: time | None = None,
    window_end: time | None = None,
) -> SubscriptionPackage:
    if billing_cycle_months < 1:
        msg = "billing_cycle_months must be >= 1"
        raise ValueError(msg)
    strategy = build_strategy_for_kind(
        kind,
        allowed_weekdays=allowed_weekdays,
        window_start=window_start,
        window_end=window_end,
    )
    return SubscriptionPackage(
        id=id,
        name=name,
        price_amount=price_amount,
        billing_cycle_months=billing_cycle_months,
        kind=kind,
        allowed_weekdays=allowed_weekdays,
        window_start=window_start,
        window_end=window_end,
        schedule_strategy=strategy,
    )
