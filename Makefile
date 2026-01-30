# HydroQ-QC-Assistant Makefile
# Common commands for development and testing

.PHONY: help setup-db setup-api setup-web dev-api dev-web dev test lint clean demo

# Default target
help:
	@echo "HydroQ-QC-Assistant Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup-db      - Initialize PostgreSQL database"
	@echo "  make setup-api     - Setup Python virtual environment and install dependencies"
	@echo "  make setup-web     - Install frontend dependencies"
	@echo "  make setup-all     - Run all setup commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev-api       - Start FastAPI backend in development mode"
	@echo "  make dev-web       - Start Vite frontend in development mode"
	@echo "  make dev           - Start both backend and frontend (requires tmux)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-api      - Run backend tests only"
	@echo "  make test-web      - Run frontend tests only"
	@echo ""
	@echo "Demo:"
	@echo "  make demo          - Generate sample data and run demo"
	@echo "  make sample-data   - Generate sample bathymetry dataset"
	@echo ""
	@echo "Utilities:"
	@echo "  make lint          - Run linters on all code"
	@echo "  make clean         - Remove generated files and caches"
	@echo "  make migrate       - Run database migrations"
	@echo "  make migrate-new   - Create new migration (name=MIGRATION_NAME)"

# =============================================================================
# SETUP
# =============================================================================

setup-db:
	@echo "Setting up PostgreSQL database..."
	createdb hydroq_qc 2>/dev/null || echo "Database already exists"
	psql -d hydroq_qc -f infra/db/init.sql

setup-api:
	@echo "Setting up Python API..."
	cd apps/api && python -m venv venv
	cd apps/api && . venv/bin/activate && pip install -r requirements.txt
	cd apps/api && . venv/bin/activate && alembic upgrade head

setup-web:
	@echo "Setting up React frontend..."
	cd apps/web && npm install

setup-all: setup-db setup-api setup-web
	@echo "All services setup complete!"

# =============================================================================
# DEVELOPMENT
# =============================================================================

dev-api:
	cd apps/api && . venv/bin/activate && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd apps/web && npm run dev

dev:
	@echo "Starting all services..."
	@tmux new-session -d -s hydroq 'make dev-api' \; split-window -h 'make dev-web' \; attach

# =============================================================================
# TESTING
# =============================================================================

test: test-api test-web

test-api:
	cd apps/api && . venv/bin/activate && pytest -v

test-web:
	cd apps/web && npm test

# =============================================================================
# DATABASE
# =============================================================================

migrate:
	cd apps/api && . venv/bin/activate && alembic upgrade head

migrate-new:
	@if [ -z "$(name)" ]; then echo "Usage: make migrate-new name=MIGRATION_NAME"; exit 1; fi
	cd apps/api && . venv/bin/activate && alembic revision --autogenerate -m "$(name)"

# =============================================================================
# DEMO
# =============================================================================

sample-data:
	cd apps/api && . venv/bin/activate && python ../scripts/generate_sample_data.py

demo: sample-data
	@echo "Sample data generated. Start the servers with 'make dev' and open http://localhost:5173"

# =============================================================================
# UTILITIES
# =============================================================================

lint:
	cd apps/api && . venv/bin/activate && ruff check src tests
	cd apps/web && npm run lint

clean:
	@echo "Cleaning generated files..."
	rm -rf apps/api/__pycache__
	rm -rf apps/api/src/__pycache__
	rm -rf apps/api/.pytest_cache
	rm -rf apps/api/venv
	rm -rf apps/web/node_modules
	rm -rf apps/web/dist
	rm -rf data/outputs/*
	rm -rf data/uploads/*
	@echo "Clean complete!"
