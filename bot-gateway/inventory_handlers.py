import httpx
from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import ReceiveStates, UseStates
from keyboards import cancel_keyboard, kind_keyboard, mode_keyboard, receive_keyboard
from auth_helper import require_staff
from api import fetch_consumables, find_consumable, update_consumable
from picker import start_picker, close_list
from fmt import fmt_stock, num, parse_number

router = Router()

NO_ACCESS = "Доступ только для мастеров и администраторов."


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


def receive_prompt(c: dict) -> str:
    text = f"«{c['name']}»\nСейчас: {fmt_stock(c)}"
    if c.get("pack_size"):
        text += f"\nВ пачке: {num(c['pack_size'])} {c['unit']} (нетто)"
    return text + "\nСколько пачек (штук) пришло?"


# ---------------- Остатки ----------------

@router.message(F.text == "📦 Остатки")
@router.message(Command("stock"))
async def stock_handler(message: types.Message, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer(NO_ACCESS)
        return

    consumables = await fetch_consumables(backend_url)
    if not consumables:
        await message.answer("Расходников пока нет. Добавь через «➕ Приход».")
        return

    lines = []
    for c in consumables:
        flag = " ⚠️ заканчивается" if c["quantity"] <= c["threshold"] else ""
        lines.append(f"• {c['name']}: {fmt_stock(c)}{flag}")
    await send_lines(message, "Текущие остатки:", lines)


# ---------------- Приход ----------------

@router.message(F.text == "➕ Приход")
@router.message(Command("receive"))
async def receive_start(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer(NO_ACCESS)
        return

    await state.set_state(ReceiveStates.choosing_consumable)
    await start_picker(bot, message.chat.id, state, backend_url)


@router.callback_query(F.data == "receive:new", ReceiveStates.choosing_consumable)
async def receive_new_name(callback: types.CallbackQuery, state: FSMContext):
    await close_list(callback, "Новый расходник")
    await state.set_state(ReceiveStates.entering_new_name)
    await callback.message.answer("Введи название нового расходника:")
    await callback.answer()


@router.message(ReceiveStates.entering_new_name)
async def receive_new_name_entered(message: types.Message, state: FSMContext):
    await state.update_data(new_name=message.text.strip())
    await state.set_state(ReceiveStates.choosing_new_kind)
    await message.answer("Как учитываем этот расходник?", reply_markup=kind_keyboard())


async def create_and_continue(message: types.Message, state: FSMContext, backend_url: str,
                              name: str, unit: str, pack_size):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/consumables", json={
            "name": name, "unit": unit, "pack_size": pack_size,
        })
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        await state.clear()
        return

    consumable = resp.json()
    await state.update_data(consumable_id=consumable["id"])
    await state.set_state(ReceiveStates.entering_pieces)
    await message.answer(
        f"«{name}» добавлен.\nСколько пачек (штук) пришло?",
        reply_markup=receive_keyboard(unit if pack_size else None),
    )


