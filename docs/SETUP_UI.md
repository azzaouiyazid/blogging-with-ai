# Local Setup UI — Streamlit

This document describes the Streamlit-based local Setup UI included in the repository (tools/setup_ui.py). The UI provides a human-friendly way to create and validate config.ini, validate LLM credentials (Gemini), run discovery/retrieval/page-extraction smoke tests, inspect and migrate the SQLite DB, and run the orchestrator in dry-run mode.

Important: Do NOT commit your config.ini or service-account JSON to the repository. Keep them local and add them to .gitignore.

Quick start

1. Checkout the feature branch that contains the UI:

   git fetch origin
   git checkout feat/gemini-llm

2. Create and activate a virtual environment and install requirements:

   python -m venv .venv
   source .venv/bin/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   pip install streamlit

3. Prepare credentials (recommended):

   - Create a Google Cloud service account, enable the Generative AI API for your project, and grant the service account the necessary role(s) (e.g., "Cloud Generative AI API User" or cloud-platform for quick testing).
   - Download the service account JSON key file and keep it on your local machine.

4. Create config.ini at the repository root or use the UI's form to create one. Minimal LLM-related fields:

   [llm]
   provider = gemini

   [gemini]
   service_account_file = /full/path/to/service-account.json
   model = text-bison-001

   (You can also supply gemini.api_key for quick tests but service-account auth is recommended for production.)

5. Run the Setup UI:

   streamlit run tools/setup_ui.py

   Open http://localhost:8501 in your browser.

UI features

- Edit / create config.ini: form fields for LLM (Gemini/OpenAI), NewsAPI, SerpAPI, Shopify, Telegram, Unsplash. Saves to repo-root config.ini.
- LLM validation: calls the configured LLM provider. If a service-account file is configured, the UI mints a bearer token and uses the Generative API.
- Discovery test: runs discovery.trends.discover_topics(niche).
- SERP fetch test: runs retrieval.serp.fetch_top_results(query).
- Page fetch & extract: runs retrieval.fetcher.fetch_and_extract(url) and shows extraction results or robots.txt errors.
- Orchestrator dry-run: runs orchestrator.auto_publisher.run_once(..., dry_run=True) to exercise the end-to-end pipeline without publishing to Shopify.
- DB inspector & migration: view the Posts table in db.db and run scripts/sqlite_migrate_posts.py from the UI.
- Telegram test: send a review message via your configured Telegram bot and review_chat_id.

Troubleshooting

- Missing google-auth libraries: install requirements.txt; the setup UI uses google-auth to mint tokens from a service-account JSON.
- Permission errors: ensure the service account has the Generative AI API enabled in the project and sufficient IAM roles.
- Empty LLM output: inspect the raw HTTP error shown in the UI; the Gemini response shape may vary by API version — copy the JSON response and we can adapt the parser.
- Robots.txt: fetcher respects robots.txt. If a URL is disallowed, try another site or adjust tests.

Security

- Keep config.ini and service-account JSON offline and out of version control. Add them to .gitignore.
- For production, prefer service-account JSON and the official client libraries (google-auth, google-generativeai). The UI supports service-account auth and shows how to validate it.

Advanced options (future improvements)

- Add an encrypted local store for service-account JSON with a passphrase in the UI.
- Provide a one-click installer script to create venv and install requirements.
- Provide a Docker Compose development stack including the UI and optional ngrok for webhook testing.

