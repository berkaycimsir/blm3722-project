"""Monthly planned vs actual budget entries (bütçe planlama — MVP)."""

from dataclasses import dataclass
from enum import StrEnum


class BudgetCategory(StrEnum):
    SUBSCRIPTION_REVENUE = "subscription_revenue"
    MAINTENANCE_EXPENSE = "maintenance_expense"
    REPAIR_EXPENSE = "repair_expense"


@dataclass(slots=True)
class BudgetLine:
    """One row per (year, month, category) with planned and realized amounts."""

    id: int | None
    period_year: int
    period_month: int  # 1-12
    category: BudgetCategory
    planned_amount: str
    actual_amount: str
