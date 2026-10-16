import httpx


async def fetch_consumables(backend_url: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/inventory/consumables")
        return resp.json() if resp.status_code == 200 else []


async def find_consumable(backend_url: str, consumable_id: int):
    consumables = await fetch_consumables(backend_url)
    return next((c for c in consumables if c["id"] == consumable_id), None)
