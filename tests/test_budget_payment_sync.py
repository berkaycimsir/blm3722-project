"""Payment recording updates subscription revenue budget actual for that month."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gym_management.domain.finance.budget import BudgetCategory, BudgetLine
from gym_management.infrastructure.orm_models import Base
from gym_management.infrastructure.repo_sqlalchemy import SqlBudgetLineRepository


def test_apply_subscription_payment_adds_to_existing_budget_line() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        repo = SqlBudgetLineRepository(session)
        repo.upsert(
            BudgetLine(
                id=None,
                period_year=2026,
                period_month=5,
                category=BudgetCategory.SUBSCRIPTION_REVENUE,
                planned_amount="100.00",
                actual_amount="10.00",
            )
        )
        repo.apply_subscription_payment_to_budget(datetime(2026, 5, 15, 12, 0, 0), "25.50")
        line = repo.get_line(2026, 5, BudgetCategory.SUBSCRIPTION_REVENUE)
        assert line is not None
        assert Decimal(line.actual_amount) == Decimal("35.50")
        assert line.planned_amount == "100.00"
    finally:
        session.close()


def test_apply_subscription_payment_creates_line_when_missing() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        repo = SqlBudgetLineRepository(session)
        repo.apply_subscription_payment_to_budget(datetime(2026, 3, 1, 8, 0, 0), "500.00")
        line = repo.get_line(2026, 3, BudgetCategory.SUBSCRIPTION_REVENUE)
        assert line is not None
        assert Decimal(line.actual_amount) == Decimal("500.00")
        assert Decimal(line.planned_amount) == Decimal("0.00")
    finally:
        session.close()
