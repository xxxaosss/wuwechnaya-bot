import os
import httpx

ALLOWED_ROLES = {"master", "admin"}
ADMIN_TELEGRAM_ID = int(os.environ["ADMIN_TELEGRAM_ID"])


async def get_user_role(backend_url: str, telegram_id: int) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/auth/me/{telegram_id}")
        if resp.status_code != 200:
            return "unknown"
        return resp.json().get("role", "unknown")


async def require_staff(backend_url: str, telegram_id: int) -> bool:
    role = await get_user_role(backend_url, telegram_id)
    return role in ALLOWED_ROLES


async def require_admin(backend_url: str, telegram_id: int) -> bool:
    if telegram_id == ADMIN_TELEGRAM_ID:
        return True
    return await get_user_role(backend_url, telegram_id) == "admin"
