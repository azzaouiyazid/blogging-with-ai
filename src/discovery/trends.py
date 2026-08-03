"""Discovery utilities to find trending / recent topics for a niche.

This module provides a small NewsAPI-based discovery implementation and a
fallback n-gram extractor from recent headlines. It returns candidate
topics/keywords for downstream RAG + generation.

Requirements: add a NewsAPI key to config.ini under [newsapi] as api_key.
"""
from __future__ import annotations

from typing import List, Tuple
import datetime
import re
from collections import Counter

from utils.configparser import parse_config
from utils.http import get

STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are', 'was', 'were', 'will', 'has', 'have',
    'how', 'what', 'when', 'where', 'why', 'your', 'our', 'you', 'a', 'an', 'in', 'on', 'to', 'of', 'is',
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[\w']+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _top_phrases_from_texts(texts: List[str], top_k: int = 10) -> List[Tuple[str, int]]:
    unigrams = Counter()
    bigrams = Counter()
    for t in texts:
        tokens = _tokenize(t)
        unigrams.update(tokens)
        bigrams.update([' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)])
    # prefer bigrams, then unigrams
    results: List[Tuple[str, int]] = []
    for phrase, count in bigrams.most_common(top_k * 2):
        results.append((phrase, count))
        if len(results) >= top_k:
            break
    if len(results) < top_k:
        for phrase, count in unigrams.most_common(top_k):
            if (phrase, count) not in results:
                results.append((phrase, count))
            if len(results) >= top_k:
                break
    return results[:top_k]


def discover_topics_from_news(niche: str, days: int = 2, top_k: int = 10) -> List[Tuple[str, int]]:
    """Use NewsAPI to search for recent articles matching the niche and extract top phrases.

    Returns a list of (phrase, score).
    """
    config = parse_config()
    api_key = config.get('newsapi', {}).get('api_key') if config is not None else None
    if not api_key:
        raise RuntimeError('NewsAPI api_key not found in config.ini under [newsapi]')

    to_date = datetime.datetime.utcnow()
    from_date = to_date - datetime.timedelta(days=days)

    url = 'https://newsapi.org/v2/everything'
    params = {
        'q': niche,
        'from': from_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'to': to_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'pageSize': 100,
        'sortBy': 'relevancy',
        'language': 'en',
        'apiKey': api_key,
    }
    r = get(url, params=params)
    data = r.json()
    articles = data.get('articles', [])
    texts: List[str] = []
    for a in articles:
        title = a.get('title', '')
        desc = a.get('description', '') or ''
        combined = f"{title}. {desc}"
        texts.append(combined)
    if not texts:
        return []
    return _top_phrases_from_texts(texts, top_k=top_k)


def discover_topics(niche: str, days: int = 2, top_k: int = 10) -> List[str]:
    """Main entry: returns a list of candidate topic phrases (strings).

    Strategy: try NewsAPI-based discovery. If it fails, raise an exception so
    callers can fall back to a seed list or manual topics.
    """
    phrases = discover_topics_from_news(niche, days=days, top_k=top_k)
    return [p for p, _score in phrases]
