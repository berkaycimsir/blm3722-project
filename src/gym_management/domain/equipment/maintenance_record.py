"""In-gym preventive/corrective maintenance."""

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class MaintenanceRecord:
    """Maintenance performed on-premises with captured labor/parts cost."""

    id: int | None
    equipment_id: int
    performed_on: date
    cost_amount: str
    description: str
