from typing import Any, Optional
import requests
from utils.configparser import parse_config


class LLMClient:
    """Provider-agnostic LLM client.

    Provider is selected via config.ini under [llm].provider (default: gemini).
    Supports a minimal generate(prompt) interface returning plain text.
    """

    def __init__(self, provider: Optional[str] = None):
        cfg = parse_config()
        provider_cfg = cfg.get('llm', {}) if cfg is not None else {}
        self.provider = provider or provider_cfg.get('provider', 'gemini')
        # Gemini config
        gem_cfg = cfg.get('gemini', {}) if cfg is not None else {}
        self.gemini_api_key = gem_cfg.get('api_key')
        self.gemini_model = gem_cfg.get('model', 'text-bison-001')
        # OpenAI config (fallback)
        gtp3_cfg = cfg.get('gtp3', {}) if cfg is not None else {}
        self.openai_api_key = gtp3_cfg.get('apikey')
        self.openai_model = gtp3_cfg.get('model', 'text-davinci-002')

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        if self.provider.lower() == 'gemini':
            return self._generate_gemini(prompt, max_tokens, temperature)
        else:
            return self._generate_openai(prompt, max_tokens, temperature)

    def _generate_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.gemini_api_key:
            raise RuntimeError('Gemini api_key not found in config.ini under [gemini]')
        # NOTE: this uses the (public) Generative Language REST endpoint pattern. Adjust if your
        # Google Cloud setup requires service account authentication or a different path.
        url = f"https://generativelanguage.googleapis.com/v1beta2/models/{self.gemini_model}:generate?key={self.gemini_api_key}"
        payload = {
            "prompt": {"text": prompt},
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        }
        r = requests.post(url, json=payload, timeout=60)
        try:
            r.raise_for_status()
        except Exception:
            # Surface raw body for easier debugging
            raise RuntimeError(f'Gemini request failed: {r.status_code} {r.text}')
        data = r.json()
        # Try common response shapes. Depending on API version the text may be in:
        # - data['candidates'][0]['output']
        # - data['result']['content']
        # - data['candidates'][0]['content']
        text = ''
        if isinstance(data, dict):
            if 'candidates' in data and isinstance(data['candidates'], list) and data['candidates']:
                cand = data['candidates'][0]
                text = cand.get('output') or cand.get('content') or ''
            if not text:
                result = data.get('result') or {}
                text = result.get('content', '') or result.get('output', '')
        return text or ''

    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.openai_api_key:
            raise RuntimeError('OpenAI apikey not found in config.ini under [gtp3]')
        url = 'https://api.openai.com/v1/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.openai_api_key}'
        }
        payload = {
            'model': self.openai_model,
            'prompt': prompt,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # OpenAI completion response typically has choices[0].text
        choices = data.get('choices', [])
        if choices:
            return choices[0].get('text', '')
        return ''
