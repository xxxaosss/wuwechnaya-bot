import httpx
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from states import WorkLogStates
from keyboards import services_keyboard, consumables_multiselect_keyboard
from auth_helper import require_staff
from inventory_handlers import fetch_consumables

router = Router()


async def fetch_services(backend_url: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{backend_url}/worklog/services")
        return resp.json() if resp.status_code == 200 else []


@router.message(F.text == "💼 Провести работу")
async def worklog_start(message: types.Message, state: FSMContext, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer("Доступ только для мастеров и администраторов.")
        return

    services = await fetch_services(backend_url)
    await state.set_state(WorkLogStates.choosing_service)
    await message.answer("Выбери услугу:", reply_markup=services_keyboard(services))


@router.callback_query(F.data == "service:new", WorkLogStates.choosing_service)
async def new_service_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(WorkLogStates.entering_new_service_name)
    await callback.message.answer("Введи название новой услуги:")
    await callback.answer()


@router.message(WorkLogStates.entering_new_service_name)
async def new_service_name_entered(message: types.Message, state: FSMContext):
    await state.update_data(new_service_name=message.text)
    await state.set_state(WorkLogStates.entering_new_service_price)
    await message.answer("Базовая цена услуги? (число, например 1500)")


@router.message(WorkLogStates.entering_new_service_price)
async def new_service_price_entered(message: types.Message, state: FSMContext, backend_url: str):
    try:
        price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например: 1500")
        return

    data = await state.get_data()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/worklog/services", json={
            "name": data["new_service_name"], "price": price
        })
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        await state.clear()
        return

    service = resp.json()
    await proceed_to_consumables(message, state, service["id"], service["name"], service["price"], backend_url)


@router.callback_query(F.data.startswith("service:"), WorkLogStates.choosing_service)
async def service_chosen(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    service_id = int(callback.data.split(":")[1])
    services = await fetch_services(backend_url)
    service = next((s for s in services if s["id"] == service_id), None)
    if not service:
        await callback.answer("Услуга не найдена")
        return
    await proceed_to_consumables(callback.message, state, service["id"], service["name"], service["price"], backend_url)
    await callback.answer()


async def proceed_to_consumables(message, state: FSMContext, service_id, service_name, service_price, backend_url):
    await state.update_data(
        service_id=service_id,
        service_name=service_name,
        service_price=service_price,
        selected_consumables=[],
    )
    consumables = await fetch_consumables(backend_url)
    await state.set_state(WorkLogStates.choosing_consumables)
    await message.answer(
        f"Услуга: {service_name}\nОтметь использованные расходники:",
        reply_markup=consumables_multiselect_keyboard(consumables, [])
    )


@router.callback_query(F.data.startswith("toggle:"), WorkLogStates.choosing_consumables)
async def toggle_consumable(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    consumable_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_consumables", [])
    if consumable_id in selected:
        selected.remove(consumable_id)
    else:
        selected.append(consumable_id)
    await state.update_data(selected_consumables=selected)

    consumables = await fetch_consumables(backend_url)
    await callback.message.edit_reply_markup(
        reply_markup=consumables_multiselect_keyboard(consumables, selected)
    )
    await callback.answer()


@router.callback_query(F.data == "consumables:none", WorkLogStates.choosing_consumables)
async def no_consumables(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected_consumables=[], consumables_queue=[], consumables_qty={})
    await state.set_state(WorkLogStates.entering_client_name)
    await callback.message.answer("Без расходников. Имя клиента? (или \"-\")")
    await callback.answer()


@router.callback_query(F.data == "consumables:done", WorkLogStates.choosing_consumables)
async def consumables_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_consumables", [])
    if not selected:
        await callback.answer("Выбери хотя бы один расходник или нажми «Без расходников»", show_alert=True)
        return
    await state.update_data(consumables_queue=list(selected), consumables_qty={})
    await ask_next_quantity(callback.message, state)
    await callback.answer()


async def ask_next_quantity(message: types.Message, state: FSMContext):
    data = await state.get_data()
    queue = data.get("consumables_queue", [])
    if not queue:
        await state.set_state(WorkLogStates.entering_client_name)
        await message.answer("Имя клиента? (или \"-\")")
        return

    next_id = queue[0]
    await state.set_state(WorkLogStates.entering_consumable_quantity)
    await message.answer(f"Сколько использовано? (расходник id {next_id}) Введи число")


@router.message(WorkLogStates.entering_consumable_quantity)
async def consumable_quantity_entered(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например: 1 или 0.5")
        return

    data = await state.get_data()
    queue = data.get("consumables_queue", [])
    current_id = queue.pop(0)
    qty_map = data.get("consumables_qty", {})
    qty_map[str(current_id)] = qty
    await state.update_data(consumables_queue=queue, consumables_qty=qty_map)
    await ask_next_quantity(message, state)


@router.message(WorkLogStates.entering_client_name)
async def client_name_entered(message: types.Message, state: FSMContext):
    client_name = None if message.text.strip() == "-" else message.text
    await state.update_data(client_name=client_name)
    data = await state.get_data()
    default_price = data.get("service_price", 0)
    await state.set_state(WorkLogStates.entering_cost)
    await message.answer(f"Итоговая стоимость? (базовая цена услуги: {default_price})")


@router.message(WorkLogStates.entering_cost)
async def cost_entered(message: types.Message, state: FSMContext, backend_url: str):
    try:
        cost = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число, например: 1500")
        return

    data = await state.get_data()
    qty_map = data.get("consumables_qty", {})
    consumables_payload = [
        {"consumable_id": int(cid), "quantity": qty} for cid, qty in qty_map.items()
    ]

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/worklog/complete", json={
            "service_id": data["service_id"],
            "master_telegram_id": message.from_user.id,
            "client_name": data.get("client_name"),
            "cost": cost,
            "consumables": consumables_payload,
        })

    await state.clear()
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code} — {resp.text}")
        return

    result = resp.json()
    text = f"Работа сохранена ✅\nУслуга: {data['service_name']}\nСтоимость: {cost}"
    if result.get("low_stock"):
        text += "\n⚠️ Заканчиваются: " + ", ".join(result["low_stock"])
    await message.answer(text)
