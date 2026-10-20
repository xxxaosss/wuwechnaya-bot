import csv
import io
import httpx
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from states import ImportStates
from keyboards import cancel_keyboard, confirm_import_keyboard
from auth_helper import require_admin
from api import fetch_consumables
from fmt import num, fmt_stock

router = Router()

HELP = (
    "Пришли CSV-файл (разделитель «;», кодировка UTF-8) в таком формате:\n\n"
    "Название;Штук;Объём;Ед;Вес, г\n"
    "Шампунь 1000 мл;2;1000;мл;\n"
    "Краска 60 мл;3;60;мл;62\n"
    "Перчатки;10;;;\n\n"
    "• Название и Штук — обязательные (Штук можно 0, чтобы только завести позицию)\n"
    "• Объём — сколько мл/г в одной пачке (пусто — учёт только в штуках)\n"
    "• Ед — мл или г\n"
    "• Вес, г — нетто одной пачки. Если указан, позиция считается в граммах по этому весу, "
    "а у уже существующей позиции учёт переключится на граммы (число пачек сохранится)\n"
    "• Позиции ищутся по названию: если такая уже есть, пачки добавятся к остатку"
)

ALIASES = {
    "name": {"name", "название", "наименование", "позиция"},
    "pieces": {"pieces", "штук", "шт", "количество", "кол-во"},
    "volume": {"volume", "объем", "объём", "pack_size"},
    "unit": {"unit", "ед", "ед.", "единица"},
    "weight": {"weight", "вес, г", "вес,г", "вес г", "вес", "нетто", "нетто, г"},
}


def canon(header: str):
    h = header.strip().lower()
    for field, names in ALIASES.items():
        if h in names:
            return field
    return None


def to_float(value):
    if value is None:
        return None
    value = value.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_csv(raw: bytes):
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
    if not rows:
        return [], ["файл пустой"]

    header = {canon(k) for k in rows[0].keys() if k}
    if not {"name", "pieces"} <= header:
        return [], ["в первой строке нужны колонки «Название» и «Штук» (разделитель «;»)"]

    lines, errors = [], []
    for i, raw_row in enumerate(rows, start=2):
        row = {}
        for k, v in raw_row.items():
            field = canon(k) if k else None
            if field:
                row[field] = (v or "").strip()
        if not any(row.values()):
            continue

        name = row.get("name", "")
        pieces = to_float(row.get("pieces"))
        if not name or pieces is None or pieces < 0:
            errors.append(f"строка {i}: нужны Название и Штук (0 или больше)")
            continue

        volume = to_float(row.get("volume"))
        unit = row.get("unit", "").lower() or None
        if unit and unit not in {"мл", "г", "шт"}:
            errors.append(f"строка {i}: «Ед» — только мл или г")
            continue
        if volume is not None and volume <= 0:
            errors.append(f"строка {i}: Объём должен быть больше нуля")
            continue

        raw_weight = row.get("weight", "")
        weight = to_float(raw_weight)
        if raw_weight and (weight is None or weight <= 0):
            errors.append(f"строка {i}: «Вес, г» должен быть числом больше нуля")
            continue

        has_volume = bool(volume) and unit != "шт"
        lines.append({
            "name": name,
            "pieces": pieces,
            "volume": volume if has_volume else None,
            "unit": (unit or "мл") if has_volume else None,
            "weight": weight,
        })

    if not lines and not errors:
        errors.append("в файле нет ни одной позиции")
    return lines, errors


def will_convert(line: dict, ex: dict | None) -> bool:
    return bool(ex and line.get("weight")
                and (ex["unit"] != "г" or (ex.get("pack_size") or None) != line["weight"]))


def preview(lines: list[dict], existing: dict) -> str:
    out = []
    for l in lines[:15]:
        ex = existing.get(l["name"].strip().lower())
        if l.get("weight"):
            spec = f" × {num(l['weight'])} г нетто"
        elif l["volume"]:
            spec = f" × {num(l['volume'])} {l['unit']}"
        else:
            spec = ""
        head = f"• {l['name']}: +{num(l['pieces'])} шт{spec}"
        if ex is None:
            out.append(head + " — новая позиция")
            continue

        pieces_after = ex["pieces"] + l["pieces"]
        if l.get("weight"):
            unit_after, pack_after = "г", l["weight"]
            note = " ⚙️ учёт станет: г" if will_convert(l, ex) else ""
        else:
            unit_after, pack_after = ex["unit"], ex.get("pack_size")
            note = ""
            if (ex.get("pack_size") or None) != (l["volume"] or None):
                note = " ⚠️ объём упаковки отличается от базы, возьмётся из базы"
        after = {
            "unit": unit_after, "pack_size": pack_after, "pieces": pieces_after,
            "quantity": pieces_after * (pack_after or 1),
        }
        out.append(f"{head} — было {fmt_stock(ex)}, станет {fmt_stock(after)}{note}")
    if len(lines) > 15:
        out.append(f"… и ещё {len(lines) - 15}")
    return "\n".join(out)


@router.message(F.text == "📥 Импорт накладной")
async def import_start(message: types.Message, state: FSMContext, backend_url: str):
    if not await require_admin(backend_url, message.from_user.id):
        await message.answer("Импорт доступен только администратору.")
        return
    await state.set_state(ImportStates.waiting_file)
    await message.answer(HELP, reply_markup=cancel_keyboard())


@router.message(ImportStates.waiting_file, F.document)
async def import_file(message: types.Message, state: FSMContext, bot: Bot, backend_url: str):
    buf = io.BytesIO()
    await bot.download(message.document, destination=buf)
    try:
        lines, errors = parse_csv(buf.getvalue())
    except UnicodeDecodeError:
        await message.answer("Не удалось прочитать файл: сохрани его в кодировке UTF-8.")
        return

    if errors:
        await message.answer(
            "Нашёл проблемы в файле:\n" + "\n".join(errors[:10]) + "\n\nИсправь и пришли файл снова.",
            reply_markup=cancel_keyboard(),
        )
        return

    existing = {c["name"].strip().lower(): c for c in await fetch_consumables(backend_url)}
    new_count = sum(1 for l in lines if l["name"].strip().lower() not in existing)
    conv_count = sum(1 for l in lines if will_convert(l, existing.get(l["name"].strip().lower())))

    await state.update_data(import_lines=lines)
    await state.set_state(ImportStates.confirming)
    summary = f"Прочитал {len(lines)} поз. (новых: {new_count}"
    summary += f", перейдут на граммы: {conv_count})" if conv_count else ")"
    await message.answer(
        f"{summary}:\n\n{preview(lines, existing)}\n\nЗагружаем?",
        reply_markup=confirm_import_keyboard(),
    )


@router.message(ImportStates.waiting_file)
async def import_wrong_input(message: types.Message):
    await message.answer("Жду файл .csv — пришли его как документ.")


@router.callback_query(F.data == "import:confirm", ImportStates.confirming)
async def import_confirm(callback: types.CallbackQuery, state: FSMContext, backend_url: str):
    data = await state.get_data()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{backend_url}/inventory/import", json={
            "telegram_id": callback.from_user.id,
            "lines": data["import_lines"],
        })

    await state.clear()
    await callback.answer()
    if resp.status_code != 200:
        await callback.message.answer(f"Ошибка backend: {resp.status_code}")
        return

    result = resp.json()
    text = (
        f"Готово ✅ Новых позиций: {result['created']}, "
        f"пополнено существующих: {result['updated']}"
    )
    if result.get("converted"):
        text += f"\nПереведено на граммы: {result['converted']}"
    await callback.message.answer(text)
