"""Sellable subscription templates with polymorphic visit rules."""

from dataclasses import dataclass
from datetime import time

from gym_management.domain.subscription.schedule_strategy import (
    PackageKind,
    VisitScheduleStrategy,
)


@dataclass(slots=True)
class SubscriptionPackage:
    """Catalog package: pricing + schedule strategy for attendance validation."""

    id: int | None
    name: str
    price_amount: str  # Decimal as string at domain edge; DB uses Numeric
    billing_cycle_months: int  # 1=aylık, 3=3 aylık, 12=yıllık; price = tutar / dönem
    kind: PackageKind
    allowed_weekdays: frozenset[int] | None
    window_start: time | None
    window_end: time | None
    schedule_strategy: VisitScheduleStrategy

    def allows_visit(self, weekday: int, at_time: time | None) -> bool:
        return self.schedule_strategy.allows_visit(weekday, at_time)
