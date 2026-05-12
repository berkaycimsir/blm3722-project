"""Aggregated operational costs for finance queries."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from gym_management.api import schemas
from gym_management.api.deps import get_db
from gym_management.infrastructure.repo_sqlalchemy import SqlMaintenanceRepository, SqlRepairRepository

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/costs", response_model=schemas.CostSummaryRead)
def costs_between(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
):
    maint = SqlMaintenanceRepository(db).total_cost_between(start, end)
    repair = SqlRepairRepository(db).total_cost_between(start, end)
    return schemas.CostSummaryRead(maintenance_total=maint, repair_total=repair)
