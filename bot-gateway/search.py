import unicodedata

PAGE_SIZE = 8


def normalize(text: str) -> str:
    """Нижний регистр без диакритики: 'Équisebo' -> 'equisebo', 'ё' -> 'е'."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def filter_consumables(consumables: list[dict], query: str) -> list[dict]:
    """В названии должны встретиться все слова запроса (в любом порядке)."""
    words = normalize(query).split()
    if not words:
        return consumables
    return [c for c in consumables if all(w in normalize(c["name"]) for w in words)]


def paginate(items: list, page: int):
    """Возвращает (элементы страницы, номер страницы, всего страниц)."""
    pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    start = page * PAGE_SIZE
    return items[start:start + PAGE_SIZE], page, pages
