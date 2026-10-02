# backend/auth/models.py
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(64))
    role = Column(String(20), default="pending")
    approved_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)
