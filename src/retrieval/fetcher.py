from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from utils.http import get

try:
    from readability import Document
    from bs4 import BeautifulSoup
    HAVE_READABILITY = True
except Exception:
    HAVE_READABILITY = False


def _extract_meta_description(soup: 'BeautifulSoup') -> Optional[str]:
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        return meta['content']
    og = soup.find('meta', attrs={'property': 'og:description'})
    if og and og.get('content'):
        return og['content']
    return None


def fetch_and_extract(url: str, max_chars: int = 800) -> Dict[str, Any]:
    """Fetch a page and extract its main text and a short excerpt.

    Tries to use readability + BeautifulSoup for best results. Falls back to
    meta description and the first paragraphs if readability is not available.
    Returns a dict: { 'url', 'title', 'text', 'excerpt', 'html' }
    """
    try:
        r = get(url, timeout=10)
    except Exception as e:
        return {'url': url, 'title': '', 'text': '', 'excerpt': '', 'html': '', 'error': str(e)}

    html = r.text
    try:
        if HAVE_READABILITY:
            doc = Document(html)
            summary_html = doc.summary()
            title = doc.title() or ''
            soup = BeautifulSoup(summary_html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            excerpt = text[:max_chars]
            return {'url': url, 'title': title, 'text': text, 'excerpt': excerpt, 'html': summary_html}
        else:
            # fallback: parse with bs4 and get meta description + first 3 paragraphs
            soup_full = BeautifulSoup(html, 'html.parser')
            title_tag = soup_full.find('title')
            title = title_tag.get_text().strip() if title_tag else ''
            meta_desc = _extract_meta_description(soup_full) or ''
            paras = [p.get_text().strip() for p in soup_full.find_all('p') if p.get_text().strip()]
            joined = ' '.join(paras[:3])
            text = meta_desc or joined
            excerpt = text[:max_chars]
            return {'url': url, 'title': title, 'text': text, 'excerpt': excerpt, 'html': ''}
    except Exception as e:
        return {'url': url, 'title': '', 'text': '', 'excerpt': '', 'html': '', 'error': str(e)}


def fetch_snippets_for_results(results: List[Dict[str, Any]], max_chars: int = 800) -> List[Dict[str, Any]]:
    """Enrich a list of SERP results with extracted text from each result's URL.

    Input: results is a list of dicts with keys: title, snippet, link
    Output: list of dicts with additional keys: text, excerpt, html
    """
    enriched: List[Dict[str, Any]] = []
    for r in results:
        link = r.get('link') or r.get('url') or ''
        if not link:
            enriched.append({**r, 'text': '', 'excerpt': ''})
            continue
        try:
            fetched = fetch_and_extract(link, max_chars=max_chars)
            item = {**r, 'text': fetched.get('text', ''), 'excerpt': fetched.get('excerpt', ''), 'html': fetched.get('html', '')}
        except Exception as e:
            item = {**r, 'text': '', 'excerpt': '', 'html': '', 'error': str(e)}
        enriched.append(item)
    return enriched
