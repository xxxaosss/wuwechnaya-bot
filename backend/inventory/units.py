from decimal import Decimal

TWO = Decimal("0.01")


def to_base(consumable, amount: Decimal, mode: str) -> Decimal:
    """Перевод введённого количества в базовые единицы (мл/г/шт).
    mode="pieces" — amount в пачках (штуках), mode="base" — уже в мл/г/шт."""
    if mode == "pieces" and consumable.pack_size:
        return amount * consumable.pack_size
    return amount


def receive_amount(consumable, amount: Decimal, mode: str) -> Decimal:
    """Приход. Возвращает прибавку в базовых единицах.
    mode: 'pieces' — пачек; 'base' — мл/г/шт содержимого;
          'gross' — вес на весах вместе с упаковкой (только для г, нужна тара)."""
    if mode == "pieces":
        added = amount * (consumable.pack_size or Decimal(1))
    elif mode == "base":
        added = amount
    elif mode == "gross":
        if consumable.unit != "г" or consumable.tare is None:
            raise ValueError("tare is not set")
        added = amount - consumable.tare
        if added <= 0:
            raise ValueError("weight is not greater than tare")
    else:
        raise ValueError("unknown mode")
    consumable.quantity += added
    return added


def apply_receive(consumable, pieces: Decimal) -> Decimal:
    """Приход в пачках (для импорта)."""
    return receive_amount(consumable, pieces, "pieces")


def reconfigure(consumable, unit: str, pack_size: Decimal | None):
    """Меняет способ учёта (шт / мл / г) и нетто одной пачки.
    Число пачек сохраняется: остаток и порог пересчитываются под новое нетто.
    Тара имеет смысл только в граммах, при другом учёте она сбрасывается."""
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
    if unit != "г":
        consumable.tare = None
