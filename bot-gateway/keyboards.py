from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from fmt import fmt_stock

UNIT_BY_KIND = {"pieces": "шт", "ml": "мл", "g": "г"}


def pick_keyboard(items: list[dict], action: str, page: int, pages: int, query: str = "",
                  selected: list | None = None, with_new: bool = False) -> InlineKeyboardMarkup:
    """items — позиции текущей страницы.
    action: 'receive' / 'use' / 'edit' — одиночный выбор, 'toggle' — мультивыбор (selected не None)."""
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
    builder.button(text="💧 Пачки с объёмом (мл)", callback_data="kind:ml")
    builder.button(text="⚖️ Пачки с весом (г)", callback_data="kind:g")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def receive_keyboard(c: dict | None = None, mode: str = "pieces") -> InlineKeyboardMarkup:
    """Для прихода: переключатель способа ввода и кнопка изменения нетто (для позиций в мл/г)."""
    builder = InlineKeyboardBuilder()
    sizes = []
    if c and c.get("pack_size"):
        unit = c["unit"]
        row = 0
        if mode != "pieces":
            builder.button(text="📦 В пачках", callback_data="rmode:pieces")
            row += 1
        if mode != "base":
            builder.button(text=f"⚖️ В {unit}", callback_data="rmode:base")
            row += 1
        if unit == "г" and c.get("tare") is not None and mode != "gross":
            builder.button(text="🧴 Вес с упаковкой", callback_data="rmode:gross")
            row += 1
        if row:
            sizes.append(row)
        builder.button(text=f"✏️ Изменить нетто ({unit})", callback_data="rcv:net")
        sizes.append(1)
    builder.button(text="❌ Отмена", callback_data="cancel")
    sizes.append(1)
    builder.adjust(*sizes)
    return builder.as_markup()


def edit_menu_keyboard(c: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for kind, unit in UNIT_BY_KIND.items():
        mark = "✅ " if c["unit"] == unit else ""
        builder.button(text=f"{mark}Учёт: {unit}", callback_data=f"ekind:{kind}")
    sizes = [3]

    row = 0
    if c.get("pack_size"):
        builder.button(text="⚖️ Нетто", callback_data="ecfg:net")
        row += 1
    if c["unit"] == "г" and c.get("pack_size"):
        builder.button(text="🧴 Тара", callback_data="ecfg:tare")
        row += 1
    builder.button(text="🔔 Порог", callback_data="ecfg:thr")
    row += 1
    sizes.append(row)

    builder.button(text="✔️ Готово", callback_data="ecfg:done")
    sizes.append(1)
    builder.adjust(*sizes)
    return builder.as_markup()


def tare_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🧴 Взвесил целую пачку", callback_data="etare:full")
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
