#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -d .venv ]; then
  echo "Existing venv detected: backend/.venv" >&2
else
  python3 -m venv .venv
  echo "Created venv at backend/.venv" >&2
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
elif [ -f pyproject.toml ]; then
  pip install -e .
fi
echo "Venv ready. Activate with: source backend/.venv/bin/activate" >&2
