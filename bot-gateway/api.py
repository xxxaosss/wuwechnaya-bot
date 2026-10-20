import httpx


async def fetch_consumables(backend_url: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/inventory/consumables")
        return resp.json() if resp.status_code == 200 else []


async def find_consumable(backend_url: str, consumable_id: int):
    consumables = await fetch_consumables(backend_url)
    return next((c for c in consumables if c["id"] == consumable_id), None)


async def update_consumable(backend_url: str, consumable_id: int, **fields):
    """PATCH настроек расходника. Возвращает обновлённый расходник или None при ошибке."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(f"{backend_url}/inventory/consumables/{consumable_id}", json=fields)
    return resp.json() if resp.status_code == 200 else None
