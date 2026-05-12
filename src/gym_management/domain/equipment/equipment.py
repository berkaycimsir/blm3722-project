"""Gym equipment inventory."""

from dataclasses import dataclass
from enum import StrEnum


class EquipmentStatus(StrEnum):
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    OUT_FOR_REPAIR = "out_for_repair"


@dataclass(slots=True)
class Equipment:
    """Tracked asset for maintenance and external repair workflows."""

    id: int | None
    name: str
    serial_number: str | None
    status: EquipmentStatus
