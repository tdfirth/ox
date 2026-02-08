.PHONY: lint format typecheck test check

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format --check src/ tests/

typecheck:
	uv run ty check src/

test:
	uv run pytest -v

check: lint format typecheck test