@router.callback_query(F.data.startswith("kind:"), ReceiveStates.choosing_new_kind)
async def receive_kind_chosen(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    kind = callback.data.split(":")[1]
    data = await state.get_data()
    await callback.answer()

    if kind == "pieces":
        await create_and_continue(callback.message, state, backend_url, data["new_name"], "шт", None)
        return

    unit = "мл" if kind == "ml" else "г"
    await state.update_data(new_unit=unit)
    await state.set_state(ReceiveStates.entering_pack_size)
    prompt = (
        "Сколько мл в одной пачке? (например, 1000)" if unit == "мл"
        else "Вес содержимого одной пачки (нетто), г? Без упаковки, например 1000"
    )
    await callback.message.answer(prompt, reply_markup=cancel_keyboard())


@router.message(ReceiveStates.entering_pack_size)
async def receive_pack_size_entered(message: types.Message, state: FSMContext, backend_url: str):
    pack_size = parse_number(message.text)
    if pack_size is None:
        await message.answer("Введи число больше нуля, например: 1000")
        return
    data = await state.get_data()
    await create_and_continue(message, state, backend_url, data["new_name"], data["new_unit"], pack_size)


@router.callback_query(F.data.startswith("receive:"), ReceiveStates.choosing_consumable)
async def receive_choose(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    consumable_id = int(callback.data.split(":")[1])
    consumable = await find_consumable(backend_url, consumable_id)
    if consumable is None:
        await callback.answer("Расходник не найден", show_alert=True)
        return

    await close_list(callback, f"Выбрано: «{consumable['name']}»")
    await state.update_data(consumable_id=consumable_id)
    await state.set_state(ReceiveStates.entering_pieces)
    await callback.message.answer(
        receive_prompt(consumable),
        reply_markup=receive_keyboard(consumable["unit"] if consumable.get("pack_size") else None),
    )
    await callback.answer()


@router.callback_query(F.data == "rcv:net", ReceiveStates.entering_pieces)
async def receive_net_edit(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    data = await state.get_data()
    consumable = await find_consumable(backend_url, data["consumable_id"])
    if consumable is None or not consumable.get("pack_size"):
        await callback.answer("Нетто задаётся только для позиций в мл или г", show_alert=True)
        return

    await state.set_state(ReceiveStates.entering_new_net)
    await callback.message.answer(
        f"Новый вес нетто одной пачки, {consumable['unit']}? (сейчас {num(consumable['pack_size'])})",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ReceiveStates.entering_new_net)
async def receive_net_entered(message: types.Message, state: FSMContext, backend_url: str):
    net = parse_number(message.text)
    if net is None:
        await message.answer("Введи число больше нуля, например: 1015")
        return

    data = await state.get_data()
    updated = await update_consumable(backend_url, data["consumable_id"], pack_size=net)
    if updated is None:
        await message.answer("Не удалось сохранить. Попробуй ещё раз.")
        return

    await state.set_state(ReceiveStates.entering_pieces)
    await message.answer(
        "Нетто обновлено.\n" + receive_prompt(updated),
        reply_markup=receive_keyboard(updated["unit"]),
    )


@router.message(ReceiveStates.entering_pieces)
async def receive_pieces_entered(message: types.Message, state: FSMContext, backend_url: str):
    pieces = parse_number(message.text)
    if pieces is None:
        await message.answer("Введи число больше нуля, например: 2")
        return

    data = await state.get_data()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/receive", json={
            "consumable_id": data["consumable_id"],
            "pieces": pieces,
            "telegram_id": message.from_user.id,
        })

    await state.clear()
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        return

    result = resp.json()
    await message.answer(f"Приход зафиксирован ✅\n«{result['name']}»: теперь {fmt_stock(result)}")


# ---------------- Списание ----------------

@router.message(F.text == "➖ Списать")
@router.message(Command("use"))
async def use_start(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    if not await require_staff(backend_url, message.from_user.id):
        await message.answer(NO_ACCESS)
        return

    if not await fetch_consumables(backend_url):
        await message.answer("Расходников пока нет.")
        return

    await state.set_state(UseStates.choosing_consumable)
    await start_picker(bot, message.chat.id, state, backend_url)


@router.callback_query(F.data.startswith("use:"), UseStates.choosing_consumable)
async def use_choose(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    consumable_id = int(callback.data.split(":")[1])
    consumable = await find_consumable(backend_url, consumable_id)
    if consumable is None:
        await callback.answer("Расходник не найден", show_alert=True)
        return

    await close_list(callback, f"Выбрано: «{consumable['name']}»")
    await state.update_data(consumable_id=consumable_id, unit=consumable["unit"])
    header = f"Остаток {fmt_stock(consumable)}"

    if consumable.get("pack_size"):
        await state.set_state(UseStates.choosing_mode)
        await callback.message.answer(
            f"{header}\nВ чём списываем?", reply_markup=mode_keyboard(consumable["unit"])
        )
    else:
        await state.update_data(mode="base")
        await state.set_state(UseStates.entering_amount)
        await callback.message.answer(
            f"{header}\nСколько списать, {consumable['unit']}?", reply_markup=cancel_keyboard()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("qmode:"), UseStates.choosing_mode)
async def use_mode_chosen(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    data = await state.get_data()
    label = "штук" if mode == "pieces" else data["unit"]
    await state.update_data(mode=mode)
    await state.set_state(UseStates.entering_amount)
    await callback.message.answer(f"Сколько списать, {label}?", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(UseStates.entering_amount)
async def use_amount_entered(message: types.Message, state: FSMContext, backend_url: str):
    amount = parse_number(message.text)
    if amount is None:
        await message.answer("Введи число больше нуля, например: 1 или 0.5")
        return

    data = await state.get_data()
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{backend_url}/inventory/use", json={
            "consumable_id": data["consumable_id"],
            "amount": amount,
            "mode": data["mode"],
            "telegram_id": message.from_user.id,
        })

    await state.clear()
    if resp.status_code == 400:
        await message.answer("Недостаточно остатка для такого списания.")
        return
    if resp.status_code != 200:
        await message.answer(f"Ошибка backend: {resp.status_code}")
        return

    result = resp.json()
    text = f"Списано ✅ Остаток «{result['name']}»: {fmt_stock(result)}"
    if result["low_stock"]:
        text += "\n⚠️ Остаток ниже порога — пора закупить!"
    await message.answer(text)


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()
