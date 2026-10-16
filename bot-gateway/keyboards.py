from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from fmt import fmt_stock


def pick_keyboard(items: list[dict], action: str, page: int, pages: int, query: str = "",
                  selected: list | None = None, with_new: bool = False) -> InlineKeyboardMarkup:
    """items — позиции текущей страницы.
    action: 'receive' / 'use' — одиночный выбор, 'toggle' — мультивыбор (selected не None)."""
    builder = InlineKeyboardBuilder()
    multi = selected is not None

    for c in items:
        mark = ("✅ " if c["id"] in selected else "⬜ ") if multi else ""
        builder.button(text=f"{mark}{c['name']} — {fmt_stock(c)}", callback_data=f"{action}:{c['id']}")
    sizes = [1] * len(items)

    if pages > 1:
        builder.button(text="◀", callback_data=f"page:{page - 1}" if page > 0 else "noop")
        builder.button(text=f"{page + 1}/{pages}", callback_data="noop")
        builder.button(text="▶", callback_data=f"page:{page + 1}" if page < pages - 1 else "noop")
        sizes.append(3)

    if query:
        builder.button(text="🔄 Сбросить поиск", callback_data="search:reset")
        sizes.append(1)
    if with_new:
        builder.button(text="➕ Новый расходник", callback_data="receive:new")
        sizes.append(1)
    if multi:
        builder.button(text="Без расходников", callback_data="consumables:none")
        builder.button(text=f"✅ Готово ({len(selected)})", callback_data="consumables:done")
        sizes.append(2)

    builder.button(text="❌ Отмена", callback_data="cancel")
    sizes.append(1)
    builder.adjust(*sizes)
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


def confirm_import_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Загрузить", callback_data="import:confirm")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)
    return builder.as_markup()
