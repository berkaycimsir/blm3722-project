"""Equipment, on-site maintenance, and external repairs."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from gym_management.api import schemas
from gym_management.api.deps import get_db
from gym_management.domain.equipment.equipment import Equipment
from gym_management.domain.equipment.maintenance_record import MaintenanceRecord
from gym_management.domain.equipment.repair_record import RepairRecord
from gym_management.infrastructure.repo_sqlalchemy import (
    SqlEquipmentRepository,
    SqlMaintenanceRepository,
    SqlRepairRepository,
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("", response_model=schemas.EquipmentRead)
def create_equipment(payload: schemas.EquipmentCreate, db: Session = Depends(get_db)):
    repo = SqlEquipmentRepository(db)
    created = repo.add(
        Equipment(
            id=None,
            name=payload.name,
            serial_number=payload.serial_number,
            status=payload.status,
        )
    )
    if created.id is None:
        raise HTTPException(status_code=500, detail="equipment id not assigned")
    return schemas.EquipmentRead(
        id=created.id,
        name=created.name,
        serial_number=created.serial_number,
        status=created.status,
    )


@router.get("", response_model=list[schemas.EquipmentRead])
def list_equipment(db: Session = Depends(get_db)):
    repo = SqlEquipmentRepository(db)
    rows = repo.list()
    return [
        schemas.EquipmentRead(
            id=e.id,
            name=e.name,
            serial_number=e.serial_number,
            status=e.status,
        )
        for e in rows
        if e.id is not None
    ]


@router.post("/{equipment_id}/maintenance", response_model=schemas.MaintenanceRead)
def add_maintenance(
    equipment_id: int,
    payload: schemas.MaintenanceCreate,
    db: Session = Depends(get_db),
):
    equip_repo = SqlEquipmentRepository(db)
    if equip_repo.get(equipment_id) is None:
        raise HTTPException(status_code=404, detail="equipment not found")
    repo = SqlMaintenanceRepository(db)
    created = repo.add(
        MaintenanceRecord(
            id=None,
            equipment_id=equipment_id,
            performed_on=payload.performed_on,
            cost_amount=payload.cost,
            description=payload.description,
        )
    )
    if created.id is None:
        raise HTTPException(status_code=500, detail="maintenance id not assigned")
    return schemas.MaintenanceRead(
        id=created.id,
        equipment_id=created.equipment_id,
        performed_on=created.performed_on,
        cost=created.cost_amount,
        description=created.description,
    )


@router.get(
    "/{equipment_id}/maintenance",
    response_model=list[schemas.MaintenanceRead],
)
def list_maintenance(equipment_id: int, db: Session = Depends(get_db)):
    repo = SqlMaintenanceRepository(db)
    rows = repo.list_for_equipment(equipment_id)
    return [
        schemas.MaintenanceRead(
            id=r.id,
            equipment_id=r.equipment_id,
            performed_on=r.performed_on,
            cost=r.cost_amount,
            description=r.description,
        )
        for r in rows
        if r.id is not None
    ]


@router.post("/{equipment_id}/repairs", response_model=schemas.RepairRead)
def add_repair(equipment_id: int, payload: schemas.RepairCreate, db: Session = Depends(get_db)):
    equip_repo = SqlEquipmentRepository(db)
    if equip_repo.get(equipment_id) is None:
        raise HTTPException(status_code=404, detail="equipment not found")
    repo = SqlRepairRepository(db)
    created = repo.add(
        RepairRecord(
            id=None,
            equipment_id=equipment_id,
            service_vendor=payload.service_vendor,
            sent_on=payload.sent_on,
            returned_on=payload.returned_on,
            cost_amount=payload.cost,
            description=payload.description,
        )
    )
    if created.id is None:
        raise HTTPException(status_code=500, detail="repair id not assigned")
    return schemas.RepairRead(
        id=created.id,
        equipment_id=created.equipment_id,
        service_vendor=created.service_vendor,
        sent_on=created.sent_on,
        returned_on=created.returned_on,
        cost=created.cost_amount,
        description=created.description,
    )


@router.get("/{equipment_id}/repairs", response_model=list[schemas.RepairRead])
def list_repairs(equipment_id: int, db: Session = Depends(get_db)):
    repo = SqlRepairRepository(db)
    rows = repo.list_for_equipment(equipment_id)
    return [
        schemas.RepairRead(
            id=r.id,
            equipment_id=r.equipment_id,
            service_vendor=r.service_vendor,
            sent_on=r.sent_on,
            returned_on=r.returned_on,
            cost=r.cost_amount,
            description=r.description,
        )
        for r in rows
        if r.id is not None
    ]
