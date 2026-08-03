import os
import json
import hashlib
import time
from typing import Optional

CACHE_DIR = os.path.join('.cache', 'pages')
DEFAULT_TTL = 24 * 3600  # 24 hours

if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path_for_url(url: str) -> str:
    h = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")


def get_cached(url: str, max_age: int = DEFAULT_TTL) -> Optional[dict]:
    path = _cache_path_for_url(url)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ts = data.get('_fetched_at', 0)
        if time.time() - ts > max_age:
            return None
        return data
    except Exception:
        return None


def set_cached(url: str, payload: dict) -> None:
    path = _cache_path_for_url(url)
    try:
        payload_copy = dict(payload)
        payload_copy['_fetched_at'] = int(time.time())
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload_copy, f)
    except Exception:
        # best-effort; don't fail fetching because of cache write error
        return
