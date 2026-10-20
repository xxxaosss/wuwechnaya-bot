from decimal import Decimal

TWO = Decimal("0.01")


def to_base(consumable, amount: Decimal, mode: str) -> Decimal:
    """Перевод введённого количества в базовые единицы (мл/г/шт).
    mode="pieces" — amount в пачках (штуках), mode="base" — уже в мл/г/шт."""
    if mode == "pieces" and consumable.pack_size:
        return amount * consumable.pack_size
    return amount


def apply_receive(consumable, pieces: Decimal) -> Decimal:
    """Приход в пачках: увеличивает остаток, возвращает прибавку в базовых единицах."""
    added = pieces * (consumable.pack_size or Decimal(1))
    consumable.quantity += added
    return added


def reconfigure(consumable, unit: str, pack_size: Decimal | None):
    """Меняет способ учёта (шт / мл / г) и нетто одной пачки.
    Число пачек сохраняется: остаток и порог пересчитываются под новое нетто."""
    old_pack = consumable.pack_size or Decimal(1)
    pieces = consumable.quantity / old_pack
    threshold_packs = consumable.threshold / old_pack

    if unit == "шт":
        pack_size = None
    new_pack = pack_size or Decimal(1)

    consumable.unit = unit
    consumable.pack_size = pack_size
    consumable.quantity = (pieces * new_pack).quantize(TWO)
    consumable.threshold = (threshold_packs * new_pack).quantize(TWO)
