.DEFAULT_GOAL := all
DIRS = src/
uv = uv run
mypy = mypy


.PHONY: format
format:
	ruff format src
	ruff check src --fix

.PHONY: typecheck
typecheck:
	mypy $(DIRS)

.PHONY: dev
dev:
	uv run fastapi dev src/app.py --port 8088

.PHONY: all
all: format
