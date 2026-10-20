def num(x) -> str:
    """12.0 -> '12', 2.5 -> '2.5', 0.6667 -> '0.67'"""
    return f"{float(x):.2f}".rstrip("0").rstrip(".")


def fmt_stock(c: dict) -> str:
    """'0.85 шт (850 г)' для позиций с нетто, '3 шт' для остальных."""
    if c.get("pack_size"):
        return f"{num(c['pieces'])} шт ({num(c['quantity'])} {c['unit']})"
    return f"{num(c['quantity'])} {c['unit']}"


def fmt_config(c: dict) -> str:
    """'Учёт: г, в пачке 1015 г (нетто), тара 60 г, порог: 1 пач.'"""
    if c.get("pack_size"):
        pack = f"в пачке {num(c['pack_size'])} {c['unit']} (нетто)"
        if c["unit"] == "г":
            if c.get("tare") is not None:
                pack += f", тара {num(c['tare'])} г"
            else:
                pack += ", тара не задана"
        word = "пач."
    else:
        pack = "считается в штуках"
        word = "шт"
    thr = f"порог: {num(c['threshold_packs'])} {word}" if c.get("threshold") else "порог не задан"
    return f"Учёт: {c['unit']}, {pack}, {thr}"


def parse_number(text, allow_zero: bool = False):
    """Число из текста пользователя (запятая или точка). None, если не число."""
    try:
        value = float(text.replace(",", ".").replace(" ", "").replace("\u00a0", ""))
    except (ValueError, AttributeError):
        return None
    if value < 0 or (value == 0 and not allow_zero):
        return None
    return value
