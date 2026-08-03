import json
import time
from typing import Any, Dict, List, Optional

from tests.test_openai import Openai


DEFAULT_MAX_RETRIES = 2


def _extract_json(text: str) -> str:
    """Attempt to extract the first JSON object found in text."""
    text = text.strip()
    # try direct json first
    try:
        json.loads(text)
        return text
    except Exception:
        pass
    # try to find a substring that looks like JSON
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass
    # fallback: try to find a list
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            pass
    raise ValueError('No JSON found in model output')


def _validate_article_schema(article: Dict[str, Any]) -> None:
    required = [
        'title', 'meta_description', 'slug', 'body_html', 'tags', 'faq_jsonld', 'seo_keywords'
    ]
    for k in required:
        if k not in article:
            raise ValueError(f"Missing required key: {k}")
    # meta length check
    if not (10 <= len(article['meta_description']) <= 320):
        # be permissive but warn
        raise ValueError('meta_description length out of expected range (10-320)')
    # tags and seo_keywords should be lists
    if not isinstance(article['tags'], list) or not isinstance(article['seo_keywords'], list):
        raise ValueError('tags and seo_keywords must be arrays')


def generate_prompt(topic: str, snippets: List[Dict[str, str]], primary_keyword: Optional[str], target_wordcount: int) -> str:
    snippets_text = ''
    for i, s in enumerate(snippets[:5], start=1):
        snippets_text += f"CONTEXT {i}: title: {s.get('title','')}; snippet: {s.get('snippet','')}; url: {s.get('link','')}.\n"

    seo_kw = primary_keyword or topic

    prompt = (
        "You are an expert SEO copywriter. Using only the CONTEXT snippets below, write an SEO-optimized blog article for the topic '"
        + topic + "'. Do NOT invent facts outside the provided CONTEXT. If a claim is not supported by the CONTEXT, mark it as 'needs verification'.\n\n"
        "SEO Brief:\n"
        f"- Primary keyword: {seo_kw}\n"
        f"- Target wordcount (approx): {target_wordcount}\n"
        "- Tone: authoritative and helpful. Include H1 and at least 3 H2 sections. Provide FAQ as JSON-LD.\n\n"
        "CONTEXT:\n"
        + snippets_text
        + "\nOUTPUT FORMAT: Return a single JSON object only with these keys: title, meta_description (50-160 chars preferred), slug, body_html (HTML string, include H1/H2/H3 tags), tags (array of strings), faq_jsonld (a JSON-LD string), seo_keywords (array of strings).\n"
        "Be strict: JSON only, no surrounding explanation.\n"
    )
    return prompt


def generate_article(topic: str, snippets: List[Dict[str, str]], primary_keyword: Optional[str] = None,
                     target_wordcount: int = 900, retries: int = DEFAULT_MAX_RETRIES) -> Dict[str, Any]:
    """Generate an article using the OpenAI wrapper in the repo.

    Returns a validated dict with required keys. Raises on repeated failure.
    """
    openai = Openai()
    prompt = generate_prompt(topic, snippets, primary_keyword, target_wordcount)

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        resp = openai.make_request(prompt)
        if resp.get('error') is not None:
            last_err = Exception(f"OpenAI error: {resp['error']}")
            time.sleep(1)
            continue
        raw = resp['choices'][0]['text']
        try:
            body = _extract_json(raw)
            article = json.loads(body)
            _validate_article_schema(article)
            return article
        except Exception as e:
            last_err = e
            # retry after short delay
            time.sleep(1)
            continue
    raise RuntimeError(f'Failed to generate valid article after {retries+1} attempts: {last_err}')
