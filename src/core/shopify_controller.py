import requests
from typing import Any, Dict, Optional
from utils.configparser import parse_config


class ShopifyController:
    def __init__(self, store: Optional[str] = None, token: Optional[str] = None, api_version: Optional[str] = None):
        """Simple Shopify Admin API client for creating and updating blog articles.

        Expects config.ini [shopify] section with keys: store (your-store.myshopify.com),
        api_token (private app token), api_version (optional, defaults to 2024-10), blog_id.
        """
        self.config = parse_config()
        self.store = store if store is not None else self.config["shopify"]["store"]
        self.token = token if token is not None else self.config["shopify"]["api_token"]
        self.api_version = api_version if api_version is not None else self.config["shopify"].get("api_version", "2024-10")
        self.base = f"https://{self.store}/admin/api/{self.api_version}"

    def _headers(self) -> Dict[str, str]:
        return {"X-Shopify-Access-Token": self.token, "Content-Type": "application/json"}

    def create_article(self, blog_id: int, title: str, body_html: str, tags: list[str] | None = None,
                       summary_html: str | None = None, published_at: str | None = None,
                       image_src: str | None = None, published: bool | None = None) -> Any:
        """Create an article. If `published` is False the article will be created as draft.

        Note: Shopify API accepts `published` and `published_at` (ISO8601) in the article payload.
        """
        payload: Dict[str, Any] = {
            "article": {
                "title": title,
                "body_html": body_html,
            }
        }
        if tags:
            # Shopify expects a comma-separated string for tags
            payload["article"]["tags"] = ", ".join(tags)
        if summary_html:
            payload["article"]["summary_html"] = summary_html
        if published_at:
            payload["article"]["published_at"] = published_at
        if image_src:
            payload["article"]["image"] = {"src": image_src}
        if published is not None:
            payload["article"]["published"] = bool(published)

        url = f"{self.base}/blogs/{blog_id}/articles.json"
        r = requests.post(url, json=payload, headers=self._headers())
        r.raise_for_status()
        return r.json()["article"]

    def update_article(self, blog_id: int, article_id: int, published: bool = True, published_at: Optional[str] = None) -> Any:
        """Update an existing article. Use this to publish a draft by setting published=True.

        Returns the updated article object.
        """
        payload: Dict[str, Any] = {"article": {"id": article_id, "published": bool(published)}}
        if published_at:
            payload["article"]["published_at"] = published_at
        url = f"{self.base}/blogs/{blog_id}/articles/{article_id}.json"
        r = requests.put(url, json=payload, headers=self._headers())
        r.raise_for_status()
        return r.json().get("article")

    def get_all_articles(self, blog_id: int) -> Any:
        url = f"{self.base}/blogs/{blog_id}/articles.json"
        r = requests.get(url, headers=self._headers())
        r.raise_for_status()
        return r.json()
