import time
from typing import Any, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _default_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = _default_session()


def get(url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None, timeout: int = 10) -> requests.Response:
    """GET with retries and simple backoff."""
    try:
        r = SESSION.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.RequestException as e:
        # simple backoff
        time.sleep(1)
        raise
