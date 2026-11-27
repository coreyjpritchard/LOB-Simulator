# Regenerate tests, the headline figure and docs/results.csv. Needs uv.
.PHONY: reproduce sync test figures

reproduce: sync test figures

sync:
	uv sync --extra dev

test:
	uv run pytest

figures:
	uv run python -m lobsim.figures
