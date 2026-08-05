import requests
from typing import Any
from utils.configparser import parse_config
import json


class Openai:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.config = parse_config()

    def make_request(self, prompt: str) -> Any:
        # Backwards compatibility shim: delegate to LLMClient if available
        try:
            from utils.llm import LLMClient
            client = LLMClient()
            text = client.generate(prompt, max_tokens=2000, temperature=0)
            return {'choices': [{'text': text}], 'usage': {'total_tokens': len(text.split())}}
        except Exception:
            # Fallback to original direct OpenAI call if LLMClient is not usable
            if self.api_key is None:
                self.api_key = self.config['gtp3']['apikey']
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            url = "https://api.openai.com/v1/completions"
            payload = json.dumps({
                "model": "text-davinci-002",
                "prompt": f"{prompt}",
                "temperature": 0,
                "max_tokens": int(self.config['gtp3']['maxtoken']) - len(prompt)
            })
            r = requests.post(url, headers=headers, data=payload)
            return r.json()

    def validate(self) -> Any:
        try:
            from utils.llm import LLMClient
            client = LLMClient()
            _ = client.generate("Say this is a test", max_tokens=1)
            return {'ok': True}
        except Exception:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config["gtp3"]["apikey"]}'
            }
            url = "https://api.openai.com/v1/completions"
            payload = json.dumps({
                "model": "text-davinci-002",
                "prompt": "Say this is a test",
                "temperature": 0,
                "max_tokens": 1
            })
            r = requests.post(url, headers=headers, data=payload)
            return r.json()

    def __str__(self) -> Any:
        return self.api_key


# pytest-compatible test that skips if no remote credentials

def test_openai() -> None:
    from utils.configparser import parse_config
    import pytest
    cfg = parse_config()
    gem = cfg.get('gemini', {})
    gtp3 = cfg.get('gtp3', {})
    if not gem.get('api_key') and not gem.get('service_account_file') and not gtp3.get('apikey'):
        pytest.skip('No LLM credentials configured in config.ini; skipping remote LLM tests')
    openai = Openai()
    validation = openai.validate()
    if isinstance(validation, dict) and validation.get('error'):
        raise Exception(f'LLM request was not successful: {validation["error"]["message"]}')


def test_make_request() -> None:
    from utils.configparser import parse_config
    import pytest
    cfg = parse_config()
    gem = cfg.get('gemini', {})
    gtp3 = cfg.get('gtp3', {})
    if not gem.get('api_key') and not gem.get('service_account_file') and not gtp3.get('apikey'):
        pytest.skip('No LLM credentials configured in config.ini; skipping remote LLM tests')
    openai = Openai()
    assert openai.make_request("Whats 2 multiplied 2") is not None
