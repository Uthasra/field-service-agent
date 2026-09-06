#!/usr/bin/env bash
# One-shot local setup. Run from the repo root: bash scripts/setup.sh
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

[ -f .env ] || { cp .env.example .env; echo "created .env — add your API key"; }

python -m app.rag.index
python -m app.db

echo
echo "setup done. start the server with:"
echo "  source .venv/bin/activate && uvicorn app.main:app --reload"
