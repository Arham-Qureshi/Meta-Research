import os
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

API_KEY = os.environ.get('GEMINI_API_KEY', '')
MODEL_NAME = 'gemini-2.0-flash'

if GENAI_AVAILABLE and API_KEY:
    genai.configure(api_key=API_KEY)

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


def _local_presummarize(text: str, sentence_count: int = 6) -> str:
    if not SUMY_AVAILABLE:
        return text

    if text.count('.') <= sentence_count + 1:
        return text

    try:
        parser = PlaintextParser.from_string(text, Tokenizer('english'))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, sentence_count)
        return ' '.join(str(s) for s in summary_sentences)
    except Exception:
        return text


def _build_paper_context(paper: dict) -> str:
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
    abstract = paper.get('full_summary') or paper.get('summary') or ''
    if abstract:
        abstract = _local_presummarize(abstract)
        parts.append(f"Abstract:\n{abstract}")
    return '\n'.join(parts)

def chat_with_paper(paper: dict, user_message: str) -> dict:
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

def summarize_paper(paper: dict) -> dict:
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

