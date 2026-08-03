import json
import time
from typing import Any, Dict, List, Optional

from utils.configparser import parse_config
import requests

DEFAULT_MAX_RETRIES = 2


def _validate_article_schema(article: Dict[str, Any]) -> None:
    required = [
        'title', 'meta_description', 'slug', 'body_html', 'tags', 'faq_jsonld', 'seo_keywords'
    ]
    for k in required:
        if k not in article:
            raise ValueError(f"Missing required key: {k}")
    if not isinstance(article['tags'], list) or not isinstance(article['seo_keywords'], list):
        raise ValueError('tags and seo_keywords must be arrays')


def generate_prompt_messages(topic: str, snippets: List[Dict[str, str]], primary_keyword: Optional[str], target_wordcount: int) -> List[Dict[str, str]]:
    snippets_text = ''
    for i, s in enumerate(snippets[:5], start=1):
        # include excerpt/text if present for deeper retrieval
        snippet_part = s.get('excerpt') or s.get('snippet') or ''
        snippets_text += f"CONTEXT {i}: title: {s.get('title','')}; excerpt: {snippet_part}; url: {s.get('link','')}.\n"

    seo_kw = primary_keyword or topic

    system_msg = (
        "You are an expert SEO copywriter. Using only the CONTEXT snippets below, write an SEO-optimized blog article. Do NOT invent facts outside the provided CONTEXT. If a claim is not supported by the CONTEXT, mark it as 'needs verification'."
    )
    user_msg = (
        "SEO Brief:\n"
        f"- Primary keyword: {seo_kw}\n"
        f"- Target wordcount (approx): {target_wordcount}\n"
        "- Tone: authoritative and helpful. Include H1 and at least 3 H2 sections. Provide FAQ as JSON-LD.\n\n"
        "CONTEXT:\n"
        + snippets_text
        + "\nYou must RETURN A SINGLE JSON OBJECT matching the function schema exactly. No additional text."
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def generate_article(topic: str, snippets: List[Dict[str, str]], primary_keyword: Optional[str] = None,
                     target_wordcount: int = 900, retries: int = DEFAULT_MAX_RETRIES) -> Dict[str, Any]:
    """Generate an article using the OpenAI Chat Completions API with a function schema.

    This forces the model to return a structured JSON payload via a function call.
    """
    config = parse_config()
    api_key = config.get('gtp3', {}).get('apikey') if config is not None else None
    if not api_key:
        raise RuntimeError('OpenAI API key not found in config.ini under [gtp3]')

    messages = generate_prompt_messages(topic, snippets, primary_keyword, target_wordcount)

    function_schema = {
        "name": "return_article",
        "description": "Return a JSON object representing the generated article",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "meta_description": {"type": "string"},
                "slug": {"type": "string"},
                "body_html": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "faq_jsonld": {"type": "string"},
                "seo_keywords": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title", "meta_description", "slug", "body_html", "tags", "faq_jsonld", "seo_keywords"]
        }
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": config.get('gtp3', {}).get('model', 'gpt-4-0613'),
        "messages": messages,
        "functions": [function_schema],
        "function_call": {"name": "return_article"},
        "temperature": 0.0,
        "max_tokens": int(config.get('gtp3', {}).get('maxtoken', 2000))
    }

    last_err = None
    for attempt in range(retries + 1):
        r = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=payload, timeout=30)
        if r.status_code != 200:
            last_err = Exception(f'OpenAI API returned {r.status_code}: {r.text}')
            time.sleep(1)
            continue
        data = r.json()
        try:
            choice = data['choices'][0]
            msg = choice['message']
            if msg.get('function_call'):
                args_str = msg['function_call'].get('arguments', '{}')
                article = json.loads(args_str)
                _validate_article_schema(article)
                return article
            else:
                last_err = Exception('No function_call in response')
        except Exception as e:
            last_err = e
        time.sleep(1)
    raise RuntimeError(f'Failed to generate valid article after {retries+1} attempts: {last_err}')
