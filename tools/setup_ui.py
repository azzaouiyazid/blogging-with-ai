import streamlit as st
import sys
from pathlib import Path
import configparser
import json
import sqlite3

# Make sure src is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / 'src'
sys.path.insert(0, str(SRC_PATH))

st.set_page_config(page_title="AI Blogger Setup UI", layout="wide")
st.title("AI-Blogger — Local Setup & Control Panel")
st.markdown("""
This local UI helps you configure and validate the blogging-with-ai project.
- Create or edit config.ini (service account upload supported)
- Validate LLM (Gemini) credentials
- Run discovery / retrieval smoke tests
- Inspect the SQLite DB and run migration
- Run the orchestrator in dry-run

Run this UI with:

```bash
pip install -r requirements.txt
streamlit run tools/setup_ui.py
```
""")


def write_config(cfg: configparser.ConfigParser, path: Path):
    with open(path, 'w') as f:
        cfg.write(f)


st.sidebar.header("Config file")
config_file_path = REPO_ROOT / 'config.ini'
st.sidebar.write(f"Config file: {config_file_path}")

if config_file_path.exists():
    st.sidebar.success("config.ini found")
else:
    st.sidebar.warning("No config.ini present — use the form below to create one")

with st.expander("Edit / create config.ini", expanded=True):
    cfg = configparser.ConfigParser()
    if config_file_path.exists():
        cfg.read(config_file_path)

    def get(section, key, default=''):
        try:
            return cfg.get(section, key)
        except Exception:
            return default

    # LLM section
    st.subheader("LLM (Gemini / OpenAI)")
    provider = st.selectbox("Provider", options=['gemini', 'openai'], index=0 if get('llm', 'provider', 'gemini') == 'gemini' else 1)
    gemini_service_account = st.text_input('Gemini service_account_file (path)', value=get('gemini', 'service_account_file', ''))
    gemini_api_key = st.text_input('Gemini API key (optional)', value=get('gemini', 'api_key', ''))
    gemini_model = st.text_input('Gemini model', value=get('gemini', 'model', 'text-bison-001'))

    # OpenAI fallback
    st.subheader('OpenAI (fallback)')
    openai_api_key = st.text_input('OpenAI API key', value=get('gtp3', 'apikey', ''))
    openai_model = st.text_input('OpenAI model', value=get('gtp3', 'model', 'text-davinci-002'))
    openai_max_token = st.text_input('OpenAI maxtoken', value=get('gtp3', 'maxtoken', '2000'))

    # NewsAPI / SerpAPI
    st.subheader('Discovery / Retrieval')
    newsapi_key = st.text_input('NewsAPI key', value=get('newsapi', 'api_key', ''))
    serpapi_key = st.text_input('SerpAPI key', value=get('serpapi', 'api_key', ''))

    # Shopify
    st.subheader('Shopify (optional)')
    shop_store = st.text_input('Shopify store (your-store.myshopify.com)', value=get('shopify', 'store', ''))
    shop_token = st.text_input('Shopify admin api_token', value=get('shopify', 'api_token', ''))
    shop_blog_id = st.text_input('Shopify blog_id', value=get('shopify', 'blog_id', ''))
    shop_api_version = st.text_input('Shopify api_version', value=get('shopify', 'api_version', '2024-10'))
    shop_blog_handle = st.text_input('Shopify blog_handle (optional)', value=get('shopify', 'blog_handle', ''))

    # Telegram
    st.subheader('Telegram (optional)')
    telegram_token = st.text_input('Telegram bot token', value=get('telegram', 'bot_token', ''))
    telegram_chat = st.text_input('Telegram review_chat_id', value=get('telegram', 'review_chat_id', ''))

    # Unsplash
    st.subheader('Unsplash (optional)')
    unsplash_access = st.text_input('Unsplash accesskey', value=get('unsplash', 'accesskey', ''))
    unsplash_secret = st.text_input('Unsplash secretkey', value=get('unsplash', 'secretkey', ''))

    if st.button('Save config.ini'):
        if not cfg.has_section('llm'):
            cfg.add_section('llm')
        cfg.set('llm', 'provider', provider)
        if not cfg.has_section('gemini'):
            cfg.add_section('gemini')
        cfg.set('gemini', 'service_account_file', gemini_service_account)
        cfg.set('gemini', 'api_key', gemini_api_key)
        cfg.set('gemini', 'model', gemini_model)
        if not cfg.has_section('gtp3'):
            cfg.add_section('gtp3')
        cfg.set('gtp3', 'apikey', openai_api_key)
        cfg.set('gtp3', 'model', openai_model)
        cfg.set('gtp3', 'maxtoken', openai_max_token)
        if not cfg.has_section('newsapi'):
            cfg.add_section('newsapi')
        cfg.set('newsapi', 'api_key', newsapi_key)
        if not cfg.has_section('serpapi'):
            cfg.add_section('serpapi')
        cfg.set('serpapi', 'api_key', serpapi_key)
        if not cfg.has_section('shopify'):
            cfg.add_section('shopify')
        cfg.set('shopify', 'store', shop_store)
        cfg.set('shopify', 'api_token', shop_token)
        cfg.set('shopify', 'blog_id', shop_blog_id)
        cfg.set('shopify', 'api_version', shop_api_version)
        cfg.set('shopify', 'blog_handle', shop_blog_handle)
        if not cfg.has_section('telegram'):
            cfg.add_section('telegram')
        cfg.set('telegram', 'bot_token', telegram_token)
        cfg.set('telegram', 'review_chat_id', telegram_chat)
        if not cfg.has_section('unsplash'):
            cfg.add_section('unsplash')
        cfg.set('unsplash', 'accesskey', unsplash_access)
        cfg.set('unsplash', 'secretkey', unsplash_secret)

        write_config(cfg, config_file_path)
        st.success(f'Wrote config.ini to {config_file_path}')


