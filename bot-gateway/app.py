import asyncio
import httpx
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from inventory_handlers import router as inventory_router

BOT_TOKEN = os.environ["BOT_TOKEN"]
BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend:8000")
ADMIN_TELEGRAM_ID = int(os.environ["ADMIN_TELEGRAM_ID"])

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(inventory_router)


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/auth/request-access", params={
            "telegram_id": message.from_user.id,
            "username": message.from_user.username
        })
        if resp.status_code != 200:
            await message.answer(f"Ошибка backend: {resp.status_code}")
            return
        data = resp.json()

    if data["status"] == "pending":
        await message.answer("Заявка на доступ отправлена администратору. Ожидай подтверждения.")
        await bot.send_message(
            ADMIN_TELEGRAM_ID,
            f"Новая заявка: @{message.from_user.username} (id {message.from_user.id})\n"
            f"Подтвердить: /approve {message.from_user.id} master"
        )
    else:
        await message.answer(f"Твоя роль: {data['status']}\n\nКоманды: /stock /receive /use")


@dp.message(Command("approve"))
async def approve_handler(message: types.Message):
    if message.from_user.id != ADMIN_TELEGRAM_ID:
        return
    parts = message.text.split()
    telegram_id, role = int(parts[1]), parts[2]
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_URL}/auth/approve", params={
            "telegram_id": telegram_id, "role": role, "admin_id": message.from_user.id
        })
        if resp.status_code != 200:
            await message.answer(f"Ошибка backend: {resp.status_code}")
            return
    await message.answer(f"Пользователь {telegram_id} получил роль {role}")
    await bot.send_message(telegram_id, f"Доступ подтверждён! Твоя роль: {role}")


async def main():
    await dp.start_polling(bot, backend_url=BACKEND_URL)


if __name__ == "__main__":
    asyncio.run(main())
