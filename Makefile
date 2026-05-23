.PHONY: lint format typecheck test check install

install:
	uv sync --extra dev

lint:
	uv run --extra dev ruff check src tests

format:
	uv run --extra dev ruff format src tests

typecheck:
	uv run --extra dev mypy src

test:
	uv run --extra dev pytest tests/ -v

check: lint typecheck test
