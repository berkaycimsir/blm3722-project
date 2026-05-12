"""Recorded subscription payment (ödeme takibi)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Payment:
    """Links monetary collection to an active subscription."""

    id: int | None
    subscription_id: int
    amount: str
    paid_at: datetime
    note: str | None
