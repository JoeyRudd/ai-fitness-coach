.PHONY: venv install backend dev test lint clean

venv:
	python3 -m venv backend/.venv

install: venv
	. backend/.venv/bin/activate && pip install --upgrade pip && \
	(if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; else pip install -e backend; fi)

backend:
	PYTHONPATH=backend/app backend/.venv/bin/uvicorn app.main:app --reload --app-dir backend

dev: install backend

test:
	. backend/.venv/bin/activate && cd backend && pytest -q

lint:
	. backend/.venv/bin/activate && cd backend && ruff check . || true

clean:
	rm -rf backend/.venv
