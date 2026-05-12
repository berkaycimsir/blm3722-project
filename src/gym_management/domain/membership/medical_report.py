"""Medical clearance aligned with Turkish regulation (1-year validity from issue date)."""

from dataclasses import dataclass
from datetime import date


def _add_one_calendar_year(issued_on: date) -> date:
    """Return the same calendar day next year, clamping Feb 29 -> Feb 28 when needed."""
    year = issued_on.year + 1
    try:
        return date(year, issued_on.month, issued_on.day)
    except ValueError:
        return date(year, 2, 28)


@dataclass(slots=True)
class MedicalReport:
    """Stores who issued the clearance and when; expiry is derived (+1 year)."""

    id: int | None
    institution_name: str
    issued_on: date

    def expires_on(self) -> date:
        return _add_one_calendar_year(self.issued_on)

    def is_expired(self, as_of: date) -> bool:
        return as_of > self.expires_on()

    def days_until_expiry(self, as_of: date) -> int:
        """Negative means already expired."""
        return (self.expires_on() - as_of).days
