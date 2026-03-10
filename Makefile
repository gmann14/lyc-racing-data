# LYC Racing Data — Pipeline Orchestrator
#
# Usage:
#   make export          # Re-export all JSON from current DB (most common)
#   make export-only T=analysis  # Export just analysis.json
#   make build           # Export JSON + build Next.js site
#   make fresh           # Full rebuild: wipe DB, reload, re-export, build
#   make validate        # Run pre-deploy validation checks
#   make deploy          # Export + build + validate + push
#   make test            # Run all Python tests

SHELL := /bin/bash
.ONESHELL:

VENV := source .venv/bin/activate
DB := lyc_racing.db

.PHONY: help export export-only build fresh validate deploy test clean-ds-store weather

help:
	@echo "LYC Racing Data Pipeline"
	@echo ""
	@echo "  make export          Re-export all JSON from current DB"
	@echo "  make export-only T=analysis   Export a subset (analysis, boats, events, etc.)"
	@echo "  make build           Export JSON + build Next.js site"
	@echo "  make fresh           Full rebuild: wipe DB, reload everything, re-export"
	@echo "  make validate        Run pre-deploy validation checks"
	@echo "  make deploy          Export + build + validate + push to main"
	@echo "  make test            Run all Python tests"
	@echo "  make weather         Backfill weather (uses cache, fast)"
	@echo "  make weather-fetch   Re-fetch all weather from API (slow, ~13min)"

# Remove .DS_Store files that can cause issues
clean-ds-store:
	@find web/public/data -name .DS_Store -delete 2>/dev/null || true

# Re-export all JSON from current database
export: clean-ds-store
	$(VENV) && cd scraper && python export_json.py

# Export a subset: make export-only T="analysis boats"
export-only: clean-ds-store
	@if [ -z "$(T)" ]; then echo "Usage: make export-only T=\"analysis boats\""; exit 1; fi
	$(VENV) && cd scraper && python export_json.py --only $(T)

# Backfill weather using local cache (fast)
weather:
	$(VENV) && cd scraper && python backfill_weather.py

# Re-fetch all weather from API (slow)
weather-fetch:
	$(VENV) && cd scraper && python backfill_weather.py --force-fetch

# Full rebuild from scratch
fresh: clean-ds-store
	$(VENV) && cd scraper && python load_db.py --fresh
	$(VENV) && cd scraper && python export_json.py
	@echo ""
	@echo "Full rebuild complete. Run 'make build' to build the site."

# Build Next.js static site
build: export
	cd web && npm run build

# Run all Python tests
test:
	$(VENV) && python -m pytest tests/ -q

# Pre-deploy validation
validate:
	@echo "Running pre-deploy validation..."
	@$(VENV) && python scraper/validate.py

# Full deploy: export + build + validate + push
deploy: build validate
	git add web/public/data/
	@if git diff --cached --quiet; then \
		echo "No data changes to commit."; \
	else \
		git commit -m "chore: regenerate JSON data"; \
	fi
	git push
	@echo "Deployed to GitHub Pages."
