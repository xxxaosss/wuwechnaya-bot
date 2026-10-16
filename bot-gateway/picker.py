"""Общий выбор расходника с поиском и страницами для «Приход», «Списать», «Провести работу».

Состояние (FSM data): pick_query, pick_page, list_msg_id.
Какой режим — определяется по текущему состоянию пользователя.
"""
from aiogram import Bot, Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from api import fetch_consumables
from keyboards import pick_keyboard
from search import filter_consumables, paginate
from states import ReceiveStates, UseStates, WorkLogStates

router = Router()

PICK_STATES = (
    ReceiveStates.choosing_consumable,
    UseStates.choosing_consumable,
    WorkLogStates.choosing_consumables,
)


async def show_picker(bot: Bot, chat_id: int, state: FSMContext, backend_url: str,
                      message_id: int | None = None):
    """Рисует список для текущего состояния; если есть message_id — обновляет сообщение на месте."""
    data = await state.get_data()
    current = await state.get_state()
    consumables = await fetch_consumables(backend_url)

    query = data.get("pick_query", "")
    found = filter_consumables(consumables, query)
    items, page, pages = paginate(found, data.get("pick_page", 0))
    await state.update_data(pick_page=page)

    selected = None
    with_new = False
    if current == WorkLogStates.choosing_consumables.state:
        action = "toggle"
        selected = data.get("selected_consumables", [])
        title = f"Услуга: {data.get('service_name', '')}\nОтметь использованные расходники"
    elif current == UseStates.choosing_consumable.state:
        action = "use"
        title = "Какой расходник списать?"
    else:
        action = "receive"
        with_new = True
        title = "Выбери расходник для прихода или добавь новый"

    if query:
        info = f"🔎 «{query}»: найдено {len(found)} из {len(consumables)}"
        if not found:
            info += "\nНичего не найдено — попробуй другие слова или сбрось поиск."
    else:
        info = f"Всего позиций: {len(consumables)}. Чтобы найти нужную, напиши часть названия."

    text = f"{title}\n\n{info}"
    if selected:
        chosen = [c["name"] for c in consumables if c["id"] in selected]
        shown = ", ".join(chosen[:10]) + ("…" if len(chosen) > 10 else "")
        text += f"\n\n✅ Выбрано ({len(chosen)}): {shown}"

    markup = pick_keyboard(items, action, page, pages, query, selected, with_new)

    if message_id is not None:
        try:
            await bot.edit_message_text(text=text, chat_id=chat_id, message_id=message_id,
                                        reply_markup=markup)
            await state.update_data(list_msg_id=message_id)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            # сообщение не найдено/устарело — отправим новое

    sent = await bot.send_message(chat_id, text, reply_markup=markup)
    await state.update_data(list_msg_id=sent.message_id)


async def start_picker(bot: Bot, chat_id: int, state: FSMContext, backend_url: str):
    """Начало выбора: сбрасывает поиск и показывает первую страницу."""
    await state.update_data(pick_query="", pick_page=0, list_msg_id=None)
    await show_picker(bot, chat_id, state, backend_url)


async def close_list(callback: types.CallbackQuery, text: str):
    """Заменяет список коротким итогом и убирает кнопки."""
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("page:"), StateFilter(*PICK_STATES))
async def pick_page(callback: types.CallbackQuery, state: FSMContext, bot: Bot, backend_url: str):
    await state.update_data(pick_page=int(callback.data.split(":")[1]))
    await show_picker(bot, callback.message.chat.id, state, backend_url,
                      message_id=callback.message.message_id)
    await callback.answer()


@router.callback_query(F.data == "search:reset", StateFilter(*PICK_STATES))
async def pick_reset(callback: types.CallbackQuery, state: FSMContext, bot: Bot, backend_url: str):
    await state.update_data(pick_query="", pick_page=0)
    await show_picker(bot, callback.message.chat.id, state, backend_url,
                      message_id=callback.message.message_id)
    await callback.answer()


@router.message(StateFilter(*PICK_STATES), F.text, ~F.text.startswith("/"))
async def pick_search(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    data = await state.get_data()
    await state.update_data(pick_query=message.text.strip(), pick_page=0)
    await show_picker(bot, message.chat.id, state, backend_url, message_id=data.get("list_msg_id"))
    try:  # убираем введённый запрос из чата, чтобы список оставался чистым
        await message.delete()
    except TelegramBadRequest:
        pass
