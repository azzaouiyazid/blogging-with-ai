import streamlit as st
import sys
from pathlib import Path
import configparser
import json
import sqlite3
import os

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

# Credentials directory (local, restricted)
CRED_DIR = REPO_ROOT / '.credentials'
CRED_DIR.mkdir(exist_ok=True)
SERVICE_ACCOUNT_PATH = CRED_DIR / 'gemini_service_account.json'

with st.expander("Upload / manage service account (recommended)", expanded=True):
    st.write("Upload a Google Cloud service account JSON for Gemini (the file will be stored locally at ~/.credentials and configured automatically).")
    uploaded_file = st.file_uploader('Upload gemini service account JSON', type=['json'], accept_multiple_files=False)
    if uploaded_file is not None:
        try:
            content = uploaded_file.read()
            parsed = json.loads(content)
            # basic validation
            client_email = parsed.get('client_email')
            project_id = parsed.get('project_id')
            if not client_email or not project_id:
                st.error('Uploaded JSON does not look like a valid service account key (missing client_email or project_id).')
            else:
                # ensure credentials dir exists and write file with secure permissions
                CRED_DIR.mkdir(mode=0o700, exist_ok=True)
                with open(SERVICE_ACCOUNT_PATH, 'wb') as f:
                    f.write(content)
                try:
                    os.chmod(SERVICE_ACCOUNT_PATH, 0o600)
                except Exception:
                    # chmod may fail on Windows; ignore
                    pass
                st.success(f'Wrote service account JSON to {SERVICE_ACCOUNT_PATH}')
                st.write(f'Project: {project_id} — {client_email}')

                # update or create config.ini with gemini.service_account_file
                cfg = configparser.ConfigParser()
                if config_file_path.exists():
                    cfg.read(config_file_path)
                if not cfg.has_section('llm'):
                    cfg.add_section('llm')
                if not cfg.has_section('gemini'):
                    cfg.add_section('gemini')
                cfg.set('llm', 'provider', cfg.get('llm', 'provider', fallback='gemini'))
                cfg.set('gemini', 'service_account_file', str(SERVICE_ACCOUNT_PATH))
                cfg.set('gemini', 'model', cfg.get('gemini', 'model', fallback='text-bison-001'))
                write_config(cfg, config_file_path)
                st.info(f'Updated {config_file_path} with gemini.service_account_file')
        except json.JSONDecodeError:
            st.error('Uploaded file is not valid JSON')
        except Exception as e:
            st.error(f'Error saving service account file: {e}')

    if SERVICE_ACCOUNT_PATH.exists():
        st.write('Service account currently stored at:')
        st.code(str(SERVICE_ACCOUNT_PATH))
        if st.button('Remove stored service account'):
            try:
                SERVICE_ACCOUNT_PATH.unlink()
                st.success('Removed stored service account file')
            except Exception as e:
                st.error(f'Failed to remove file: {e}')


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
            if out:
                st.success('LLM call succeeded')
                st.code(out)
            else:
                st.warning('LLM call returned empty response — check credentials and model')
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
            import json as _json
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
            # safe attempt to query Posts table
            try:
                cur.execute("SELECT * FROM Posts LIMIT 20;")
                rows = cur.fetchall()
                st.write(rows)
            except Exception:
                st.warning('Posts table not found or query failed')
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
