from services.providers.arxiv import ArxivProvider
from services.providers.semantic_scholar import SemanticScholarProvider
from services.providers.crossref import CrossrefProvider
from services.providers.openalex import OpenAlexProvider

PROVIDERS = {
    'arxiv':            ArxivProvider(),
    'semantic_scholar': SemanticScholarProvider(),
    'crossref':         CrossrefProvider(),
    'openalex':         OpenAlexProvider(),
}

def get_provider(name: str):
    return PROVIDERS.get(name)

def get_all_providers():
    return PROVIDERS.values()

