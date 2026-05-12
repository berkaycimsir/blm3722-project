"""HTTP routes: membership + medical compliance."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from gym_management.api import schemas
from gym_management.api.deps import get_db
from gym_management.domain.membership.medical_report import MedicalReport
from gym_management.domain.membership.subscriber import Subscriber
from gym_management.infrastructure.repo_sqlalchemy import SqlMedicalReportRepository, SqlSubscriberRepository

router = APIRouter(prefix="/membership", tags=["membership"])


@router.post("/medical-reports", response_model=schemas.MedicalReportRead)
def create_medical_report(payload: schemas.MedicalReportCreate, db: Session = Depends(get_db)):
    repo = SqlMedicalReportRepository(db)
    created = repo.add(
        MedicalReport(id=None, institution_name=payload.institution_name, issued_on=payload.issued_on)
    )
    return schemas.MedicalReportRead(
        id=created.id,
        institution_name=created.institution_name,
        issued_on=created.issued_on,
        expires_on=created.expires_on(),
    )


@router.get("/medical-reports/expiring", response_model=list[schemas.MedicalReportRead])
def list_expiring_reports(
    by_date: date = Query(..., description="Include reports whose expiry is on/before this date."),
    db: Session = Depends(get_db),
):
    repo = SqlMedicalReportRepository(db)
    items = repo.list_expiring_before(by_date)
    return [
        schemas.MedicalReportRead(
            id=r.id,
            institution_name=r.institution_name,
            issued_on=r.issued_on,
            expires_on=r.expires_on(),
        )
        for r in items
        if r.id is not None
    ]


@router.post("/subscribers", response_model=schemas.SubscriberRead)
def create_subscriber(payload: schemas.SubscriberCreate, db: Session = Depends(get_db)):
    repo = SqlSubscriberRepository(db)
    created = repo.add(
        Subscriber(
            id=None,
            full_name=payload.full_name,
            email=str(payload.email),
            phone=payload.phone,
            medical_report_id=payload.medical_report_id,
        )
    )
    if created.id is None:
        raise HTTPException(status_code=500, detail="subscriber id not assigned")
    return schemas.SubscriberRead(
        id=created.id,
        full_name=created.full_name,
        email=created.email,
        phone=created.phone,
        medical_report_id=created.medical_report_id,
    )


@router.get("/subscribers", response_model=list[schemas.SubscriberRead])
def list_subscribers(db: Session = Depends(get_db)):
    repo = SqlSubscriberRepository(db)
    rows = repo.list()
    return [
        schemas.SubscriberRead(
            id=s.id,
            full_name=s.full_name,
            email=s.email,
            phone=s.phone,
            medical_report_id=s.medical_report_id,
        )
        for s in rows
        if s.id is not None
    ]


@router.get("/subscribers/{subscriber_id}", response_model=schemas.SubscriberRead)
def get_subscriber(subscriber_id: int, db: Session = Depends(get_db)):
    repo = SqlSubscriberRepository(db)
    s = repo.get(subscriber_id)
    if s is None or s.id is None:
        raise HTTPException(status_code=404, detail="subscriber not found")
    return schemas.SubscriberRead(
        id=s.id,
        full_name=s.full_name,
        email=s.email,
        phone=s.phone,
        medical_report_id=s.medical_report_id,
    )
