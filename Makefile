.PHONY: help install backend frontend dev check-retailers lint

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv, install backend + frontend deps
	python3 -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q -e ".[dev]"
	cd frontend && npm install
	@test -f .env || (cp .env.example .env && echo "Created .env - add your ANTHROPIC_API_KEY")

backend: ## Run the API on :8787
	.venv/bin/uvicorn atelier.main:app --reload --port 8787 --app-dir backend

frontend: ## Run the UI on :5173
	cd frontend && npm run dev

dev: ## Run both (needs two terminals, or use: make dev)
	@echo "Starting backend and frontend..."
	@(.venv/bin/uvicorn atelier.main:app --reload --port 8787 --app-dir backend &) && cd frontend && npm run dev

check-retailers: ## HEAD-request every retailer search URL to find broken templates
	.venv/bin/python scripts/check_retailers.py

lint:
	.venv/bin/ruff check backend scripts
