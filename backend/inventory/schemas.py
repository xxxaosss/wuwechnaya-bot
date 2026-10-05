from pydantic import BaseModel
from typing import Optional


class ConsumableOut(BaseModel):
    id: int
    name: str
    unit: str
    quantity: float
    threshold: float

    class Config:
        from_attributes = True


class ConsumableCreate(BaseModel):
    name: str
    unit: str = "шт"
    threshold: float = 0


class ReceiveRequest(BaseModel):
    consumable_id: int
    quantity: float
    supplier: Optional[str] = None
    price: Optional[float] = None
    telegram_id: int


class UseRequest(BaseModel):
    consumable_id: int
    quantity: float
    telegram_id: int
