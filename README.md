# Blogging-with-AI — Shopify Auto-Publisher

This repository implements a Shopify-focused automated blogging pipeline powered by retrieval-augmented generation (RAG). It discovers recent, relevant topics in your niche, retrieves and extracts authoritative sources, generates SEO-optimized drafts using an LLM, verifies claims heuristically, creates drafts on Shopify, and sends review messages to Telegram for human approval.

This README is the authoritative project README aligned to the current repository scope (Shopify-first pipeline). It documents what we changed, what to check, how to run locally, what to verify before publishing, and next recommended steps. An architecture diagram is included below.

---

## Project overview

Goals
- Automatically discover trending topics in your niche (past 48 hours by default).
- Run SERP discovery and fetch top results, extracting main text for grounding.
- Use RAG to generate SEO-optimized blog posts (title, meta, slug, body_html, tags, FAQ JSON-LD, keywords).
- Heuristically verify claims against retrieved sources and flag unsupported sentences for review.
- Create drafts in Shopify (news/blog) and send a Telegram review message with Confirm / Rerun actions.
- Keep human-in-the-loop approval: drafts are created by default and published only after confirmation.

Primary components
- discovery: trending topic discovery (NewsAPI)
- retrieval: SERP retrieval (SerpAPI) + deeper page fetch & extract
- authoring: RAG writer (chat-completions + function schema) + claim verifier
- orchestrator: end-to-end pipeline that ties discovery → retrieval → authoring → publish
- integrations: Shopify controller, Unsplash helper, Telegram review integration
- storage: SQLite DB to track Posts and lifecycle

---

## Recent changes and current capabilities

The repository now implements the following (core features):
- NewsAPI-based discovery for recent topics (src/discovery/trends.py)
- SerpAPI adapter to fetch top organic results (src/retrieval/serp.py)
- Page fetcher with readability/BeautifulSoup extraction, robots.txt checks, polite throttling, and file-cache (.cache/pages) (src/retrieval/fetcher.py, src/retrieval/cache.py)
- RAG writer using OpenAI Chat Completions + function schema for strict JSON article output (src/authoring/rag_writer.py)
- Claim verification heuristics that flag unsupported sentences (src/authoring/claim_verifier.py)
- Orchestrator to run the pipeline and create Shopify drafts (src/orchestrator/auto_publisher.py)
- ShopifyController with draft creation & publishing endpoints (src/core/shopify_controller.py)
- Telegram integration for review/approval with inline Confirm / Rerun actions (src/integrations/telegram.py + webhook)
- DB model updates and a safe SQLite migration helper script to add columns (scripts/sqlite_migrate_posts.py)
- Utilities: HTTP helper with retries, caching helpers, and configuration parsing

We removed WordPress support to keep the project focused on the Shopify auto-publishing goal (src/core/wordpress_controller.py has been deprecated).

---

## Architecture (diagram)

ASCII overview:

  [Discovery]
       |
       v
  [SERP retrieval] -> [Page Fetch & Extract (cache)]
       |
       v
  [RAG Writer (LLM, function schema)]
       |
       v
  [Claim Verifier] -> flags -> [Human Review (Telegram)]
       |
       v
  [Create Shopify Draft]  <-- Confirm (Telegram) -- [Publish on Shopify]

Mermaid flow (GitHub supports mermaid diagrams in Markdown):

```mermaid
flowchart TD
  A[Discovery (NewsAPI)] --> B[SERP retrieval (SerpAPI)]
  B --> C[Page Fetch & Extract (readability / BeautifulSoup)]
  C --> D[RAG Writer (OpenAI Chat + function schema)]
  D --> E[Claim Verifier]
  E --> F[Orchestrator stores Draft in DB]
  F --> G[ShopifyController creates Draft]
  G --> H[Telegram Review Message]
  H -->|Confirm| I[ShopifyController publish draft]
  H -->|Rerun| D
```

Figure: pipeline sequencing — discovery → retrieval → generation → verification → draft → review → publish.

---

## Prerequisites

- Python 3.9+ (project uses typing annotations that assume 3.9+)
- Git
- API keys and accounts:
  - OpenAI API key (for the Chat Completions API)
  - NewsAPI key (newsapi.org) for discovery
  - SerpAPI key (or alternative search provider)
  - Shopify Admin API token and blog_id for your news/blog
  - Telegram bot token and your chat id (for review messages)
  - Optional: Unsplash API (used by existing Unsplash helper)

---

## Configuration (config.ini)

Create a `config.ini` in the repo root (the project expects a simple parser). Example keys the pipeline expects:

```ini
[gtp3]
apikey = YOUR_OPENAI_API_KEY
model = gpt-4-0613
maxtoken = 2000

[newsapi]
api_key = YOUR_NEWSAPI_KEY

[serpapi]
api_key = YOUR_SERPAPI_KEY

[shopify]
store = your-store.myshopify.com
api_token = YOUR_SHOPIFY_ADMIN_API_TOKEN
blog_id = 123456789
api_version = 2024-10
# optional
blog_handle = news

[telegram]
bot_token = YOUR_TELEGRAM_BOT_TOKEN
review_chat_id = YOUR_TELEGRAM_CHAT_ID

# optional: unsplash keys, other sections used by existing helpers
[unsplash]
api_key = YOUR_UNSPLASH_KEY
```

