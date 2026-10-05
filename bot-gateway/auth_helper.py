import httpx

ALLOWED_ROLES = {"master", "admin"}


async def get_user_role(backend_url: str, telegram_id: int) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/auth/me/{telegram_id}")
        if resp.status_code != 200:
            return "unknown"
        return resp.json().get("role", "unknown")


async def require_staff(backend_url: str, telegram_id: int) -> bool:
    role = await get_user_role(backend_url, telegram_id)
    return role in ALLOWED_ROLES
