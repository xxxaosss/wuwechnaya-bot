from pydantic import BaseModel
from typing import Optional


class ServiceOut(BaseModel):
    id: int
    name: str
    price: float

    class Config:
        from_attributes = True


class ServiceCreate(BaseModel):
    name: str
    price: float = 0


class ConsumableUsageItem(BaseModel):
    consumable_id: int
    quantity: float


class WorkLogCreate(BaseModel):
    service_id: int
    master_telegram_id: int
    client_name: Optional[str] = None
    cost: float
    consumables: list[ConsumableUsageItem] = []
