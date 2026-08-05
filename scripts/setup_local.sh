#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

echo "Creating virtual environment at $VENV"
python3 -m venv "$VENV"

# shellcheck disable=SC1090
source "$VENV/bin/activate"

echo "Upgrading pip and installing requirements"
python -m pip install --upgrade pip
if [ -f "$REPO_ROOT/requirements.txt" ]; then
  pip install -r "$REPO_ROOT/requirements.txt"
else
  echo "requirements.txt not found in repo root; skipping pip install -r requirements.txt"
fi

# Install Streamlit for the UI
pip install streamlit

cat <<'EOF'

Setup completed.

To run the Setup UI:
  source ".venv/bin/activate"
  streamlit run tools/setup_ui.py

Optional: install pandoc for full markdown <-> html/text conversions (pypandoc wrapper):
  - macOS (Homebrew): brew install pandoc
  - Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y pandoc
  - Windows: download from https://pandoc.org/installing.html

Security note: Do NOT commit config.ini or any service-account JSON files to the repository. Add them to .gitignore.

EOF
