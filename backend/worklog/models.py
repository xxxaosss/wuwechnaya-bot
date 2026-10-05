from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, ForeignKey
from datetime import datetime
from db import Base


class Service(Base):
    __tablename__ = "services"
    __table_args__ = {"schema": "worklog"}

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0)


class WorkLog(Base):
    __tablename__ = "work_logs"
    __table_args__ = {"schema": "worklog"}

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("worklog.services.id"), nullable=False)
    master_telegram_id = Column(BigInteger, nullable=False)
    client_name = Column(String(100))
    cost = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
