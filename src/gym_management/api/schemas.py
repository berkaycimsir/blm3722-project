"""Pydantic models exposed by HTTP API (DTO layer)."""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from gym_management.domain.equipment.equipment import EquipmentStatus
from gym_management.domain.finance.budget import BudgetCategory
from gym_management.domain.subscription.schedule_strategy import PackageKind
from gym_management.domain.subscription.subscription import SubscriptionStatus


class MedicalReportCreate(BaseModel):
    institution_name: str = Field(min_length=1, max_length=255)
    issued_on: date


class MedicalReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_name: str
    issued_on: date
    expires_on: date


class SubscriberCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    medical_report_id: int | None = None


class SubscriberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    phone: str
    medical_report_id: int | None


class SubscriptionPackageCreate(BaseModel):
    name: str
    price: str
    kind: PackageKind
    billing_cycle_months: int = Field(default=1, ge=1, le=120)
    allowed_weekdays: list[int] | None = None
    window_start: time | None = None
    window_end: time | None = None


class SubscriptionPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: str
    kind: PackageKind
    billing_cycle_months: int
    allowed_weekdays: list[int] | None
    window_start: time | None
    window_end: time | None


class SubscriptionCreate(BaseModel):
    subscriber_id: int
    package_id: int
    start_date: date
    end_date: date | None = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    package_id: int
    start_date: date
    end_date: date | None
    status: SubscriptionStatus


class PaymentCreate(BaseModel):
    amount: str
    paid_at: datetime | None = None
    note: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    amount: str
    paid_at: datetime
    note: str | None


class EquipmentCreate(BaseModel):
    name: str
    serial_number: str | None = None
    status: EquipmentStatus = EquipmentStatus.OPERATIONAL


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    serial_number: str | None
    status: EquipmentStatus


class MaintenanceCreate(BaseModel):
    performed_on: date
    cost: str
    description: str


class MaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    performed_on: date
    cost: str
    description: str


class RepairCreate(BaseModel):
    service_vendor: str
    sent_on: date
    returned_on: date | None = None
    cost: str
    description: str


class RepairRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    service_vendor: str
    sent_on: date
    returned_on: date | None
    cost: str
    description: str


class BudgetLineUpsert(BaseModel):
    category: BudgetCategory
    planned: str
    actual: str


class BudgetLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_year: int
    period_month: int
    category: BudgetCategory
    planned: str
    actual: str


class CostSummaryRead(BaseModel):
    maintenance_total: str
    repair_total: str
