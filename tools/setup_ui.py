import streamlit as st
import sys
from pathlib import Path
import configparser
import json
import sqlite3
import os
import requests

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
- Configure API keys and scheduler
- Add keywords (dashboard)
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


def read_config(path: Path) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if path.exists():
        cfg.read(path)
    return cfg


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
DATA_DIR = REPO_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)
KEYWORDS_FILE = DATA_DIR / 'keywords.json'

# Load existing keywords or empty list
def load_keywords():
    if KEYWORDS_FILE.exists():
        try:
            return json.loads(KEYWORDS_FILE.read_text())
        except Exception:
            return []
    return []

def save_keywords(keywords):
    KEYWORDS_FILE.write_text(json.dumps(keywords, indent=2, ensure_ascii=False))


# Top-level tabs
tabs = st.tabs(["Settings", "Scheduler", "Dashboard (Keywords)", "Posts", "Logs & Actions"]) 

# --- Settings tab ---
with tabs[0]:
    st.header("Settings")
    cfg = read_config(config_file_path)

    llm_section = cfg.get('llm', {}) if cfg is not None else {}
    provider = llm_section.get('provider', 'gemini')

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("LLM / API keys")
        prov = st.selectbox('LLM provider', options=['gemini', 'openai'], index=0 if provider == 'gemini' else 1)

        # Gemini section
        st.markdown('### Gemini')
        gem_api_key = cfg.get('gemini', {}).get('api_key', '')
        gem_api_key_input = st.text_input('Gemini API key (optional)', value=gem_api_key, key='gem_api_key')
        gem_model = cfg.get('gemini', {}).get('model', 'text-bison-001')
        gem_model_input = st.text_input('Gemini model', value=gem_model, key='gem_model')
        st.write('Service account upload available in the main setup section.')

        # OpenAI
        st.markdown('### OpenAI (fallback)')
        openai_api_key = cfg.get('gtp3', {}).get('apikey', '')
        openai_api_key_input = st.text_input('OpenAI API key', value=openai_api_key, key='openai_api_key')
        openai_model = cfg.get('gtp3', {}).get('model', 'text-davinci-002')
        openai_model_input = st.text_input('OpenAI model', value=openai_model, key='openai_model')

        # Other keys
        st.markdown('### Other services')
        newsapi_key = cfg.get('newsapi', {}).get('api_key', '')
        newsapi_key_input = st.text_input('NewsAPI key', value=newsapi_key, key='newsapi_key')
        serpapi_key = cfg.get('serpapi', {}).get('api_key', '')
        serpapi_key_input = st.text_input('SerpAPI key', value=serpapi_key, key='serpapi_key')
        shop_store = cfg.get('shopify', {}).get('store', '')
        shop_store_input = st.text_input('Shopify store (your-store.myshopify.com)', value=shop_store, key='shop_store')
        shop_token = cfg.get('shopify', {}).get('api_token', '')
        shop_token_input = st.text_input('Shopify admin api_token', value=shop_token, key='shop_token')

        if st.button('Save settings'):
            # write back to config.ini
            if not cfg.has_section('llm'):
                cfg.add_section('llm')
            cfg.set('llm', 'provider', prov)
            if not cfg.has_section('gemini'):
                cfg.add_section('gemini')
            cfg.set('gemini', 'api_key', gem_api_key_input)
            cfg.set('gemini', 'model', gem_model_input)
            if not cfg.has_section('gtp3'):
                cfg.add_section('gtp3')
            cfg.set('gtp3', 'apikey', openai_api_key_input)
            cfg.set('gtp3', 'model', openai_model_input)
            if not cfg.has_section('newsapi'):
                cfg.add_section('newsapi')
            cfg.set('newsapi', 'api_key', newsapi_key_input)
            if not cfg.has_section('serpapi'):
                cfg.add_section('serpapi')
            cfg.set('serpapi', 'api_key', serpapi_key_input)
            if not cfg.has_section('shopify'):
                cfg.add_section('shopify')
            cfg.set('shopify', 'store', shop_store_input)
            cfg.set('shopify', 'api_token', shop_token_input)
            write_config(cfg, config_file_path)
            st.success('Settings saved to config.ini')

    with col2:
        st.subheader('Quick tests')
        st.write('Use these buttons to validate that API keys work (short tests).')

        if st.button('Test Gemini LLM'):
            st.info('Testing Gemini LLM...')
            try:
                from utils.llm import LLMClient
                client = LLMClient()
                out = client.generate('Say hi in one sentence', max_tokens=20)
                st.success('Gemini test succeeded')
                st.code(out)
            except Exception as e:
                st.error(f'Gemini test failed: {e}')

        if st.button('Test OpenAI key'):
            st.info('Testing OpenAI API...')
            try:
                from utils.llm import LLMClient
                client = LLMClient(provider='openai')
                out = client.generate('Say hi in one sentence', max_tokens=20)
                st.success('OpenAI test succeeded')
                st.code(out)
            except Exception as e:
                st.error(f'OpenAI test failed: {e}')

        if st.button('Test NewsAPI key'):
            st.info('Testing NewsAPI...')
            try:
                cfg = read_config(config_file_path)
                key = cfg.get('newsapi', {}).get('api_key')
                if not key:
                    raise RuntimeError('No NewsAPI key configured')
                r = requests.get('https://newsapi.org/v2/top-headlines', params={'apiKey': key, 'q': 'shopify', 'pageSize': 1}, timeout=10)
                r.raise_for_status()
                st.success('NewsAPI test succeeded')
                st.json(r.json())
            except Exception as e:
                st.error(f'NewsAPI test failed: {e}')

        if st.button('Test SerpAPI key'):
            st.info('Testing SerpAPI...')
            try:
                cfg = read_config(config_file_path)
                key = cfg.get('serpapi', {}).get('api_key')
                if not key:
                    raise RuntimeError('No SerpAPI key configured')
                r = requests.get('https://serpapi.com/search.json', params={'q': 'shopify trends', 'api_key': key, 'num': 1}, timeout=10)
                r.raise_for_status()
                st.success('SerpAPI test succeeded')
                st.json(r.json())
            except Exception as e:
                st.error(f'SerpAPI test failed: {e}')

