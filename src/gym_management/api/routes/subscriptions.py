"""Catalog packages, memberships, payments, and budget lines."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from gym_management.api import schemas
from gym_management.api.deps import get_db
from gym_management.domain.finance.budget import BudgetLine
from gym_management.domain.finance.payment import Payment
from gym_management.domain.subscription.package_factory import create_subscription_package
from gym_management.domain.subscription.subscription import Subscription
from gym_management.infrastructure.repo_sqlalchemy import (
    SqlBudgetLineRepository,
    SqlPaymentRepository,
    SqlSubscriptionPackageRepository,
    SqlSubscriptionRepository,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("/packages", response_model=schemas.SubscriptionPackageRead)
def create_package(payload: schemas.SubscriptionPackageCreate, db: Session = Depends(get_db)):
    allowed = frozenset(payload.allowed_weekdays) if payload.allowed_weekdays is not None else None
    try:
        package = create_subscription_package(
            id=None,
            name=payload.name,
            price_amount=payload.price,
            kind=payload.kind,
            billing_cycle_months=payload.billing_cycle_months,
            allowed_weekdays=allowed,
            window_start=payload.window_start,
            window_end=payload.window_end,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repo = SqlSubscriptionPackageRepository(db)
    created = repo.add(package)
    if created.id is None:
        raise HTTPException(status_code=500, detail="package id not assigned")
    return schemas.SubscriptionPackageRead(
        id=created.id,
        name=created.name,
        price=created.price_amount,
        kind=created.kind,
        billing_cycle_months=created.billing_cycle_months,
        allowed_weekdays=sorted(created.allowed_weekdays)
        if created.allowed_weekdays
        else None,
        window_start=created.window_start,
        window_end=created.window_end,
    )


@router.get("/packages", response_model=list[schemas.SubscriptionPackageRead])
def list_packages(db: Session = Depends(get_db)):
    repo = SqlSubscriptionPackageRepository(db)
    items = repo.list()
    out: list[schemas.SubscriptionPackageRead] = []
    for p in items:
        if p.id is None:
            continue
        out.append(
            schemas.SubscriptionPackageRead(
                id=p.id,
                name=p.name,
                price=p.price_amount,
                kind=p.kind,
                billing_cycle_months=p.billing_cycle_months,
                allowed_weekdays=sorted(p.allowed_weekdays) if p.allowed_weekdays else None,
                window_start=p.window_start,
                window_end=p.window_end,
            )
        )
    return out


@router.post("/memberships", response_model=schemas.SubscriptionRead)
def create_membership(payload: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    repo = SqlSubscriptionRepository(db)
    created = repo.add(
        Subscription(
            id=None,
            subscriber_id=payload.subscriber_id,
            package_id=payload.package_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=payload.status,
        )
    )
    if created.id is None:
        raise HTTPException(status_code=500, detail="subscription id not assigned")
    return schemas.SubscriptionRead(
        id=created.id,
        subscriber_id=created.subscriber_id,
        package_id=created.package_id,
        start_date=created.start_date,
        end_date=created.end_date,
        status=created.status,
    )


@router.get(
    "/memberships/by-subscriber/{subscriber_id}",
    response_model=list[schemas.SubscriptionRead],
)
def list_memberships_for_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    repo = SqlSubscriptionRepository(db)
    rows = repo.list_for_subscriber(subscriber_id)
    return [
        schemas.SubscriptionRead(
            id=s.id,
            subscriber_id=s.subscriber_id,
            package_id=s.package_id,
            start_date=s.start_date,
            end_date=s.end_date,
            status=s.status,
        )
        for s in rows
        if s.id is not None
    ]


@router.post(
    "/memberships/{subscription_id}/payments",
    response_model=schemas.PaymentRead,
)
def add_payment(
    subscription_id: int,
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
):
    sub_repo = SqlSubscriptionRepository(db)
    if sub_repo.get(subscription_id) is None:
        raise HTTPException(status_code=404, detail="subscription not found")
    paid_at = payload.paid_at or datetime.now(timezone.utc)
    payment = Payment(
        id=None,
        subscription_id=subscription_id,
        amount=payload.amount,
        paid_at=paid_at,
        note=payload.note,
    )
    repo = SqlPaymentRepository(db)
    created = repo.add(payment)
    if created.id is None:
        raise HTTPException(status_code=500, detail="payment id not assigned")
    SqlBudgetLineRepository(db).apply_subscription_payment_to_budget(paid_at, payload.amount)
    return schemas.PaymentRead(
        id=created.id,
        subscription_id=created.subscription_id,
        amount=created.amount,
        paid_at=created.paid_at,
        note=created.note,
    )


@router.get(
    "/memberships/{subscription_id}/payments",
    response_model=list[schemas.PaymentRead],
)
def list_payments(subscription_id: int, db: Session = Depends(get_db)):
    repo = SqlPaymentRepository(db)
    rows = repo.list_for_subscription(subscription_id)
    return [
        schemas.PaymentRead(
            id=p.id,
            subscription_id=p.subscription_id,
            amount=p.amount,
            paid_at=p.paid_at,
            note=p.note,
        )
        for p in rows
        if p.id is not None
    ]


@router.get(
    "/memberships/{subscription_id}/payments/total",
    response_model=dict[str, str],
)
def payment_total(subscription_id: int, db: Session = Depends(get_db)):
    repo = SqlPaymentRepository(db)
    total = repo.total_for_subscription(subscription_id)
    return {"subscription_id": str(subscription_id), "total_paid": total}


@router.put(
    "/budget/{year}/{month}",
    response_model=list[schemas.BudgetLineRead],
)
def upsert_budget(
    year: int,
    month: int,
    payload: list[schemas.BudgetLineUpsert],
    db: Session = Depends(get_db),
):
    repo = SqlBudgetLineRepository(db)
    saved: list[schemas.BudgetLineRead] = []
    for line in payload:
        domain = BudgetLine(
            id=None,
            period_year=year,
            period_month=month,
            category=line.category,
            planned_amount=line.planned,
            actual_amount=line.actual,
        )
        updated = repo.upsert(domain)
        if updated.id is None:
            raise HTTPException(status_code=500, detail="budget line id missing")
        saved.append(
            schemas.BudgetLineRead(
                id=updated.id,
                period_year=updated.period_year,
                period_month=updated.period_month,
                category=updated.category,
                planned=updated.planned_amount,
                actual=updated.actual_amount,
            )
        )
    return saved


@router.get(
    "/budget/{year}/{month}",
    response_model=list[schemas.BudgetLineRead],
)
def get_budget(year: int, month: int, db: Session = Depends(get_db)):
    repo = SqlBudgetLineRepository(db)
    rows = repo.list_period(year, month)
    return [
        schemas.BudgetLineRead(
            id=r.id,
            period_year=r.period_year,
            period_month=r.period_month,
            category=r.category,
            planned=r.planned_amount,
            actual=r.actual_amount,
        )
        for r in rows
        if r.id is not None
    ]
