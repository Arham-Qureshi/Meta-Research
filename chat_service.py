"""
chat_service.py – AI Chat Service for Meta Research
====================================================

Uses two AI backends:
  - Google Gemini (gemini-2.0-flash) for paper SUMMARIZATION.
  - Groq (llama-3.3-70b-versatile) for the "Chat with Paper" Q&A feature.

Setup:
    GEMINI_API_KEY – free key from https://aistudio.google.com/app/apikey
    GROQ_API_KEY   – free key from https://console.groq.com
"""

import os

# Local pre-summarization (token optimization)
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Gemini (for summarization)
API_KEY = os.environ.get('GEMINI_API_KEY', '')
MODEL_NAME = 'gemini-2.0-flash'

if GENAI_AVAILABLE and API_KEY:
    genai.configure(api_key=API_KEY)

# Groq (for chat with paper)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = 'llama-3.3-70b-versatile'
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_AVAILABLE and GROQ_API_KEY else None


def _get_model():
    """Return a configured Gemini GenerativeModel or None."""
    if not GENAI_AVAILABLE:
        return None
    if not API_KEY:
        return None
    return genai.GenerativeModel(MODEL_NAME)


# ---------------------------------------------------------------------------
# Local Pre-Summarization (Token Optimization)
# ---------------------------------------------------------------------------

def _local_presummarize(text: str, sentence_count: int = 6) -> str:
    """
    Use sumy's LSA algorithm to extract the most important sentences
    from a long text. This runs 100% locally with zero API cost.

    Args:
        text: The original abstract/summary text.
        sentence_count: Number of key sentences to extract (default: 6).

    Returns:
        A shortened version of the text (5-7 sentences), or the
        original text if sumy is unavailable or the text is already short.
    """
    if not SUMY_AVAILABLE:
        return text

    # If the text is already short (fewer than 8 sentences), don't summarize
    if text.count('.') <= sentence_count + 1:
        return text

    try:
        parser = PlaintextParser.from_string(text, Tokenizer('english'))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, sentence_count)
        return ' '.join(str(s) for s in summary_sentences)
    except Exception:
        # If anything goes wrong, just return the original text
        return text


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
    # Pre-summarize the abstract locally before sending to AI
    abstract = paper.get('full_summary') or paper.get('summary') or ''
    if abstract:
        abstract = _local_presummarize(abstract)
        parts.append(f"Abstract:\n{abstract}")
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Chat with Paper
# ---------------------------------------------------------------------------

def chat_with_paper(paper: dict, user_message: str) -> dict:
    """
    Send a user question about a paper to Groq and return the AI response.

    Args:
        paper: Dict with paper metadata (title, authors, summary, etc.)
        user_message: The user's question.

    Returns:
        {'reply': str, 'error': str|None}
    """
    if not GROQ_AVAILABLE:
        return {
            'reply': '',
            'error': 'The groq package is not installed. '
                     'Run: pip install groq'
        }
    if groq_client is None:
        return {
            'reply': '',
            'error': 'GROQ_API_KEY environment variable is not set. '
                     'Get a free key at https://console.groq.com'
        }

    context = _build_paper_context(paper)

    system_prompt = """You are a helpful research assistant. The user is reading an academic paper and has a question about it. Answer clearly and accurately based on the paper's information. If you cannot determine the answer from the provided abstract, say so honestly and offer your best insight. Use bullet points or numbered lists where helpful. Keep the tone informative but accessible."""

    user_prompt = f"""--- PAPER ---
{context}
--- END PAPER ---

User's question: {user_message}"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0.4,
            max_tokens=1024,
        )
        reply = chat_completion.choices[0].message.content
        return {'reply': reply, 'error': None}
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
    if not GROQ_AVAILABLE:
        return {
            'summary': '',
            'error': 'The groq package is not installed. '
                     'Run: pip install groq'
        }
    if groq_client is None:
        return {
            'summary': '',
            'error': 'GROQ_API_KEY environment variable is not set. '
                     'Get a free key at https://console.groq.com'
        }

    context = _build_paper_context(paper)

    system_prompt = """You are an expert research analyst. Given an academic paper, provide a comprehensive and insightful summary. Structure your response as follows:

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

Provide a thorough, well-organized summary. Use markdown formatting. Be informative but keep it accessible to someone who hasn't read the full paper."""

    user_prompt = f"""--- PAPER ---
{context}
--- END PAPER ---"""

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            model=GROQ_MODEL,
            temperature=0.5,
            max_tokens=2048,
        )
        reply = chat_completion.choices[0].message.content
        return {'summary': reply, 'error': None}
    except Exception as e:
        return {'summary': '', 'error': f'AI request failed: {str(e)}'}

