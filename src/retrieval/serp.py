"""Simple SERP adapter using SerpAPI as primary provider.

This module exposes functions to run a web search and return the top results
(title, snippet, link, source, published_at). The implementation expects a
`serpapi` section in config.ini with `api_key`.

If you prefer another provider, add a new function and update the orchestrator
to use it.
"""
from __future__ import annotations

from typing import List, Dict, Any
from urllib.parse import urlencode

from utils.configparser import parse_config
from utils.http import get


def search_serpapi(query: str, num: int = 5) -> List[Dict[str, Any]]:
    config = parse_config()
    api_key = config.get('serpapi', {}).get('api_key') if config is not None else None
    if not api_key:
        raise RuntimeError('SerpAPI api_key not found in config.ini under [serpapi]')
    params = {
        'q': query,
        'api_key': api_key,
        'num': num,
        'engine': 'google'
    }
    url = f"https://serpapi.com/search.json?{urlencode(params)}"
    r = get(url)
    data = r.json()
    results: List[Dict[str, Any]] = []
    organic = data.get('organic_results', [])
    for item in organic[:num]:
        results.append({
            'title': item.get('title'),
            'snippet': item.get('snippet') or item.get('snippet') or '',
            'link': item.get('link') or item.get('formatted_url'),
            'source': item.get('source') or '',
            'published_at': item.get('published') or None,
        })
    return results


def fetch_top_results(query: str, num: int = 5) -> List[Dict[str, Any]]:
    """Public helper: returns top SERP results for a query."""
    return search_serpapi(query, num=num)
