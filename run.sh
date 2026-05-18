#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

.venv/bin/pip install -q -r requirements.txt

echo "Starting arXiv Batch Downloader at http://localhost:5000"
.venv/bin/python app.py
