.PHONY: lint format typecheck test check install

install:
	uv sync --extra dev

lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy src

test:
	uv run pytest tests/ -v

check: lint typecheck test
