import os
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

ADMIN_TELEGRAM_ID = int(os.environ["ADMIN_TELEGRAM_ID"])


def staff_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Остатки")
    builder.button(text="➕ Приход")
    builder.button(text="➖ Списать")
    builder.button(text="💼 Провести работу")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📦 Остатки")
    builder.button(text="➕ Приход")
    builder.button(text="➖ Списать")
    builder.button(text="💼 Провести работу")
    builder.button(text="📥 Импорт накладной")
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def pending_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="ℹ️ Статус заявки")
    return builder.as_markup(resize_keyboard=True)


def menu_for(role: str, telegram_id: int) -> ReplyKeyboardMarkup:
    if role == "admin" or telegram_id == ADMIN_TELEGRAM_ID:
        return admin_menu()
    if role == "master":
        return staff_menu()
    return pending_menu()