Place your keys and keep this file out of version control (add it to .gitignore).

---

## Install dependencies

Recommended virtual environment and install commands:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
# optional for better extraction
pip install readability-lxml beautifulsoup4
# if you will run the Telegram webhook
pip install flask requests
```

(If `requirements.txt` is not present, install these packages manually: requests, sqlalchemy, beautifulsoup4, readability-lxml, flask)

---

## Database & migration

The project uses an SQLite database (`db.db`) to store Post records.

Before running the orchestrator on an existing database, back it up:

```bash
cp db.db db.db.bak
```

If your Posts table was created before the model was updated, run the migration helper to add new columns safely:

```bash
python scripts/sqlite_migrate_posts.py
```

This script will run `ALTER TABLE` statements to add `platform`, `external_id`, `url`, `status`, and `topic` if they are missing. Keep a backup as this is non-reversible without a backup.

---

## Quick local checks (what to verify before running)

1. config.ini exists and contains valid API keys mentioned above.
2. `db.db` either doesn't exist (first run) or you have a backup copy.
3. `shopify.blog_id` is a valid integer and the provided token has the necessary Admin permissions (write articles).
4. Telegram credentials are valid and you know your `review_chat_id` (you can get it by messaging the bot or using `getUpdates`).
5. Optional: Install readability + BS4 for better extraction quality.

---

## How to run locally (safe dry-run first)

1) Discover topics (quick test):

```bash
PYTHONPATH=src python -c "from discovery.trends import discover_topics; print(discover_topics('your niche', days=2, top_k=5))"
```

2) Fetch top SERP results (quick test):

```bash
PYTHONPATH=src python -c "from retrieval.serp import fetch_top_results; import json; print(json.dumps(fetch_top_results('keyword', num=5), indent=2))"
```

3) Test page fetch + extraction (robot rules, cache):

```bash
PYTHONPATH=src python -c "from retrieval.fetcher import fetch_and_extract; import json; print(json.dumps(fetch_and_extract('https://example.com'), indent=2))"
```

4) Run the orchestrator in dry-run (no Shopify calls):

```bash
PYTHONPATH=src python -c "from orchestrator.auto_publisher import run_once; import json; print(json.dumps(run_once('your niche', days=2, topics_k=3, snippets_per_topic=3, dry_run=True), indent=2))"
```

5) Create actual Shopify drafts (only when you verified config and credentials):

```bash
PYTHONPATH=src python -c "from orchestrator.auto_publisher import run_once; print(run_once('your niche', dry_run=False))"
```

6) Run the Telegram webhook locally (for review callbacks):

```bash
PYTHONPATH=src python src/integrations/telegram_webhook.py
# expose with ngrok for Telegram to call your webhook:
# ngrok http 5000
# set webhook:
# curl "https://api.telegram.org/bot<token>/setWebhook?url=https://<ngrok-url>/telegram_webhook"
```

7) (Optional) Send a manual review message for testing:

```bash
PYTHONPATH=src python - <<'PY'
from integrations.telegram import send_review_message
from utils.configparser import parse_config
cfg = parse_config()
chat_id = cfg['telegram']['review_chat_id']
article = {"title":"Test","meta_description":"Meta","slug":"test","body_html":"<p>Test</p>","tags":[],"faq_jsonld":"[]","seo_keywords":[]}
print(send_review_message(chat_id, 1, article))
PY
```

---

## What to check after a run

- Check `.cache/pages` for cached page files (ensures caching is working).
- Check `db.db` rows in the `Posts` table. Each run should create Post records with `status` = 'draft' (or 'failed').
- If dry_run=False and Shopify credentials are correct, drafts should appear in your Shopify blog (verify `Posts.external_id` stores the article id).
- Telegram: you should receive a review message in the configured chat. Use Confirm to publish or Rerun to regenerate.
- Inspect logs for OpenAI usage and potential errors — ensure you have token budget monitored.

---

## Next recommended steps (prioritized)

1. Add a human-review UI (simple Flask app) to view drafts and flagged sentences, with Approve/Reject actions.
2. Implement crawl-delay parsing in robots.txt and honor site-specific crawl delays per-domain.
3. Add SERP response caching and a small quota system to avoid hitting provider limits.
4. Add claim-verification improvements (semantic similarity using embeddings rather than word overlap) for more robust checks.
5. Use a task queue (Celery/RQ + Redis) to schedule and scale discovery runs.
6. Add monitoring: token usage, success/failure rates, and Search Console integration for performance measurement.

---

## Files removed / deprecated
- WordPress support removed and replaced with a deprecation stub: `src/core/wordpress_controller.py` is no longer active. The original implementation is archived in `scripts/archived/` (if present) for recovery.

---

## Troubleshooting
- OpenAI errors: check `config.ini` for valid key and that usage limits are not exceeded.
- Shopify errors: ensure Admin API token has correct scopes (write content) and `blog_id` exists for the store.
- Robots/403 on fetcher: some sites block scraping; the fetcher will respect robots.txt and may return `disallowed by robots.txt`.

---

## Contact / Credits
- Built and maintained by the repository owner.
- If you want me to make further changes (human review UI, better claim verification, deployable Docker image), list them and I will implement them next.

---

