from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, ForeignKey
from datetime import datetime
from db import Base

class Consumable(Base):
    __tablename__ = "consumables"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=False, default="шт")
    quantity = Column(Numeric(10, 2), nullable=False, default=0)
    threshold = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsumableIncoming(Base):
    __tablename__ = "consumable_incomings"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    consumable_id = Column(Integer, ForeignKey("inventory.consumables.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    supplier = Column(String(100))
    price = Column(Numeric(10, 2))
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsumableUsage(Base):
    __tablename__ = "consumable_usages"
    __table_args__ = {"schema": "inventory"}

    id = Column(Integer, primary_key=True)
    consumable_id = Column(Integer, ForeignKey("inventory.consumables.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    used_by = Column(BigInteger, nullable=False)
    work_log_id = Column(Integer, ForeignKey("worklog.work_logs.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
