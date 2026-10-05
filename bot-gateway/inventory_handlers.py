import httpx
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import ReceiveStates, UseStates
from keyboards import consumables_keyboard, cancel_keyboard
from auth_helper import require_staff

router = Router()


async def fetch_consumables(backend_url: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/inventory/consumables")
        return resp.json() if resp.status_code == 200 else []


@router.message(Command("stock"))
async def stock_handler(message: types.Message, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer("Доступ только для мастеров и администраторов.")
        return

    consumables = await fetch_consumables(backend_url)
    if not consumables:
        await message.answer("Расходников пока нет. Добавь через /receive.")
        return

    lines = [f"• {c['name']}: {c['quantity']} {c['unit']}" +
             (" ⚠️ заканчивается" if c['quantity'] <= c['threshold'] else "")
             for c in consumables]
    await message.answer("Текущие остатки:\n" + "\n".join(lines))


@router.message(Command("receive"))
async def receive_start(message: types.Message, state: FSMContext, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer("Доступ только для мастеров и администраторов.")
        return

    consumables = await fetch_consumables(backend_url)
    await state.set_state(ReceiveStates.choosing_consumable)
    await message.answer(
        "Выбери расходник для прихода или добавь новый:",
        reply_markup=consumables_keyboard(consumables, "receive")
    )


@router.callback_query(F.data == "receive:new", ReceiveStates.choosing_consumable)
async def receive_new_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ReceiveStates.entering_new_name)
    await callback.message.answer("Введи название нового расходника:")
    await callback.answer()


@router.message(ReceiveStates.entering_new_name)
async def receive_new_name_entered(message: types.Message, state: FSMContext, backend_url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/consumables", json={
            "name": message.text, "unit": "шт", "threshold": 0
        })
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        await state.clear()
        return

    consumable = resp.json()
    await state.update_data(consumable_id=consumable["id"], consumable_name=consumable["name"])
    await state.set_state(ReceiveStates.entering_quantity)
    await message.answer(f"Сколько {consumable['unit']} пришло?", reply_markup=cancel_keyboard())


@router.callback_query(F.data.startswith("receive:"), ReceiveStates.choosing_consumable)
async def receive_choose(callback: types.CallbackQuery, state: FSMContext):
    consumable_id = int(callback.data.split(":")[1])
    await state.update_data(consumable_id=consumable_id)
    await state.set_state(ReceiveStates.entering_quantity)
    await callback.message.answer("Сколько пришло? (введи число)", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(ReceiveStates.entering_quantity)
async def receive_quantity_entered(message: types.Message, state: FSMContext):
    try:
        quantity = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например: 5 или 2.5")
        return
    await state.update_data(quantity=quantity)
    await state.set_state(ReceiveStates.entering_supplier)
    await message.answer("От какого поставщика? (или напиши \"-\", если неважно)")


@router.message(ReceiveStates.entering_supplier)
async def receive_supplier_entered(message: types.Message, state: FSMContext, backend_url: str):
    data = await state.get_data()
    supplier = None if message.text.strip() == "-" else message.text

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/receive", json={
            "consumable_id": data["consumable_id"],
            "quantity": data["quantity"],
            "supplier": supplier,
            "telegram_id": message.from_user.id,
        })

    await state.clear()
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        return

    result = resp.json()
    await message.answer(f"Приход зафиксирован. Новый остаток: {result['new_quantity']}")


@router.message(Command("use"))
async def use_start(message: types.Message, state: FSMContext, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer("Доступ только для мастеров и администраторов.")
        return

    consumables = await fetch_consumables(backend_url)
    if not consumables:
        await message.answer("Расходников пока нет.")
        return

    await state.set_state(UseStates.choosing_consumable)
    await message.answer(
        "Какой расходник списать?",
        reply_markup=consumables_keyboard(consumables, "use")
    )


@router.callback_query(F.data.startswith("use:"), UseStates.choosing_consumable)
async def use_choose(callback: types.CallbackQuery, state: FSMContext):
    consumable_id = int(callback.data.split(":")[1])
    await state.update_data(consumable_id=consumable_id)
    await state.set_state(UseStates.entering_quantity)
    await callback.message.answer("Сколько списать? (введи число)", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(UseStates.entering_quantity)
async def use_quantity_entered(message: types.Message, state: FSMContext, backend_url: str):
    try:
        quantity = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например: 1 или 0.5")
        return

    data = await state.get_data()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/use", json={
            "consumable_id": data["consumable_id"],
            "quantity": quantity,
            "telegram_id": message.from_user.id,
        })

    await state.clear()
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        return

    result = resp.json()
    text = f"Списано. Остаток «{result['name']}»: {result['new_quantity']}"
    if result["low_stock"]:
        text += "\n⚠️ Остаток ниже порога — пора закупить!"
    await message.answer(text)


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()
