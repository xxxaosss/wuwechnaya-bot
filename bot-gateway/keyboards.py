from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def consumables_keyboard(consumables: list[dict], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in consumables:
        builder.button(
            text=f"{c['name']} ({c['quantity']} {c['unit']})",
            callback_data=f"{action}:{c['id']}"
        )
    if action == "receive":
        builder.button(text="➕ Новый расходник", callback_data="receive:new")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()
