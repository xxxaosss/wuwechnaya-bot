from aiogram import types

from fmt import fmt_stock


def stock_lines(consumables: list[dict]) -> list[str]:
    lines = []
    for c in consumables:
        flag = " ⚠️ заканчивается" if c["quantity"] <= c["threshold"] else ""
        lines.append(f"• {c['name']}: {fmt_stock(c)}{flag}")
    return lines


async def send_lines(message: types.Message, header: str, lines: list[str]):
    """Отправляет длинный список частями (лимит Telegram — 4096 символов)."""
    chunk = header
    for line in lines:
        if len(chunk) + len(line) + 1 > 3800:
            await message.answer(chunk)
            chunk = ""
        chunk += ("\n" if chunk else "") + line
    if chunk:
        await message.answer(chunk)
