"""Orchestrator that runs discovery -> retrieval -> RAG writer -> create draft in Shopify and stores a DB record.

Usage:
    from orchestrator.auto_publisher import run_once
    run_once('your niche here', dry_run=True)

By default dry_run=True (no Shopify API calls). Set dry_run=False to actually create drafts in Shopify.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import datetime
import json

from discovery.trends import discover_topics
from retrieval.serp import fetch_top_results
from authoring.rag_writer import generate_article
from core.shopify_controller import ShopifyController
from core.unsplash import Unsplash
from database.database import Database
from database.models import Post


def _ensure_release_dt(release: Optional[str] | datetime.datetime | None) -> datetime.datetime:
    if release is None:
        return datetime.datetime.now()
    if isinstance(release, datetime.datetime):
        return release
    # try to parse string isoformat
    try:
        return datetime.datetime.fromisoformat(str(release))
    except Exception:
        return datetime.datetime.now()


def run_once(niche: str, days: int = 2, topics_k: int = 3, snippets_per_topic: int = 3, dry_run: bool = True) -> List[Dict[str, Any]]:
    """Discover recent topics and generate drafts.

    Returns a list of result dicts with keys: topic, article (the generated JSON), shopify (api response or None), db (Post id)
    """
    results: List[Dict[str, Any]] = []
    topics = discover_topics(niche, days=days, top_k=topics_k)
    if not topics:
        return results

    shop = ShopifyController()
    unsplash = Unsplash()
    db = Database()

    for topic in topics:
        snippets = fetch_top_results(topic, num=snippets_per_topic)
        try:
            article = generate_article(topic=topic, snippets=snippets, primary_keyword=topic, target_wordcount=900)
        except Exception as e:
            results.append({'topic': topic, 'error': str(e)})
            continue

        # pick an image from unsplash if available
        image_src = None
        try:
            photo = unsplash.search_by_keyword(topic)
            if photo is not None:
                image_src = photo.get('photo_url')
        except Exception:
            image_src = None

        shopify_response = None
        external_id = None
        published_url = None
        status = 'draft'
        if not dry_run:
            try:
                blog_id = int(shop.config['shopify']['blog_id'])
                # create as draft (published=False)
                shopify_response = shop.create_article(blog_id=blog_id,
                                                       title=article['title'],
                                                       body_html=article['body_html'],
                                                       tags=article.get('tags', []),
                                                       summary_html=article.get('meta_description'),
                                                       image_src=image_src,
                                                       published=False)
                external_id = str(shopify_response.get('id')) if shopify_response.get('id') else None
                # try to build URL if blog_handle configured
                blog_handle = shop.config['shopify'].get('blog_handle', '')
                if blog_handle and shopify_response.get('handle'):
                    published_url = f"https://{shop.store}/blogs/{blog_handle}/{shopify_response.get('handle')}"
            except Exception as e:
                status = 'failed'
                shopify_response = {'error': str(e)}

        # persist to DB
        release_dt = _ensure_release_dt(None)
        post = Post(title=article['title'], content=article['body_html'],
                    release=release_dt, generated=datetime.datetime.now(),
                    wordcount=len(article['body_html'].split()), costs_in_dollar=0.0,
                    )
        # add optional fields if the model and DB support them
        try:
            # attempt to set new attributes; models may or may not have them depending on migration
            setattr(post, 'platform', 'shopify')
            setattr(post, 'external_id', external_id)
            setattr(post, 'url', published_url)
            setattr(post, 'status', status)
        except Exception:
            pass
        db.add(post)

        results.append({'topic': topic, 'article': article, 'shopify': shopify_response, 'db': {'title': post.title}})

    return results
