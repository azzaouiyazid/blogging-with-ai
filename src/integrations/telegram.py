"""Telegram integration: send review messages with inline Confirm / Rerun buttons, and handle callbacks.

This module provides a simple webhook handler and helper functions to send review
messages when a draft is ready. It expects `telegram_bot_token` and `review_chat_id`
in config.ini under [telegram].

Usage:
  - Add to config.ini:
    [telegram]
    bot_token=<your_bot_token>
    review_chat_id=<your_telegram_user_or_group_chat_id>

  - Deploy the webhook handler (Flask) at /telegram_webhook and configure the
    Telegram Bot webhook to point to https://<yourhost>/telegram_webhook

Notes:
  - For small deployments you can also run a polling loop instead of webhook.
  - Callback data is encoded as: action:post_id
"""
from __future__ import annotations

import json
import requests
from typing import Dict, Any, Optional

from utils.configparser import parse_config
from core.shopify_controller import ShopifyController
from authoring.rag_writer import generate_article
from retrieval.serp import fetch_top_results
from retrieval.fetcher import fetch_snippets_for_results
from authoring.claim_verifier import verify_claims


def _get_telegram_config() -> Dict[str, Any]:
    cfg = parse_config()
    t = cfg.get('telegram', {}) if cfg is not None else {}
    return t


def _bot_api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def send_review_message(chat_id: int | str, post_id: int, article: Dict[str, Any]) -> Dict[str, Any]:
    """Send the article to the reviewer chat with inline Confirm / Rerun buttons.

    Returns Telegram API response.
    """
    cfg = _get_telegram_config()
    token = cfg.get('bot_token')
    if not token:
        raise RuntimeError('Telegram bot token not configured under [telegram] in config.ini')

    title = article.get('title')
    meta = article.get('meta_description')
    excerpt = article.get('body_html')[:800]
    text = f"*Review draft:* {title}\n\n{meta}\n\n{excerpt}"

    # inline keyboard with callback_data format: action:post_id
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirm and Publish", "callback_data": f"confirm:{post_id}"},
                {"text": "🔁 Rerun and Regenerate", "callback_data": f"rerun:{post_id}"}
            ]
        ]
    }

    url = _bot_api_url(token, 'sendMessage')
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_markup': json.dumps(reply_markup)
    }
    r = requests.post(url, data=payload, timeout=15)
    r.raise_for_status()
    return r.json()


def handle_callback(update: Dict[str, Any]) -> Dict[str, Any]:
    """Process an incoming Telegram update (callback_query). Returns a response dict.

    Expected callback_data: 'confirm:<post_id>' or 'rerun:<post_id>'
    """
    cfg = _get_telegram_config()
    token = cfg.get('bot_token')
    if not token:
        raise RuntimeError('Telegram bot token not configured')

    if 'callback_query' not in update:
        return {'ok': False, 'error': 'not a callback_query'}

    cq = update['callback_query']
    data = cq.get('data', '')
    chat_id = cq['message']['chat']['id']
    message_id = cq['message']['message_id']
    from_user = cq.get('from', {})

    # acknowledge callback immediately
    ans_url = _bot_api_url(token, 'answerCallbackQuery')
    requests.post(ans_url, data={'callback_query_id': cq.get('id')})

    parts = data.split(':')
    if len(parts) != 2:
        return {'ok': False, 'error': 'invalid callback data'}
    action, post_id_str = parts
    try:
        post_id = int(post_id_str)
    except Exception:
        return {'ok': False, 'error': 'invalid post id'}

    # fetch post from DB to get topic and external_id
    from database.database import Database
    from database.models import Post
    db = Database()
    session = db.session
    post_obj = session.get(Post, post_id)
    if post_obj is None:
        # edit original message to indicate error
        _edit_message_text(token, chat_id, message_id, "Error: original post not found in DB.")
        return {'ok': False, 'error': 'post not found'}

    if action == 'confirm':
        # publish the Shopify article if external_id present
        shop = ShopifyController()
        try:
            blog_id = int(shop.config['shopify']['blog_id'])
            article_id = int(post_obj.external_id) if post_obj.external_id else None
            if article_id is None:
                # cannot publish; notify
                _edit_message_text(token, chat_id, message_id, "Cannot publish: missing article id in DB.")
                return {'ok': False, 'error': 'missing article id'}
            shop.update_article(blog_id=blog_id, article_id=article_id, published=True)
            # update post status in DB
            post_obj.status = 'published'
            session.commit()
            _edit_message_text(token, chat_id, message_id, f"Published ✅\nPost: {post_obj.title}")
            return {'ok': True}
        except Exception as e:
            _edit_message_text(token, chat_id, message_id, f"Publish failed: {e}")
            return {'ok': False, 'error': str(e)}

    elif action == 'rerun':
        # regenerate article for the same topic and send a new review message
        topic = getattr(post_obj, 'topic', None) or post_obj.title
        # regenerate using retrieval + RAG
        serp_results = fetch_top_results(topic, num=3)
        enriched = fetch_snippets_for_results(serp_results, max_chars=1200)
        try:
            article = generate_article(topic=topic, snippets=enriched, primary_keyword=topic, target_wordcount=900)
        except Exception as e:
            _edit_message_text(token, chat_id, message_id, f"Regeneration failed: {e}")
            return {'ok': False, 'error': str(e)}
        # send new review message
        send_review_message(chat_id, post_id, article)
        _edit_message_text(token, chat_id, message_id, "Regenerated and sent a new draft for review.")
        return {'ok': True}

    else:
        return {'ok': False, 'error': 'unknown action'}


def _edit_message_text(token: str, chat_id: int | str, message_id: int, text: str) -> None:
    url = _bot_api_url(token, 'editMessageText')
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text}
    try:
        requests.post(url, data=payload, timeout=15)
    except Exception:
        pass
