from typing import Any, Optional
import requests
from utils.configparser import parse_config

try:
    # Optional: use service account credentials if provided
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleAuthRequest
    _HAS_GOOGLE_AUTH = True
except Exception:
    _HAS_GOOGLE_AUTH = False


class LLMClient:
    """Provider-agnostic LLM client with Gemini (default) and OpenAI fallback.

    Gemini supports either a service account JSON file (recommended) or an API key.
    Configure via config.ini:
      [llm]
      provider = gemini

      [gemini]
      api_key = OPTIONAL_API_KEY
      service_account_file = /path/to/service-account.json
      model = text-bison-001

    OpenAI fallback uses [gtp3].apikey and [gtp3].model if provider=openai.
    """

    def __init__(self, provider: Optional[str] = None):
        cfg = parse_config()
        provider_cfg = cfg.get('llm', {}) if cfg is not None else {}
        self.provider = (provider or provider_cfg.get('provider') or 'gemini').lower()
        # Gemini config
        gem_cfg = cfg.get('gemini', {}) if cfg is not None else {}
        self.gemini_api_key = gem_cfg.get('api_key')
        self.gemini_model = gem_cfg.get('model', 'text-bison-001')
        self.gemini_service_account = gem_cfg.get('service_account_file')
        # OpenAI config (fallback)
        gtp3_cfg = cfg.get('gtp3', {}) if cfg is not None else {}
        self.openai_api_key = gtp3_cfg.get('apikey')
        self.openai_model = gtp3_cfg.get('model', 'text-davinci-002')

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
        if self.provider == 'gemini':
            return self._generate_gemini(prompt, max_tokens, temperature)
        return self._generate_openai(prompt, max_tokens, temperature)

    def _get_gemini_bearer_token(self) -> Optional[str]:
        """If a service-account file is configured and google-auth is available, use it to mint a bearer token."""
        if not self.gemini_service_account:
            return None
        if not _HAS_GOOGLE_AUTH:
            raise RuntimeError('google-auth libraries are required to use a service account. Install google-auth.')
        try:
            scopes = ['https://www.googleapis.com/auth/cloud-platform']
            creds = service_account.Credentials.from_service_account_file(self.gemini_service_account, scopes=scopes)
            auth_req = GoogleAuthRequest()
            creds.refresh(auth_req)
            return creds.token
        except Exception as e:
            raise RuntimeError(f'Failed to obtain token from service account file: {e}')

    def _generate_gemini(self, prompt: str, max_tokens: int, temperature: float) -> str:
        # Build request payload
        payload = {
            'prompt': {'text': prompt},
            'maxOutputTokens': int(max_tokens),
            'temperature': temperature,
        }
        # Prefer service-account bearer token if configured
        token = None
        if self.gemini_service_account:
            token = self._get_gemini_bearer_token()

        if token:
            url = f'https://generativelanguage.googleapis.com/v1beta2/models/{self.gemini_model}:generate'
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            r = requests.post(url, headers=headers, json=payload, timeout=60)
        elif self.gemini_api_key:
            url = f'https://generativelanguage.googleapis.com/v1beta2/models/{self.gemini_model}:generate?key={self.gemini_api_key}'
            r = requests.post(url, json=payload, timeout=60)
        else:
            raise RuntimeError('Gemini credentials not configured: set gemini.api_key or gemini.service_account_file in config.ini')

        try:
            r.raise_for_status()
        except Exception:
            raise RuntimeError(f'Gemini request failed: {r.status_code} {r.text}')

        data = r.json()
        # Parse common response shapes
        text = ''
        if isinstance(data, dict):
            if 'candidates' in data and isinstance(data['candidates'], list) and data['candidates']:
                cand = data['candidates'][0]
                text = cand.get('output') or cand.get('content') or ''
            if not text:
                result = data.get('result') or {}
                # result may contain 'content' or 'output'
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
            'max_tokens': int(max_tokens),
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        choices = data.get('choices', [])
        if choices:
            return choices[0].get('text', '')
        return ''
