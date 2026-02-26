PYTHON=./.venv/bin/python

PHONY = help install install-dev format lint type-check secure migrations migrate test test-cov

help:
	@echo "---------------HELP-----------------"
	@echo "To install the project type -> make install"
	@echo "To install the project for development type -> make install-dev"
	@echo "To format code type -> make format"
	@echo "To check linter type -> make lint"
	@echo "To run type checker -> make type-check"
	@echo "To run all security related commands -> make secure"
	@echo "To create database migrations -> make migrations"
	@echo "To run database migrations -> make migrate"
	@echo "To test the project type -> make test"
	@echo "To test with coverage -> make test-cov"
	@echo "------------------------------------"

install:
	uv sync --no-dev

install-dev:
	uv sync

format:
	uv run ruff format src tests

lint:
	uv run ruff check src tests --fix

type-check:
	${PYTHON} -m mypy --check-untyped-defs src

secure:
	${PYTHON} -m bandit -r src --config pyproject.toml

run:
	${PYTHON} -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-config logging.ini

prod:
	${PYTHON} -m gunicorn src.main:app -k uvicorn.workers.UvicornWorker -w 1 -b 0.0.0.0:8000 --access-logfile - --error-logfile -

migrations:
	alembic -c alembic.ini revision --autogenerate

migrate:
	alembic -c alembic.ini upgrade head

test:
	${PYTHON} -m pytest -svvv  tests

test-cov:
	${PYTHON} -m pytest -svvv --cov-report html --cov=src tests