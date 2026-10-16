from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, ForeignKey
from datetime import datetime
from db import Base


class Consumable(Base):
    __tablename__ = "consumables"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False, default="шт")        # базовая единица: шт / мл / г
    quantity = Column(Numeric(10, 2), nullable=False, default=0)   # остаток в базовых единицах
    pack_size = Column(Numeric(10, 2), nullable=True)              # базовых единиц в 1 шт (NULL — только штуки)
    threshold = Column(Numeric(10, 2), nullable=False, default=0)  # порог в базовых единицах
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def pieces(self):
        """Остаток в штуках (для позиций с объёмом — дробный)."""
        if self.pack_size:
            return self.quantity / self.pack_size
        return self.quantity


class ConsumableIncoming(Base):
    __tablename__ = "consumable_incomings"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    consumable_id = Column(Integer, ForeignKey("inventory.consumables.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)   # в базовых единицах
    pieces = Column(Numeric(10, 2))                     # штук по приходу
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsumableUsage(Base):
    __tablename__ = "consumable_usages"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    consumable_id = Column(Integer, ForeignKey("inventory.consumables.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)   # в базовых единицах
    used_by = Column(BigInteger, nullable=False)
    work_log_id = Column(Integer, ForeignKey("worklog.work_logs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
