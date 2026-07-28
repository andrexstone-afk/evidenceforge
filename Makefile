.PHONY: install lint format-check typecheck test check run demo

install:
	uv sync --extra dev

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy src

test:
	uv run pytest

check: lint format-check typecheck test

run:
	uv run evidenceforge serve

demo:
	uv run streamlit run streamlit_app/app.py
