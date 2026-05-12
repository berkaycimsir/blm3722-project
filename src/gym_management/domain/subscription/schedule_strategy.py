"""
Visit scheduling strategies for subscription packages (Strategy pattern).

Weekday integers follow Monday=0 .. Sunday=6 (datetime.weekday()).
"""

from abc import ABC, abstractmethod
from datetime import time
from enum import StrEnum


class PackageKind(StrEnum):
    """Declarative package categories required by the assignment brief."""

    FIXED_TWO_DAYS = "fixed_two_days"
    FIXED_THREE_DAYS = "fixed_three_days"
    DAILY_TIME_WINDOW = "daily_time_window"


class VisitScheduleStrategy(ABC):
    """Polymorphic rule: may the member visit on this weekday / optional clock time?"""

    @abstractmethod
    def allows_visit(self, weekday: int, at_time: time | None) -> bool:
        """weekday: 0=Monday .. 6=Sunday (datetime.weekday)."""


class FixedWeekdaysStrategy(VisitScheduleStrategy):
    """Member may attend only on configured weekdays (2-day or 3-day packages)."""

    def __init__(self, allowed_weekdays: frozenset[int]) -> None:
        if not allowed_weekdays:
            msg = "allowed_weekdays must be non-empty"
            raise ValueError(msg)
        self._allowed = allowed_weekdays

    def allows_visit(self, weekday: int, at_time: time | None) -> bool:
        _ = at_time
        return weekday in self._allowed


class DailyTimeWindowStrategy(VisitScheduleStrategy):
    """Every day is allowed, but only within [window_start, window_end] inclusive."""

    def __init__(self, window_start: time, window_end: time) -> None:
        if window_start >= window_end:
            msg = "window_start must be before window_end"
            raise ValueError(msg)
        self._start = window_start
        self._end = window_end

    def allows_visit(self, weekday: int, at_time: time | None) -> bool:
        _ = weekday
        if at_time is None:
            return False
        return self._start <= at_time <= self._end
