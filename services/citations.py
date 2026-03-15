"""
services/citations.py — Citation formatting service.

Converts paper metadata dicts into standard citation formats:
BibTeX, APA 7th, MLA 9th, Chicago 17th, and RIS.
"""

import re
from utils import extract_year, clean_authors


def _first_author_key(authors_str: str) -> str:
    """Extract a clean BibTeX key from the first author's surname."""
    if not authors_str:
        return 'unknown'
    first = authors_str.split(',')[0].strip()
    surname = first.split()[-1] if first else 'unknown'
    return re.sub(r'[^a-zA-Z]', '', surname).lower()


def _bibtex_key(paper: dict) -> str:
    """Generate a unique BibTeX cite key like 'smith2024transformers'."""
    author = _first_author_key(paper.get('authors', ''))
    year = extract_year(paper.get('published')) or 'nd'
    title_word = re.sub(r'[^a-zA-Z]', '', (paper.get('title', '') or '').split()[0]).lower() if paper.get('title') else 'untitled'
    return f'{author}{year}{title_word}'


def to_bibtex(paper: dict) -> str:
    """Format a paper as a BibTeX @article entry."""
    key = _bibtex_key(paper)
    year = extract_year(paper.get('published')) or ''
    fields = [
        f'  title     = {{{paper.get("title", "Untitled")}}}',
        f'  author    = {{{paper.get("authors", "Unknown")}}}',
        f'  year      = {{{year}}}',
    ]
    if paper.get('journal'):
        fields.append(f'  journal   = {{{paper["journal"]}}}')
    if paper.get('pdf_url'):
        fields.append(f'  url       = {{{paper["pdf_url"]}}}')
    elif paper.get('abstract_url'):
        fields.append(f'  url       = {{{paper["abstract_url"]}}}')
    return '@article{' + key + ',\n' + ',\n'.join(fields) + '\n}'


def to_apa(paper: dict) -> str:
    """Format a paper in APA 7th edition style."""
    authors = paper.get('authors', 'Unknown')
    year = extract_year(paper.get('published')) or 'n.d.'
    title = paper.get('title', 'Untitled')
    parts = [f'{authors} ({year}). {title}.']
    if paper.get('journal'):
        parts[0] += f' *{paper["journal"]}*.'
    url = paper.get('pdf_url') or paper.get('abstract_url')
    if url:
        parts.append(url)
    return ' '.join(parts)


def to_mla(paper: dict) -> str:
    """Format a paper in MLA 9th edition style."""
    authors = paper.get('authors', 'Unknown')
    title = paper.get('title', 'Untitled')
    parts = [f'{authors}. "{title}."']
    if paper.get('journal'):
        parts.append(f'*{paper["journal"]}*,')
    year = extract_year(paper.get('published'))
    if year:
        parts.append(f'{year}.')
    url = paper.get('pdf_url') or paper.get('abstract_url')
    if url:
        parts.append(url)
    return ' '.join(parts)


def to_chicago(paper: dict) -> str:
    """Format a paper in Chicago 17th edition style."""
    authors = paper.get('authors', 'Unknown')
    title = paper.get('title', 'Untitled')
    year = extract_year(paper.get('published')) or 'n.d.'
    parts = [f'{authors}. "{title}."']
    if paper.get('journal'):
        parts.append(f'*{paper["journal"]}*')
    parts.append(f'({year}).')
    url = paper.get('pdf_url') or paper.get('abstract_url')
    if url:
        parts.append(url)
    return ' '.join(parts)


FORMAT_MAP = {
    'bibtex': to_bibtex,
    'apa': to_apa,
    'mla': to_mla,
    'chicago': to_chicago,
}


def format_citation(paper: dict, fmt: str) -> str:
    """Format a paper in the given style. Raises ValueError for unknown formats."""
    formatter = FORMAT_MAP.get(fmt)
    if not formatter:
        raise ValueError(f'Unknown format: {fmt}. Supported: {", ".join(FORMAT_MAP)}')
    return formatter(paper)


def bulk_bibtex(papers: list[dict]) -> str:
    """Concatenate multiple papers as a BibTeX file."""
    return '\n\n'.join(to_bibtex(p) for p in papers)