st.header('Validation & Tests')

col1, col2 = st.columns(2)

with col1:
    st.subheader('LLM validation')
    niche_input = st.text_input('Test prompt', value='Say hello in one sentence')
    if st.button('Validate LLM'):
        st.info('Running LLM test...')
        try:
            from utils.llm import LLMClient
            client = LLMClient()
            out = client.generate(niche_input, max_tokens=64)
            st.success('LLM call succeeded')
            st.code(out)
        except Exception as e:
            st.error(f'LLM validation failed: {e}')

    st.subheader('Discovery test (NewsAPI)')
    niche = st.text_input('Niche for discovery', value='shopify')
    if st.button('Run discovery'):
        st.info('Running discovery.trends.discover_topics...')
        try:
            from discovery.trends import discover_topics
            topics = discover_topics(niche, days=2, top_k=5)
            st.write(topics)
        except Exception as e:
            st.error(f'Discovery test failed: {e}')

    st.subheader('SERP fetch test (SerpAPI)')
    serp_query = st.text_input('SERP query', value='shopify trends')
    if st.button('Fetch SERP top results'):
        st.info('Running retrieval.serp.fetch_top_results...')
        try:
            from retrieval.serp import fetch_top_results
            import json
            res = fetch_top_results(serp_query, num=5)
            st.json(res)
        except Exception as e:
            st.error(f'SERP fetch failed: {e}')

with col2:
    st.subheader('Page fetch & extract')
    url = st.text_input('URL to fetch', value='https://example.com')
    if st.button('Fetch & extract page'):
        st.info('Running retrieval.fetcher.fetch_and_extract...')
        try:
            from retrieval.fetcher import fetch_and_extract
            res = fetch_and_extract(url)
            st.json(res)
        except Exception as e:
            st.error(f'Fetch failed: {e}')

    st.subheader('Orchestrator (dry-run)')
    orchestrator_niche = st.text_input('Orchestrator niche', value='shopify')
    if st.button('Run orchestrator (dry-run)'):
        st.info('Running orchestrator.auto_publisher.run_once (dry_run=True)...')
        try:
            from orchestrator.auto_publisher import run_once
            import json
            out = run_once(orchestrator_niche, days=2, topics_k=2, snippets_per_topic=2, dry_run=True)
            st.json(out)
        except Exception as e:
            st.error(f'Orchestrator dry-run failed: {e}')

st.header('Database & Migration')

db_path = REPO_ROOT / 'db.db'
if db_path.exists():
    st.write(f'Database at {db_path}')
    if st.button('Show Posts (first 20 rows)'):
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cur.fetchall()
            st.write('Tables:', tables)
            cur.execute("SELECT * FROM Posts LIMIT 20;")
            rows = cur.fetchall()
            st.write(rows)
            conn.close()
        except Exception as e:
            st.error(f'Error reading database: {e}')
else:
    st.warning('No db.db found in repository root. Run the orchestrator to create one or provide an existing DB.')

if st.button('Run sqlite_migrate_posts.py'):
    st.info('Running scripts/sqlite_migrate_posts.py...')
    try:
        import subprocess
        res = subprocess.run([sys.executable, str(REPO_ROOT / 'scripts' / 'sqlite_migrate_posts.py')], capture_output=True, text=True)
        st.text(res.stdout + '\n' + res.stderr)
    except Exception as e:
        st.error(f'Migration failed: {e}')

st.header('Telegram')
if st.button('Send test review message to Telegram'):
    st.info('Sending test message (if configured)')
    try:
        from utils.configparser import parse_config
        cfg = parse_config()
        chat = cfg['telegram']['review_chat_id']
        from integrations.telegram import send_review_message
        article = {"title": "Test", "meta_description": "meta", "slug": "test", "body_html": "<p>test</p>", "tags": [], "faq_jsonld": "[]", "seo_keywords": []}
        res = send_review_message(chat, 1, article)
        st.write(res)
    except Exception as e:
        st.error(f'Telegram test failed: {e}')

st.markdown('---')
st.markdown('If you need help, paste the error outputs here and I can help you triage them.')
