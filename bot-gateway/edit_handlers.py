from aiogram import Bot, Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from states import EditStates
from keyboards import cancel_keyboard, edit_menu_keyboard, UNIT_BY_KIND
from auth_helper import require_admin
from api import find_consumable, update_consumable
from picker import start_picker, close_list
from fmt import fmt_stock, fmt_config, num, parse_number

router = Router()


async def show_menu(bot: Bot, chat_id: int, state: FSMContext, backend_url: str):
    """Показывает меню настроек расходника (старое меню теряет кнопки)."""
    data = await state.get_data()
    c = await find_consumable(backend_url, data["edit_id"])
    if c is None:
        await bot.send_message(chat_id, "Расходник не найден.")
        await state.clear()
        return

    old = data.get("menu_msg_id")
    if old:
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=old, reply_markup=None)
        except TelegramBadRequest:
            pass

    text = f"«{c['name']}»\nОстаток: {fmt_stock(c)}\n{fmt_config(c)}"
    sent = await bot.send_message(chat_id, text, reply_markup=edit_menu_keyboard(c))
    await state.update_data(menu_msg_id=sent.message_id)
    await state.set_state(EditStates.menu)


@router.message(F.text == "✏️ Расходник")
async def edit_start(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    if not await require_admin(backend_url, message.from_user.id):
        await message.answer("Настройка расходников доступна только администратору.")
        return
    await state.set_state(EditStates.choosing_consumable)
    await start_picker(bot, message.chat.id, state, backend_url)


@router.callback_query(F.data.startswith("edit:"), EditStates.choosing_consumable)
async def edit_choose(callback: types.CallbackQuery, state: FSMContext, bot: Bot, backend_url: str):
    consumable_id = int(callback.data.split(":")[1])
    c = await find_consumable(backend_url, consumable_id)
    if c is None:
        await callback.answer("Расходник не найден", show_alert=True)
        return

    await close_list(callback, f"Выбрано: «{c['name']}»")
    await state.update_data(edit_id=consumable_id, menu_msg_id=None)
    await show_menu(bot, callback.message.chat.id, state, backend_url)
    await callback.answer()


# ---- способ учёта ----

@router.callback_query(F.data.startswith("ekind:"), EditStates.menu)
async def edit_kind(callback: types.CallbackQuery, state: FSMContext, bot: Bot, backend_url: str):
    unit = UNIT_BY_KIND[callback.data.split(":")[1]]
    data = await state.get_data()
    await callback.answer()

    if unit == "шт":
        if await update_consumable(backend_url, data["edit_id"], unit="шт") is None:
            await callback.message.answer("Не удалось сохранить.")
            return
        await show_menu(bot, callback.message.chat.id, state, backend_url)
        return

    c = await find_consumable(backend_url, data["edit_id"])
    current = f" (сейчас {num(c['pack_size'])} {c['unit']})" if c and c.get("pack_size") else ""
    what = "Объём одной пачки" if unit == "мл" else "Вес нетто одной пачки (содержимое без упаковки)"
    await state.update_data(edit_unit=unit)
    await state.set_state(EditStates.entering_kind_pack)
    await callback.message.answer(f"{what}, {unit}?{current}", reply_markup=cancel_keyboard())


@router.message(EditStates.entering_kind_pack)
async def edit_kind_pack_entered(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    pack = parse_number(message.text)
    if pack is None:
        await message.answer("Введи число больше нуля, например: 1000")
        return
    data = await state.get_data()
    updated = await update_consumable(backend_url, data["edit_id"], unit=data["edit_unit"], pack_size=pack)
    if updated is None:
        await message.answer("Не удалось сохранить. Проверь значение.")
        return
    await show_menu(bot, message.chat.id, state, backend_url)


# ---- нетто пачки ----

@router.callback_query(F.data == "ecfg:net", EditStates.menu)
async def edit_net(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    data = await state.get_data()
    c = await find_consumable(backend_url, data["edit_id"])
    if c is None or not c.get("pack_size"):
        await callback.answer("Сначала выбери учёт в мл или г", show_alert=True)
        return
    await state.set_state(EditStates.entering_net)
    await callback.message.answer(
        f"Новый вес нетто одной пачки, {c['unit']}? (сейчас {num(c['pack_size'])})",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(EditStates.entering_net)
async def edit_net_entered(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    net = parse_number(message.text)
    if net is None:
        await message.answer("Введи число больше нуля, например: 1015")
        return
    data = await state.get_data()
    if await update_consumable(backend_url, data["edit_id"], pack_size=net) is None:
        await message.answer("Не удалось сохранить.")
        return
    await show_menu(bot, message.chat.id, state, backend_url)


# ---- порог ----

@router.callback_query(F.data == "ecfg:thr", EditStates.menu)
async def edit_threshold(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    data = await state.get_data()
    c = await find_consumable(backend_url, data["edit_id"])
    word = "пачек" if c and c.get("pack_size") else "штук"
    await state.set_state(EditStates.entering_threshold)
    await callback.message.answer(
        f"Сколько {word} должно остаться, чтобы бот предупредил о закупке? "
        "(0 — только когда закончится)",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(EditStates.entering_threshold)
async def edit_threshold_entered(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    value = parse_number(message.text, allow_zero=True)
    if value is None:
        await message.answer("Введи число, например: 1 или 0.5")
        return
    data = await state.get_data()
    if await update_consumable(backend_url, data["edit_id"], threshold_packs=value) is None:
        await message.answer("Не удалось сохранить.")
        return
    await show_menu(bot, message.chat.id, state, backend_url)


@router.callback_query(F.data == "ecfg:done", EditStates.menu)
async def edit_done(callback: types.CallbackQuery, state: FSMContext):
    await close_list(callback, "Настройки сохранены ✅")
    await state.clear()
    await callback.answer()
