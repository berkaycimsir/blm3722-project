"""Declarative ORM models mirroring domain aggregates."""

from datetime import date, datetime, time

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MedicalReportRow(Base):
    __tablename__ = "medical_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)


class SubscriberRow(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    medical_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("medical_reports.id"), nullable=True
    )


class SubscriptionPackageRow(Base):
    __tablename__ = "subscription_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)
    billing_cycle_months: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # JSON array of weekday ints for fixed-day packages, e.g. [0,3]
    allowed_weekdays_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    window_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    window_end: Mapped[time | None] = mapped_column(Time, nullable=True)


class SubscriptionRow(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), nullable=False)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("subscription_packages.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class PaymentRow(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), nullable=False)
    amount: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class BudgetLineRow(Base):
    __tablename__ = "budget_lines"
    __table_args__ = (
        UniqueConstraint(
            "period_year", "period_month", "category", name="uq_budget_period_category"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    planned: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)
    actual: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)


class EquipmentRow(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)


class MaintenanceRecordRow(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    performed_on: Mapped[date] = mapped_column(Date, nullable=False)
    cost: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class RepairRecordRow(Base):
    __tablename__ = "repair_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    service_vendor: Mapped[str] = mapped_column(String(255), nullable=False)
    sent_on: Mapped[date] = mapped_column(Date, nullable=False)
    returned_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    cost: Mapped[str] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
