"""Vendor repair workflow (external technical service)."""

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class RepairRecord:
    """Repair performed off-site; vendor name + costs are auditable."""

    id: int | None
    equipment_id: int
    service_vendor: str
    sent_on: date
    returned_on: date | None
    cost_amount: str
    description: str
