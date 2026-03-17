from abc import abstractmethod
from services.base import BaseService

class BaseAPIProvider(BaseService):
    NAME: str = ''
    DISPLAY_NAME: str = ''
    BASE_URL: str = ''

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def _normalize_paper(self, raw: dict) -> dict:
        raise NotImplementedError

    def _truncate_summary(self, text: str, max_len: int = 500) -> str:
        if not text:
            return ''
        return text[:max_len] + ('...' if len(text) > max_len else '')
