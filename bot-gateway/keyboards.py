from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from fmt import fmt_stock


def consumables_keyboard(consumables: list[dict], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in consumables:
        builder.button(text=f"{c['name']} — {fmt_stock(c)}", callback_data=f"{action}:{c['id']}")
    if action == "receive":
        builder.button(text="➕ Новый расходник", callback_data="receive:new")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel")
    return builder.as_markup()


def kind_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Только штуки", callback_data="kind:pieces")
    builder.button(text="💧 Штуки + объём (мл)", callback_data="kind:ml")
    builder.button(text="⚖️ Штуки + вес (г)", callback_data="kind:g")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def mode_keyboard(unit: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="В штуках", callback_data="qmode:pieces")
    builder.button(text=f"В {unit}", callback_data="qmode:base")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2, 1)
    return builder.as_markup()


def services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(text=f"{s['name']} — {s['price']}₽", callback_data=f"service:{s['id']}")
    builder.button(text="➕ Новая услуга", callback_data="service:new")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def consumables_multiselect_keyboard(consumables: list[dict], selected: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in consumables:
        mark = "✅ " if c["id"] in selected else "⬜ "
        builder.button(text=f"{mark}{c['name']} ({fmt_stock(c)})", callback_data=f"toggle:{c['id']}")
    builder.button(text="Без расходников", callback_data="consumables:none")
    builder.button(text="✅ Готово", callback_data="consumables:done")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def confirm_import_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Загрузить", callback_data="import:confirm")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()
