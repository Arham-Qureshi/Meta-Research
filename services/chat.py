"""
services/chat.py — ChatService for AI-powered paper interactions.

Inherits BaseService.  Encapsulates Groq + Gemini AI logic.
All AI interactions go through this single service.
"""

import os
from services.base import BaseService

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

try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False


class ChatService(BaseService):
    """AI chat and summarisation service for academic papers."""

    GEMINI_MODEL = 'gemini-2.0-flash'
    GROQ_MODEL = 'llama-3.3-70b-versatile'

    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if GENAI_AVAILABLE and api_key:
            genai.configure(api_key=api_key)
        self._gemini_key = api_key

        groq_key = os.environ.get('GROQ_API_KEY', '')
        self._groq_client = Groq(api_key=groq_key) if GROQ_AVAILABLE and groq_key else None

    # ── Public API ───────────────────────────────────────────

    def chat(self, paper: dict, user_message: str) -> dict:
        """Chat with a paper using Groq."""
        if not GROQ_AVAILABLE:
            return self._error('The groq package is not installed. Run: pip install groq')
        if self._groq_client is None:
            return self._error('GROQ_API_KEY environment variable is not set.')

        context = self._build_context(paper)
        system_prompt = (
            'You are a helpful research assistant. The user is reading an academic paper '
            'and has a question about it. Answer clearly and accurately based on the '
            "paper's information. If you cannot determine the answer from the provided "
            'abstract, say so honestly and offer your best insight. Use bullet points or '
            'numbered lists where helpful. Keep the tone informative but accessible.'
        )
        user_prompt = f'--- PAPER ---\n{context}\n--- END PAPER ---\n\nUser\'s question: {user_message}'

        try:
            completion = self._groq_client.chat.completions.create(
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                model=self.GROQ_MODEL,
                temperature=0.4,
                max_tokens=1024,
            )
            return {'reply': completion.choices[0].message.content, 'error': None}
        except Exception as e:
            return {'reply': '', 'error': f'AI request failed: {e}'}

    def summarize(self, paper: dict) -> dict:
        """Generate a comprehensive paper summary using Groq."""
        if not GROQ_AVAILABLE:
            return self._error('The groq package is not installed. Run: pip install groq')
        if self._groq_client is None:
            return self._error('GROQ_API_KEY environment variable is not set.')

        context = self._build_context(paper)
        system_prompt = (
            'You are an expert research analyst. Given an academic paper, provide a '
            'comprehensive and insightful summary. Structure your response clearly. '
            'Use markdown formatting. Be informative but accessible to someone who '
            "hasn't read the full paper."
        )
        user_prompt = f'--- PAPER ---\n{context}\n--- END PAPER ---'

        try:
            completion = self._groq_client.chat.completions.create(
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                model=self.GROQ_MODEL,
                temperature=0.5,
                max_tokens=2048,
            )
            return {'summary': completion.choices[0].message.content, 'error': None}
        except Exception as e:
            return {'summary': '', 'error': f'AI request failed: {e}'}

    # ── Reusable internals ───────────────────────────────────

    def _build_context(self, paper: dict) -> str:
        """Build a structured context string from paper metadata."""
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
            parts.append(f'Categories: {cats}')
        abstract = paper.get('full_summary') or paper.get('summary') or ''
        if abstract:
            abstract = self._presummarize(abstract)
            parts.append(f'Abstract:\n{abstract}')
        return '\n'.join(parts)

    @staticmethod
    def _presummarize(text: str, sentence_count: int = 6) -> str:
        """Shorten long abstracts locally before sending to AI."""
        if not SUMY_AVAILABLE:
            return text
        if text.count('.') <= sentence_count + 1:
            return text
        try:
            parser = PlaintextParser.from_string(text, Tokenizer('english'))
            summarizer = LsaSummarizer()
            sentences = summarizer(parser.document, sentence_count)
            return ' '.join(str(s) for s in sentences)
        except Exception:
            return text


# Module-level singleton
chat_service = ChatService()