# --- Scheduler tab ---
with tabs[1]:
    st.header('Scheduler')
    cfg = read_config(config_file_path)
    if not cfg.has_section('scheduler'):
        cfg.add_section('scheduler')
    start_time = cfg.get('scheduler', {}).get('start_time', '09:00')
    days_per_week = cfg.get('scheduler', {}).get('days_per_week', '3')
    start_time_input = st.time_input('Start time (local)', value=st.time(9, 0))
    days_per_week_input = st.number_input('Days to post per week', min_value=1, max_value=7, value=int(days_per_week))
    if st.button('Save schedule'):
        cfg.set('scheduler', 'start_time', start_time_input.strftime('%H:%M'))
        cfg.set('scheduler', 'days_per_week', str(days_per_week_input))
        write_config(cfg, config_file_path)
        st.success('Scheduler saved')

# --- Dashboard (Keywords) tab ---
with tabs[2]:
    st.header('Keywords Dashboard')
    st.write('Add keywords that the orchestrator will track and create content for.')
    keywords = load_keywords()
    # Convert to list of dicts suitable for experimental_data_editor
    if not isinstance(keywords, list):
        keywords = []
    if len(keywords) == 0:
        keywords = [{'keyword': '', 'priority': 3, 'niche': '', 'tags': '', 'enabled': True}]

    # Use Streamlit's data editor for an editable table
    try:
        edited = st.experimental_data_editor(keywords, num_rows="dynamic", use_container_width=True)
    except Exception:
        # fallback for older Streamlit
        edited = keywords

    col_save, col_imp = st.columns(2)
    with col_save:
        if st.button('Save keywords'):
            save_keywords(edited)
            st.success(f'Saved {len(edited)} keywords to {KEYWORDS_FILE}')
    with col_imp:
        uploaded_csv = st.file_uploader('Import keywords CSV', type=['csv'])
        if uploaded_csv is not None:
            import csv
            text = uploaded_csv.read().decode('utf-8')
            reader = csv.DictReader(text.splitlines())
            rows = [r for r in reader]
            save_keywords(rows)
            st.success(f'Imported {len(rows)} keywords')

# --- Posts tab ---
with tabs[3]:
    st.header('Posts')
    st.write('View drafts and scheduled posts (if db.db exists)')
    db_path = REPO_ROOT / 'db.db'
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT id, title, status, scheduled_at FROM Posts ORDER BY scheduled_at LIMIT 50;")
            rows = cur.fetchall()
            st.write(rows)
            conn.close()
        except Exception as e:
            st.error(f'Error querying Posts table: {e}')
    else:
        st.info('No db.db present — run the orchestrator to create posts')

# --- Logs & Actions tab ---
with tabs[4]:
    st.header('Logs & Actions')
    st.write('Run diagnostics, export logs, or execute actions')
    if st.button('Run orchestrator (dry-run)'):
        st.info('Running orchestrator.auto_publisher.run_once (dry_run=True)...')
        try:
            from orchestrator.auto_publisher import run_once
            out = run_once('shopify', days=2, topics_k=2, snippets_per_topic=2, dry_run=True)
            st.json(out)
        except Exception as e:
            st.error(f'Orchestrator dry-run failed: {e}')

    if st.button('Collect logs (zip)'):
        st.info('Collecting logs...')
        import zipfile, io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            if config_file_path.exists():
                z.writestr('config.ini', config_file_path.read_text())
            if SERVICE_ACCOUNT_PATH.exists():
                z.writestr('service_account.json', SERVICE_ACCOUNT_PATH.read_text())
            if KEYWORDS_FILE.exists():
                z.writestr('keywords.json', KEYWORDS_FILE.read_text())
            if (REPO_ROOT / 'db.db').exists():
                z.write(str(REPO_ROOT / 'db.db'), arcname='db.db')
        buf.seek(0)
        st.download_button('Download logs.zip', data=buf, file_name='logs.zip')

st.markdown('---')
st.markdown('If you need help, paste the error outputs here and I can help you triage them.')
