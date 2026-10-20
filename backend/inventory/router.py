from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from .models import Consumable, ConsumableIncoming, ConsumableUsage
from .schemas import (
    ConsumableOut, ConsumableCreate, ConsumableUpdate, ReceiveRequest, UseRequest, ImportRequest,
)
from .units import to_base, apply_receive, reconfigure

router = APIRouter(prefix="/inventory", tags=["inventory"])

TWO = Decimal("0.01")


def D(value) -> Decimal:
    return Decimal(str(value))


def stock_info(c: Consumable) -> dict:
    return {
        "name": c.name,
        "unit": c.unit,
        "quantity": float(c.quantity),
        "pack_size": float(c.pack_size) if c.pack_size else None,
        "pieces": float(c.pieces),
        "low_stock": c.quantity <= c.threshold,
    }


@router.get("/consumables", response_model=list[ConsumableOut])
async def list_consumables(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Consumable).order_by(Consumable.name))
    return result.all()


@router.get("/low-stock", response_model=list[ConsumableOut])
async def low_stock(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(Consumable).where(Consumable.quantity <= Consumable.threshold))
    return result.all()


@router.post("/consumables", response_model=ConsumableOut)
async def create_consumable(data: ConsumableCreate, session: AsyncSession = Depends(get_session)):
    pack = D(data.pack_size) if data.pack_size and data.unit != "шт" else None
    consumable = Consumable(
        name=data.name.strip(), unit=data.unit, pack_size=pack,
        quantity=Decimal(0), threshold=D(data.threshold),
    )
    session.add(consumable)
    await session.commit()
    await session.refresh(consumable)
    return consumable


@router.patch("/consumables/{consumable_id}", response_model=ConsumableOut)
async def update_consumable(consumable_id: int, data: ConsumableUpdate,
                            session: AsyncSession = Depends(get_session)):
    """Меняет способ учёта / нетто пачки / порог. Число пачек сохраняется."""
    c = await session.get(Consumable, consumable_id)
    if not c:
        raise HTTPException(404, "Consumable not found")

    unit = data.unit or c.unit
    if unit not in ("шт", "мл", "г"):
        raise HTTPException(400, "unit must be шт, мл or г")
    if data.pack_size and not data.unit and c.unit == "шт":
        raise HTTPException(400, "unit is required to set pack_size for шт")

    if data.unit or data.pack_size:
        if unit == "шт":
            pack = None
        else:
            pack = D(data.pack_size) if data.pack_size else c.pack_size
            if not pack:
                raise HTTPException(400, "pack_size is required for мл/г")
        reconfigure(c, unit, pack)

    if data.threshold_packs is not None:
        c.threshold = (D(data.threshold_packs) * (c.pack_size or Decimal(1))).quantize(TWO)

    await session.commit()
    return c


@router.post("/receive")
async def receive(data: ReceiveRequest, session: AsyncSession = Depends(get_session)):
    consumable = await session.get(Consumable, data.consumable_id)
    if not consumable:
        raise HTTPException(404, "Consumable not found")

    pieces = D(data.pieces)
    added = apply_receive(consumable, pieces)
    session.add(ConsumableIncoming(
        consumable_id=consumable.id, quantity=added, pieces=pieces, created_by=data.telegram_id,
    ))
    await session.commit()
    return {"status": "ok", **stock_info(consumable)}


@router.post("/use")
async def use(data: UseRequest, session: AsyncSession = Depends(get_session)):
    consumable = await session.get(Consumable, data.consumable_id)
    if not consumable:
        raise HTTPException(404, "Consumable not found")

    qty = to_base(consumable, D(data.amount), data.mode)
    if consumable.quantity < qty:
        raise HTTPException(400, "Not enough stock")

    consumable.quantity -= qty
    session.add(ConsumableUsage(consumable_id=consumable.id, quantity=qty, used_by=data.telegram_id))
    await session.commit()
    return {"status": "ok", **stock_info(consumable)}


@router.post("/import")
async def import_lines(data: ImportRequest, session: AsyncSession = Depends(get_session)):
    """Загрузка списка: позиции ищутся по названию (без учёта регистра), новые создаются.
    Если указан weight — позиция считается в граммах по нетто одной пачки (у существующей
    позиции учёт переключается, число пачек сохраняется)."""
    existing = {c.name.strip().lower(): c for c in (await session.scalars(select(Consumable))).all()}
    created = updated = converted = 0

    for line in data.lines:
        name = line.name.strip()
        key = name.lower()

        if line.weight:
            unit, pack = "г", D(line.weight)
        else:
            pack = D(line.volume) if line.volume else None
            unit = line.unit if pack and line.unit in ("мл", "г") else ("мл" if pack else "шт")

        consumable = existing.get(key)
        if consumable is None:
            consumable = Consumable(
                name=name, unit=unit, pack_size=pack,
                quantity=Decimal(0), threshold=Decimal(0),
            )
            session.add(consumable)
            await session.flush()
            existing[key] = consumable
            created += 1
        else:
            if line.weight and (consumable.unit != "г" or consumable.pack_size != pack):
                reconfigure(consumable, "г", pack)
                converted += 1
            updated += 1

        pieces = D(line.pieces)
        if pieces > 0:  # 0 пачек — только завести/настроить позицию, без записи прихода
            added = apply_receive(consumable, pieces)
            session.add(ConsumableIncoming(
                consumable_id=consumable.id, quantity=added, pieces=pieces, created_by=data.telegram_id,
            ))

    await session.commit()
    return {"created": created, "updated": updated, "converted": converted}
