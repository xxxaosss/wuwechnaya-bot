from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ConsumableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    unit: str
    quantity: float
    pack_size: Optional[float] = None
    pieces: float
    threshold: float
    threshold_packs: float


class ConsumableCreate(BaseModel):
    name: str
    unit: str = "шт"
    pack_size: Optional[float] = None
    threshold: float = 0


class ConsumableUpdate(BaseModel):
    unit: Optional[str] = None                                   # шт / мл / г
    pack_size: Optional[float] = Field(default=None, gt=0)       # нетто одной пачки
    threshold_packs: Optional[float] = Field(default=None, ge=0)  # порог в пачках


class ReceiveRequest(BaseModel):
    consumable_id: int
    pieces: float = Field(gt=0)
    telegram_id: int


class UseRequest(BaseModel):
    consumable_id: int
    amount: float = Field(gt=0)
    mode: str = "base"          # "pieces" | "base"
    telegram_id: int


class ImportLine(BaseModel):
    name: str
    pieces: float = Field(ge=0)
    volume: Optional[float] = None
    unit: Optional[str] = None
    weight: Optional[float] = Field(default=None, gt=0)   # нетто пачки в граммах


class ImportRequest(BaseModel):
    telegram_id: int
    lines: list[ImportLine]
