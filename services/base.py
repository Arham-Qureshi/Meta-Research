import requests
import logging

log = logging.getLogger(__name__)

class BaseService:
    # all backend services.
    TIMEOUT = 15
    HEADERS = {
        'User-Agent': 'MetaResearch/1.0 (Academic Research Tool)',
    }

    def _get(self, url: str, params: dict | None = None,
             headers: dict | None = None, timeout: int | None = None) -> requests.Response | None:
        try:
            resp = requests.get(
                url,
                params=params,
                headers={**self.HEADERS, **(headers or {})},
                timeout=timeout or self.TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning('GET %s failed: %s', url, exc)
            return None

    def _post(self, url: str, json_data: dict | None = None,
              headers: dict | None = None, timeout: int | None = None) -> requests.Response | None:
        """
        Perform an HTTP POST with shared defaults.
        """
        try:
            resp = requests.post(
                url,
                json=json_data,
                headers={**self.HEADERS, **(headers or {})},
                timeout=timeout or self.TIMEOUT,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning('POST %s failed: %s', url, exc)
            return None

    @staticmethod
    def _safe_json(response: requests.Response | None) -> dict:
        #Parse JSON 
        if response is None:
            return {}
        try:
            return response.json()
        except (ValueError, AttributeError):
            return {}

    @staticmethod
    def _error(message: str) -> dict:
        """Build a standardised error dict."""
        return {'error': message}
