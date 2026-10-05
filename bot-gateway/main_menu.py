from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def staff_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Остатки")
    builder.button(text="➕ Приход")
    builder.button(text="➖ Списать")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def pending_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="ℹ️ Статус заявки")
    return builder.as_markup(resize_keyboard=True)
