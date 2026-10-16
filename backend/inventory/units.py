from decimal import Decimal


def to_base(consumable, amount: Decimal, mode: str) -> Decimal:
    """Перевод введённого количества в базовые единицы (мл/г/шт).
    mode="pieces" — amount в штуках, mode="base" — уже в мл/г/шт."""
    if mode == "pieces" and consumable.pack_size:
        return amount * consumable.pack_size
    return amount


def apply_receive(consumable, pieces: Decimal) -> Decimal:
    """Приход в штуках: увеличивает остаток, возвращает прибавку в базовых единицах."""
    added = pieces * (consumable.pack_size or Decimal(1))
    consumable.quantity += added
    return added
