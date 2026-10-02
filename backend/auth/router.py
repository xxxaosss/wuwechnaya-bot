# backend/auth/router.py
from db import get_session
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-access")
async def request_access(
    telegram_id: int, username: str | None, session: AsyncSession = Depends(get_session)
):
    existing = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if existing:
        return {"status": existing.role}
    user = User(telegram_id=telegram_id, username=username, role="pending")
    session.add(user)
    await session.commit()
    return {"status": "pending"}


@router.post("/approve")
async def approve(
    telegram_id: int,
    role: str,
    admin_id: int,
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(role=role, approved_by=admin_id)
    )
    await session.commit()
    return {"status": "approved", "role": role}


@router.get("/me/{telegram_id}")
async def me(telegram_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        return {"role": "unknown"}
    return {"role": user.role, "username": user.username}
