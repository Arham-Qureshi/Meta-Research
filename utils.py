"""
utils.py — Shared utility functions.

Text processing, formatting, and type-safe helpers used across
services, providers, and routes.  Import from here — never duplicate.
"""

import re


def reconstruct_abstract(inverted_index: dict) -> str:
    """
    Convert OpenAlex's inverted-index abstract format into plain text.

    OpenAlex stores abstracts as { "word": [position_indexes] }.
    This function reassembles them into a readable string.

    Reused by:
        - services/providers/openalex.py
        - citation_graph/providers/openalex.py
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return ''
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return ' '.join(w for _, w in word_positions)


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis, respecting word boundaries."""
    if not text or len(text) <= max_len:
        return text or ''
    return text[:max_len].rsplit(' ', 1)[0] + '…'


def safe_int(value, default: int = 0) -> int:
    """Parse an integer safely, returning *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def extract_year(date_string: str | None) -> int | None:
    """
    Extract a 4-digit year from a date string.

    Handles formats like '2024-01-15', '2024', 'January 2024', etc.
    Returns None if no year can be found.
    """
    if not date_string:
        return None
    match = re.search(r'\b(19|20)\d{2}\b', str(date_string))
    return int(match.group()) if match else None


def clean_authors(authors_raw, max_authors: int = 3) -> str:
    """
    Normalise author data into a clean comma-separated string.

    Accepts:
        - A string ('Alice, Bob')
        - A list of strings (['Alice', 'Bob'])
        - A list of dicts ([{'name': 'Alice'}, {'name': 'Bob'}])
    """
    if not authors_raw:
        return ''
    if isinstance(authors_raw, str):
        return authors_raw
    if isinstance(authors_raw, list):
        names = []
        for a in authors_raw[:max_authors]:
            if isinstance(a, dict):
                names.append(a.get('name', a.get('display_name', '')))
            elif isinstance(a, str):
                names.append(a)
        result = ', '.join(n for n in names if n)
        if len(authors_raw) > max_authors:
            result += f' et al.'
        return result
    return str(authors_raw)
