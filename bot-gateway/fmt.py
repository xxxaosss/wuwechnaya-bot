def num(x) -> str:
    """12.0 -> '12', 2.5 -> '2.5', 0.6667 -> '0.67'"""
    return f"{float(x):.2f}".rstrip("0").rstrip(".")


def fmt_stock(c: dict) -> str:
    """'0.85 шт (850 мл)' для позиций с объёмом, '3 шт' для остальных."""
    if c.get("pack_size"):
        return f"{num(c['pieces'])} шт ({num(c['quantity'])} {c['unit']})"
    return f"{num(c['quantity'])} {c['unit']}"


def parse_number(text, allow_zero: bool = False):
    """Число из текста пользователя (запятая или точка). None, если не число."""
    try:
        value = float(text.replace(",", ".").replace(" ", "").replace("\u00a0", ""))
    except (ValueError, AttributeError):
        return None
    if value < 0 or (value == 0 and not allow_zero):
        return None
    return value
