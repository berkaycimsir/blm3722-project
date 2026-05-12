"""Bidirectional mapping between ORM rows and domain dataclasses."""

import json

from gym_management.domain.equipment.equipment import Equipment, EquipmentStatus
from gym_management.domain.equipment.maintenance_record import MaintenanceRecord
from gym_management.domain.equipment.repair_record import RepairRecord
from gym_management.domain.finance.budget import BudgetCategory, BudgetLine
from gym_management.domain.finance.payment import Payment
from gym_management.domain.membership.medical_report import MedicalReport
from gym_management.domain.membership.subscriber import Subscriber
from gym_management.domain.subscription.package_factory import create_subscription_package
from gym_management.domain.subscription.schedule_strategy import PackageKind
from gym_management.domain.subscription.subscription import Subscription, SubscriptionStatus
from gym_management.domain.subscription.subscription_package import SubscriptionPackage
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


def medical_report_from_row(row: MedicalReportRow) -> MedicalReport:
    return MedicalReport(id=row.id, institution_name=row.institution_name, issued_on=row.issued_on)


def medical_report_to_row(domain: MedicalReport) -> MedicalReportRow:
    return MedicalReportRow(
        id=domain.id,
        institution_name=domain.institution_name,
        issued_on=domain.issued_on,
    )


def subscriber_from_row(row: SubscriberRow) -> Subscriber:
    return Subscriber(
        id=row.id,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        medical_report_id=row.medical_report_id,
    )


def subscriber_to_row(domain: Subscriber) -> SubscriberRow:
    return SubscriberRow(
        id=domain.id,
        full_name=domain.full_name,
        email=domain.email,
        phone=domain.phone,
        medical_report_id=domain.medical_report_id,
    )


def subscription_package_from_row(row: SubscriptionPackageRow) -> SubscriptionPackage:
    kind = PackageKind(row.kind)
    allowed = None
    if row.allowed_weekdays_json:
        allowed = frozenset(json.loads(row.allowed_weekdays_json))
    return create_subscription_package(
        id=row.id,
        name=row.name,
        price_amount=str(row.price),
        kind=kind,
        billing_cycle_months=int(row.billing_cycle_months),
        allowed_weekdays=allowed,
        window_start=row.window_start,
        window_end=row.window_end,
    )


def subscription_package_to_row(domain: SubscriptionPackage) -> SubscriptionPackageRow:
    allowed_json = None
    if domain.allowed_weekdays is not None:
        allowed_json = json.dumps(sorted(domain.allowed_weekdays))
    return SubscriptionPackageRow(
        id=domain.id,
        name=domain.name,
        price=domain.price_amount,
        billing_cycle_months=domain.billing_cycle_months,
        kind=domain.kind.value,
        allowed_weekdays_json=allowed_json,
        window_start=domain.window_start,
        window_end=domain.window_end,
    )


def subscription_from_row(row: SubscriptionRow) -> Subscription:
    return Subscription(
        id=row.id,
        subscriber_id=row.subscriber_id,
        package_id=row.package_id,
        start_date=row.start_date,
        end_date=row.end_date,
        status=SubscriptionStatus(row.status),
    )


def subscription_to_row(domain: Subscription) -> SubscriptionRow:
    return SubscriptionRow(
        id=domain.id,
        subscriber_id=domain.subscriber_id,
        package_id=domain.package_id,
        start_date=domain.start_date,
        end_date=domain.end_date,
        status=domain.status.value if isinstance(domain.status, SubscriptionStatus) else domain.status,
    )


def payment_from_row(row: PaymentRow) -> Payment:
    return Payment(
        id=row.id,
        subscription_id=row.subscription_id,
        amount=str(row.amount),
        paid_at=row.paid_at,
        note=row.note,
    )


def payment_to_row(domain: Payment) -> PaymentRow:
    return PaymentRow(
        id=domain.id,
        subscription_id=domain.subscription_id,
        amount=domain.amount,
        paid_at=domain.paid_at,
        note=domain.note,
    )


def budget_line_from_row(row: BudgetLineRow) -> BudgetLine:
    return BudgetLine(
        id=row.id,
        period_year=row.period_year,
        period_month=row.period_month,
        category=BudgetCategory(row.category),
        planned_amount=str(row.planned),
        actual_amount=str(row.actual),
    )


def budget_line_to_row(domain: BudgetLine) -> BudgetLineRow:
    return BudgetLineRow(
        id=domain.id,
        period_year=domain.period_year,
        period_month=domain.period_month,
        category=domain.category.value,
        planned=domain.planned_amount,
        actual=domain.actual_amount,
    )


def equipment_from_row(row: EquipmentRow) -> Equipment:
    return Equipment(
        id=row.id,
        name=row.name,
        serial_number=row.serial_number,
        status=EquipmentStatus(row.status),
    )


def equipment_to_row(domain: Equipment) -> EquipmentRow:
    return EquipmentRow(
        id=domain.id,
        name=domain.name,
        serial_number=domain.serial_number,
        status=domain.status.value,
    )


def maintenance_from_row(row: MaintenanceRecordRow) -> MaintenanceRecord:
    return MaintenanceRecord(
        id=row.id,
        equipment_id=row.equipment_id,
        performed_on=row.performed_on,
        cost_amount=str(row.cost),
        description=row.description,
    )


def maintenance_to_row(domain: MaintenanceRecord) -> MaintenanceRecordRow:
    return MaintenanceRecordRow(
        id=domain.id,
        equipment_id=domain.equipment_id,
        performed_on=domain.performed_on,
        cost=domain.cost_amount,
        description=domain.description,
    )


def repair_from_row(row: RepairRecordRow) -> RepairRecord:
    return RepairRecord(
        id=row.id,
        equipment_id=row.equipment_id,
        service_vendor=row.service_vendor,
        sent_on=row.sent_on,
        returned_on=row.returned_on,
        cost_amount=str(row.cost),
        description=row.description,
    )


def repair_to_row(domain: RepairRecord) -> RepairRecordRow:
    return RepairRecordRow(
        id=domain.id,
        equipment_id=domain.equipment_id,
        service_vendor=domain.service_vendor,
        sent_on=domain.sent_on,
        returned_on=domain.returned_on,
        cost=domain.cost_amount,
        description=domain.description,
    )
