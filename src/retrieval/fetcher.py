from typing import Dict, Any, List
from urllib.parse import urlparse
import time
import urllib.robotparser as robotparser

from utils.http import get
from retrieval.cache import get_cached, set_cached

try:
    from readability import Document
    from bs4 import BeautifulSoup
    HAVE_READABILITY = True
except Exception:
    HAVE_READABILITY = False

# per-domain robot parsers & last-access times
_ROBOTS: Dict[str, robotparser.RobotFileParser] = {}
_LAST_ACCESS: Dict[str, float] = {}
_MIN_DELAY = 2.0  # seconds between requests to same domain


def _domain_from_url(url: str) -> str:
    p = urlparse(url)
    return p.netloc


def _is_allowed_by_robots(url: str, user_agent: str = '*') -> bool:
    domain = _domain_from_url(url)
    rp = _ROBOTS.get(domain)
    if rp is None:
        rp = robotparser.RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception:
            # If robots.txt cannot be fetched, default to allow
            rp = None
        _ROBOTS[domain] = rp
    if rp is None:
        return True
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


def _polite_wait(url: str) -> None:
    domain = _domain_from_url(url)
    last = _LAST_ACCESS.get(domain)
    now = time.time()
    if last is not None:
        elapsed = now - last
        if elapsed < _MIN_DELAY:
            to_wait = _MIN_DELAY - elapsed
            time.sleep(to_wait)
    _LAST_ACCESS[domain] = time.time()


def _extract_meta_description(soup) -> str:
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta and meta.get('content'):
        return meta['content']
    og = soup.find('meta', attrs={'property': 'og:description'})
    if og and og.get('content'):
        return og['content']
    return ''


def fetch_and_extract(url: str, max_chars: int = 800, cache_ttl: int = 24 * 3600) -> Dict[str, Any]:
    """Fetch a page and extract its main text and a short excerpt.

    This version respects robots.txt and uses polite per-domain throttling. It also
    uses a simple file cache to avoid refetching pages too often.
    """
    # check cache first
    cached = get_cached(url, max_age=cache_ttl)
    if cached is not None:
        return cached

    # robots.txt
    if not _is_allowed_by_robots(url):
        return {'url': url, 'title': '', 'text': '', 'excerpt': '', 'html': '', 'error': 'disallowed by robots.txt'}

    # polite wait
    _polite_wait(url)

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
            result = {'url': url, 'title': title, 'text': text, 'excerpt': excerpt, 'html': summary_html}
            set_cached(url, result)
            return result
        else:
            from bs4 import BeautifulSoup as BS
            soup_full = BS(html, 'html.parser')
            title_tag = soup_full.find('title')
            title = title_tag.get_text().strip() if title_tag else ''
            meta_desc = _extract_meta_description(soup_full) or ''
            paras = [p.get_text().strip() for p in soup_full.find_all('p') if p.get_text().strip()]
            joined = ' '.join(paras[:3])
            text = meta_desc or joined
            excerpt = text[:max_chars]
            result = {'url': url, 'title': title, 'text': text, 'excerpt': excerpt, 'html': ''}
            set_cached(url, result)
            return result
    except Exception as e:
        return {'url': url, 'title': '', 'text': '', 'excerpt': '', 'html': '', 'error': str(e)}


def fetch_snippets_for_results(results: List[Dict[str, Any]], max_chars: int = 800) -> List[Dict[str, Any]]:
    """Enrich a list of SERP results with extracted text from each result's URL.

    Input: results is a list of dicts with keys: title, snippet, link
    Output: list of dicts with additional keys: text, excerpt, html
    """
    enriched = []
    for r in results:
        link = r.get('link') or r.get('url') or ''
        if not link:
            enriched.append({**r, 'text': '', 'excerpt': ''})
            continue
        try:
            fetched = fetch_and_extract(link, max_chars=max_chars)
            item = {**r, 'text': fetched.get('text', ''), 'excerpt': fetched.get('excerpt', ''), 'html': fetched.get('html', ''), 'error': fetched.get('error')}
        except Exception as e:
            item = {**r, 'text': '', 'excerpt': '', 'html': '', 'error': str(e)}
        enriched.append(item)
    return enriched
