"""Active subscription linking a subscriber to a catalog package."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Subscription:
    """Time-bounded entitlement; payments are tracked separately."""

    id: int | None
    subscriber_id: int
    package_id: int
    start_date: date
    end_date: date | None
    status: SubscriptionStatus
