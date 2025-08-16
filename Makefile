.PHONY: venv install backend dev test lint clean ci-install ci-test ci-lint

venv:
	python3 -m venv backend/.venv

install: venv
	. backend/.venv/bin/activate && pip install --upgrade pip && \
	(if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; else pip install -e backend; fi)

backend:
	PYTHONPATH=backend/app backend/.venv/bin/uvicorn app.main:app --reload --app-dir backend

dev: install backend

test:
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. pytest -q

lint:
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. ruff check . || true

clean:
	rm -rf backend/.venv

ci-install:
	. backend/.venv/bin/activate && pip install --upgrade pip
	. backend/.venv/bin/activate && pip install -r requirements.txt
	. backend/.venv/bin/activate && pip install pytest pytest-asyncio ruff black isort mypy

ci-test:
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. pytest -v

ci-lint:
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. ruff check . || echo "Ruff found issues"
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. black --check . || echo "Black formatting issues found"
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. isort --check-only . || echo "Import sorting issues found"
	. backend/.venv/bin/activate && cd backend && PYTHONPATH=. mypy . || echo "Type checking issues found"
