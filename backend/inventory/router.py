from decimal import Decimal

from db import get_session
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Consumable, ConsumableIncoming, ConsumableUsage
from .schemas import ConsumableCreate, ConsumableOut, ReceiveRequest, UseRequest

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/consumables", response_model=list[ConsumableOut])
async def list_consumables(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Consumable).order_by(Consumable.name))
    return result.all()


@router.get("/low-stock", response_model=list[ConsumableOut])
async def low_stock(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(Consumable).where(Consumable.quantity <= Consumable.threshold)
    )
    return result.all()


@router.post("/consumables", response_model=ConsumableOut)
async def create_consumable(
    data: ConsumableCreate, session: AsyncSession = Depends(get_session)
):
    consumable = Consumable(name=data.name, unit=data.unit, threshold=data.threshold)
    session.add(consumable)
    await session.commit()
    await session.refresh(consumable)
    return consumable


@router.post("/receive")
async def receive(data: ReceiveRequest, session: AsyncSession = Depends(get_session)):
    consumable = await session.get(Consumable, data.consumable_id)
    if not consumable:
        raise HTTPException(404, "Consumable not found")

    consumable.quantity += Decimal(str(data.quantity))
    session.add(
        ConsumableIncoming(
            consumable_id=data.consumable_id,
            quantity=Decimal(str(data.quantity)),
            supplier=data.supplier,
            price=Decimal(str(data.price)) if data.price is not None else None,
            created_by=data.telegram_id,
        )
    )
    await session.commit()
    return {"status": "ok", "new_quantity": float(consumable.quantity)}


@router.post("/use")
async def use(data: UseRequest, session: AsyncSession = Depends(get_session)):
    consumable = await session.get(Consumable, data.consumable_id)
    if not consumable:
        raise HTTPException(404, "Consumable not found")

    qty = Decimal(str(data.quantity))
    if consumable.quantity < qty:
        raise HTTPException(400, "Not enough stock")

    consumable.quantity -= qty
    session.add(
        ConsumableUsage(
            consumable_id=data.consumable_id,
            quantity=qty,
            used_by=data.telegram_id,
        )
    )
    await session.commit()

    low = consumable.quantity <= consumable.threshold
    return {
        "status": "ok",
        "new_quantity": float(consumable.quantity),
        "low_stock": low,
        "name": consumable.name,
    }
