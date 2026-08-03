"""Claim verification: flag sentences in the generated article that are not supported by the retrieved sources.

This is a heuristic approach: split the article into sentences and check whether
each sentence has sufficient word-overlap with any source excerpt/text. If not,
flag it for human review.
"""
from typing import List, Dict, Any
import re

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False


def _html_to_text(html: str) -> str:
    if HAVE_BS4:
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    # naive fallback
    return re.sub('<[^<]+?>', '', html)


def _sentences_from_text(text: str) -> List[str]:
    # naive sentence split on punctuation followed by space
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def _word_set(s: str) -> set:
    words = re.findall(r"[\w']+", s.lower())
    return set(words)


def verify_claims(body_html: str, sources: List[Dict[str, Any]], min_words: int = 6, overlap_threshold: float = 0.5) -> List[Dict[str, Any]]:
    """Return list of unsupported sentences with context.

    Each entry: { 'sentence': str, 'overlap': float, 'best_source': url or None }
    """
    text = _html_to_text(body_html)
    sentences = _sentences_from_text(text)
    results: List[Dict[str, Any]] = []

    # build source texts
    source_texts = []
    for s in sources:
        # prefer the 'text' field (extracted) then 'excerpt' then 'snippet'
        t = s.get('text') or s.get('excerpt') or s.get('snippet') or ''
        source_texts.append({'url': s.get('link') or s.get('url'), 'text': t})

    for sent in sentences:
        # skip very short sentences
        wordcount = len(re.findall(r"[\w']+", sent))
        if wordcount < min_words:
            continue
        s_set = _word_set(sent)
        best_overlap = 0.0
        best_url = None
        for src in source_texts:
            src_set = _word_set(src['text'])
            if not src_set:
                continue
            overlap = len(s_set & src_set) / max(1, len(s_set))
            if overlap > best_overlap:
                best_overlap = overlap
                best_url = src['url']
        if best_overlap < overlap_threshold:
            results.append({'sentence': sent, 'overlap': best_overlap, 'best_source': best_url})
    return results
