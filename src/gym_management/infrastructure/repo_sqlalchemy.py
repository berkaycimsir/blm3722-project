"""Concrete repositories using SQLAlchemy Session."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gym_management.domain.equipment.equipment import Equipment
from gym_management.domain.equipment.maintenance_record import MaintenanceRecord
from gym_management.domain.equipment.repair_record import RepairRecord
from gym_management.domain.finance.budget import BudgetCategory, BudgetLine
from gym_management.domain.finance.payment import Payment
from gym_management.domain.membership.medical_report import MedicalReport
from gym_management.domain.membership.subscriber import Subscriber
from gym_management.domain.subscription.subscription import Subscription
from gym_management.domain.subscription.subscription_package import SubscriptionPackage
from gym_management.infrastructure import mappers
from gym_management.infrastructure.orm_models import (
    BudgetLineRow,
    EquipmentRow,
    MaintenanceRecordRow,
    MedicalReportRow,
    PaymentRow,
    RepairRecordRow,
    SubscriberRow,
    SubscriptionPackageRow,
    SubscriptionRow,
)


class SqlMedicalReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, report: MedicalReport) -> MedicalReport:
        row = mappers.medical_report_to_row(report)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.medical_report_from_row(row)

    def get(self, report_id: int) -> MedicalReport | None:
        row = self._session.get(MedicalReportRow, report_id)
        return None if row is None else mappers.medical_report_from_row(row)

    def list_expiring_before(self, cutoff: date) -> list[MedicalReport]:
        rows = list(self._session.scalars(select(MedicalReportRow)).all())
        out: list[MedicalReport] = []
        for row in rows:
            domain = mappers.medical_report_from_row(row)
            if domain.expires_on() <= cutoff:
                out.append(domain)
        return sorted(out, key=lambda r: r.expires_on())

    def list_all(self) -> list[MedicalReport]:
        rows = self._session.scalars(select(MedicalReportRow).order_by(MedicalReportRow.id)).all()
        return [mappers.medical_report_from_row(r) for r in rows]


class SqlSubscriberRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, subscriber: Subscriber) -> Subscriber:
        row = mappers.subscriber_to_row(subscriber)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.subscriber_from_row(row)

    def get(self, subscriber_id: int) -> Subscriber | None:
        row = self._session.get(SubscriberRow, subscriber_id)
        return None if row is None else mappers.subscriber_from_row(row)

    def list(self) -> list[Subscriber]:
        rows = self._session.scalars(select(SubscriberRow).order_by(SubscriberRow.id)).all()
        return [mappers.subscriber_from_row(r) for r in rows]


class SqlSubscriptionPackageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, package: SubscriptionPackage) -> SubscriptionPackage:
        row = mappers.subscription_package_to_row(package)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.subscription_package_from_row(row)

    def get(self, package_id: int) -> SubscriptionPackage | None:
        row = self._session.get(SubscriptionPackageRow, package_id)
        return None if row is None else mappers.subscription_package_from_row(row)

    def list(self) -> list[SubscriptionPackage]:
        rows = self._session.scalars(
            select(SubscriptionPackageRow).order_by(SubscriptionPackageRow.id)
        ).all()
        return [mappers.subscription_package_from_row(r) for r in rows]


class SqlSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, subscription: Subscription) -> Subscription:
        row = mappers.subscription_to_row(subscription)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.subscription_from_row(row)

    def get(self, subscription_id: int) -> Subscription | None:
        row = self._session.get(SubscriptionRow, subscription_id)
        return None if row is None else mappers.subscription_from_row(row)

    def list_for_subscriber(self, subscriber_id: int) -> list[Subscription]:
        stmt = (
            select(SubscriptionRow)
            .where(SubscriptionRow.subscriber_id == subscriber_id)
            .order_by(SubscriptionRow.id)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.subscription_from_row(r) for r in rows]

    def count_all(self) -> int:
        return int(self._session.scalar(select(func.count()).select_from(SubscriptionRow)) or 0)


class SqlPaymentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, payment: Payment) -> Payment:
        row = mappers.payment_to_row(payment)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.payment_from_row(row)

    def list_for_subscription(self, subscription_id: int) -> list[Payment]:
        stmt = (
            select(PaymentRow)
            .where(PaymentRow.subscription_id == subscription_id)
            .order_by(PaymentRow.paid_at)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.payment_from_row(r) for r in rows]

    def total_for_subscription(self, subscription_id: int) -> str:
        stmt = select(func.coalesce(func.sum(PaymentRow.amount), 0)).where(
            PaymentRow.subscription_id == subscription_id
        )
        total = self._session.scalar(stmt)
        return str(Decimal(total))

    def total_between(self, start: datetime, end: datetime) -> str:
        """Sum payment amounts with paid_at in [start, end)."""
        stmt = select(func.coalesce(func.sum(PaymentRow.amount), 0)).where(
            PaymentRow.paid_at >= start,
            PaymentRow.paid_at < end,
        )
        total = self._session.scalar(stmt)
        return str(Decimal(total))


class SqlBudgetLineRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, line: BudgetLine) -> BudgetLine:
        existing = self.get_line(line.period_year, line.period_month, line.category)
        if existing and existing.id is not None:
            row = self._session.get(BudgetLineRow, existing.id)
            assert row is not None
            row.planned = line.planned_amount
            row.actual = line.actual_amount
            self._session.flush()
            self._session.refresh(row)
            return mappers.budget_line_from_row(row)
        row = mappers.budget_line_to_row(line)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.budget_line_from_row(row)

    def apply_subscription_payment_to_budget(self, paid_at: datetime, amount: str) -> BudgetLine:
        """Add payment to SUBSCRIPTION_REVENUE actual for the calendar month of ``paid_at``."""
        dt = paid_at
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        year, month = dt.year, dt.month
        delta = Decimal(amount)
        existing = self.get_line(year, month, BudgetCategory.SUBSCRIPTION_REVENUE)
        base = Decimal(existing.actual_amount) if existing else Decimal("0")
        new_actual = (base + delta).quantize(Decimal("0.01"))
        planned = existing.planned_amount if existing else "0.00"
        return self.upsert(
            BudgetLine(
                id=None,
                period_year=year,
                period_month=month,
                category=BudgetCategory.SUBSCRIPTION_REVENUE,
                planned_amount=planned,
                actual_amount=str(new_actual),
            )
        )

    def list_period(self, year: int, month: int) -> list[BudgetLine]:
        stmt = (
            select(BudgetLineRow)
            .where(
                BudgetLineRow.period_year == year,
                BudgetLineRow.period_month == month,
            )
            .order_by(BudgetLineRow.category)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.budget_line_from_row(r) for r in rows]

    def get_line(self, year: int, month: int, category: BudgetCategory) -> BudgetLine | None:
        stmt = select(BudgetLineRow).where(
            BudgetLineRow.period_year == year,
            BudgetLineRow.period_month == month,
            BudgetLineRow.category == category.value,
        )
        row = self._session.scalars(stmt).first()
        return None if row is None else mappers.budget_line_from_row(row)


class SqlEquipmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, equipment: Equipment) -> Equipment:
        row = mappers.equipment_to_row(equipment)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.equipment_from_row(row)

    def get(self, equipment_id: int) -> Equipment | None:
        row = self._session.get(EquipmentRow, equipment_id)
        return None if row is None else mappers.equipment_from_row(row)

    def list(self) -> list[Equipment]:
        rows = self._session.scalars(select(EquipmentRow).order_by(EquipmentRow.id)).all()
        return [mappers.equipment_from_row(r) for r in rows]


class SqlMaintenanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: MaintenanceRecord) -> MaintenanceRecord:
        row = mappers.maintenance_to_row(record)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.maintenance_from_row(row)

    def list_for_equipment(self, equipment_id: int) -> list[MaintenanceRecord]:
        stmt = (
            select(MaintenanceRecordRow)
            .where(MaintenanceRecordRow.equipment_id == equipment_id)
            .order_by(MaintenanceRecordRow.performed_on)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.maintenance_from_row(r) for r in rows]

    def total_cost_between(self, start: date, end: date) -> str:
        stmt = select(func.coalesce(func.sum(MaintenanceRecordRow.cost), 0)).where(
            MaintenanceRecordRow.performed_on >= start,
            MaintenanceRecordRow.performed_on <= end,
        )
        total = self._session.scalar(stmt)
        return str(Decimal(total))


class SqlRepairRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: RepairRecord) -> RepairRecord:
        row = mappers.repair_to_row(record)
        row.id = None
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return mappers.repair_from_row(row)

    def list_for_equipment(self, equipment_id: int) -> list[RepairRecord]:
        stmt = (
            select(RepairRecordRow)
            .where(RepairRecordRow.equipment_id == equipment_id)
            .order_by(RepairRecordRow.sent_on)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.repair_from_row(r) for r in rows]

    def total_cost_between(self, start: date, end: date) -> str:
        stmt = select(func.coalesce(func.sum(RepairRecordRow.cost), 0)).where(
            RepairRecordRow.sent_on >= start,
            RepairRecordRow.sent_on <= end,
        )
        total = self._session.scalar(stmt)
        return str(Decimal(total))
