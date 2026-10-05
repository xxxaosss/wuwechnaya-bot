from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from .models import Service, WorkLog
from .schemas import ServiceOut, ServiceCreate, WorkLogCreate
from inventory.models import Consumable, ConsumableUsage

router = APIRouter(prefix="/worklog", tags=["worklog"])


@router.get("/services", response_model=list[ServiceOut])
async def list_services(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Service).order_by(Service.name))
    return result.all()


@router.post("/services", response_model=ServiceOut)
async def create_service(data: ServiceCreate, session: AsyncSession = Depends(get_session)):
    service = Service(name=data.name, price=Decimal(str(data.price)))
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


@router.post("/complete")
async def complete_work(data: WorkLogCreate, session: AsyncSession = Depends(get_session)):
    service = await session.get(Service, data.service_id)
    if not service:
        raise HTTPException(404, "Service not found")

    # Проверяем остатки ДО любых изменений — чтобы не списать часть и упасть на середине
    consumables_map = {}
    for item in data.consumables:
        consumable = await session.get(Consumable, item.consumable_id)
        if not consumable:
            raise HTTPException(404, f"Consumable {item.consumable_id} not found")
        qty = Decimal(str(item.quantity))
        if consumable.quantity < qty:
            raise HTTPException(400, f"Not enough stock for {consumable.name}")
        consumables_map[item.consumable_id] = (consumable, qty)

    work_log = WorkLog(
        service_id=data.service_id,
        master_telegram_id=data.master_telegram_id,
        client_name=data.client_name,
        cost=Decimal(str(data.cost)),
    )
    session.add(work_log)
    await session.flush()  # получаем work_log.id до коммита всей транзакции

    low_stock_items = []
    for consumable_id, (consumable, qty) in consumables_map.items():
        consumable.quantity -= qty
        session.add(ConsumableUsage(
            consumable_id=consumable_id,
            quantity=qty,
            used_by=data.master_telegram_id,
            work_log_id=work_log.id,
        ))
        if consumable.quantity <= consumable.threshold:
            low_stock_items.append(consumable.name)

    await session.commit()
    return {"status": "ok", "work_log_id": work_log.id, "low_stock": low_stock_items}
