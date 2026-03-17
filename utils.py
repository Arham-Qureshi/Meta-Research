import re

def reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index or not isinstance(inverted_index, dict):
        return ''
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return ' '.join(w for _, w in word_positions)

def truncate(text: str, max_len: int = 200) -> str:
    if not text or len(text) <= max_len:
        return text or ''
    return text[:max_len].rsplit(' ', 1)[0] + '…'

def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def extract_year(date_string: str | None) -> int | None:
    if not date_string:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', str(date_string))
    return int(match.group()) if match else None

