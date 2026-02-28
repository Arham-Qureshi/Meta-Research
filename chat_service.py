"""
chat_service.py – AI Chat Service for Meta Research
====================================================

Uses Google Gemini (gemini-2.0-flash) to power the "Chat with Paper" feature.
The gemini-2.0-flash model is 100% FREE to use – no billing required.

Setup:
    Set the environment variable GEMINI_API_KEY with your free API key from
    https://aistudio.google.com/app/apikey
"""

import os

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY = os.environ.get('GEMINI_API_KEY', '')
MODEL_NAME = 'gemini-2.0-flash'

if GENAI_AVAILABLE and API_KEY:
    genai.configure(api_key=API_KEY)


def _get_model():
    """Return a configured Gemini GenerativeModel or None."""
    if not GENAI_AVAILABLE:
        return None
    if not API_KEY:
        return None
    return genai.GenerativeModel(MODEL_NAME)


# ---------------------------------------------------------------------------
# Build paper context string
# ---------------------------------------------------------------------------

def _build_paper_context(paper: dict) -> str:
    """Build a readable context string from paper metadata."""
    parts = []
    if paper.get('title'):
        parts.append(f"Title: {paper['title']}")
    if paper.get('authors'):
        parts.append(f"Authors: {paper['authors']}")
    if paper.get('published'):
        parts.append(f"Published: {paper['published']}")
    if paper.get('categories'):
        cats = paper['categories']
        if isinstance(cats, list):
            cats = ', '.join(cats)
        parts.append(f"Categories: {cats}")
    # Use the full summary/abstract
    abstract = paper.get('full_summary') or paper.get('summary') or ''
    if abstract:
        parts.append(f"Abstract:\n{abstract}")
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Chat with Paper
# ---------------------------------------------------------------------------

def chat_with_paper(paper: dict, user_message: str) -> dict:
    """
    Send a user question about a paper to Gemini and return the AI response.

    Args:
        paper: Dict with paper metadata (title, authors, summary, etc.)
        user_message: The user's question.

    Returns:
        {'reply': str, 'error': str|None}
    """
    model = _get_model()
    if model is None:
        if not GENAI_AVAILABLE:
            return {
                'reply': '',
                'error': 'The google-generativeai package is not installed. '
                         'Run: pip install google-generativeai'
            }
        return {
            'reply': '',
            'error': 'GEMINI_API_KEY environment variable is not set. '
                     'Get a free key at https://aistudio.google.com/app/apikey'
        }

    context = _build_paper_context(paper)

    prompt = f"""You are a helpful research assistant. The user is reading an academic paper and has a question about it. Answer clearly and accurately based on the paper's information. If you cannot determine the answer from the provided abstract, say so honestly and offer your best insight.

--- PAPER ---
{context}
--- END PAPER ---

User's question: {user_message}

Provide a clear, well-structured answer. Use bullet points or numbered lists where helpful. Keep the tone informative but accessible."""

    try:
        response = model.generate_content(prompt)
        return {'reply': response.text, 'error': None}
    except Exception as e:
        return {'reply': '', 'error': f'AI request failed: {str(e)}'}


# ---------------------------------------------------------------------------
# Summarize Paper (comprehensive summary + use cases)
# ---------------------------------------------------------------------------

def summarize_paper(paper: dict) -> dict:
    """
    Generate a comprehensive summary of a paper including key findings,
    methodology, and practical use cases.

    Args:
        paper: Dict with paper metadata.

    Returns:
        {'summary': str, 'error': str|None}
    """
    model = _get_model()
    if model is None:
        if not GENAI_AVAILABLE:
            return {
                'summary': '',
                'error': 'The google-generativeai package is not installed. '
                         'Run: pip install google-generativeai'
            }
        return {
            'summary': '',
            'error': 'GEMINI_API_KEY environment variable is not set. '
                     'Get a free key at https://aistudio.google.com/app/apikey'
        }

    context = _build_paper_context(paper)

    prompt = f"""You are an expert research analyst. Given the following academic paper, provide a comprehensive and insightful summary. Structure your response as follows:

## Overview
A clear, accessible explanation of what this paper is about (2-3 sentences).

## Key Contributions
The main findings, contributions, or innovations of this paper.

## Methodology
How the authors approached the problem (techniques, datasets, experiments).

## Results & Impact
Key results, performance metrics, and their significance.

## Practical Use Cases
Real-world applications and scenarios where this research could be applied. Who would benefit from this work? How could it be used in industry or further research?

## Limitations
Any noted limitations or areas for future work.

--- PAPER ---
{context}
--- END PAPER ---

Provide a thorough, well-organized summary. Use markdown formatting. Be informative but keep it accessible to someone who hasn't read the full paper."""

    try:
        response = model.generate_content(prompt)
        return {'summary': response.text, 'error': None}
    except Exception as e:
        return {'summary': '', 'error': f'AI request failed: {str(e)}'}
