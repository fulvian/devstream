# DevStream Development Makefile
# Quick commands for common development tasks

.PHONY: help install dev test lint format check setup clean docs

# Default target
help: ## Show this help message
	@echo "DevStream Development Commands"
	@echo "============================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation and setup
install: ## Install dependencies with Poetry
	poetry install --all-extras

dev: ## Install development dependencies
	poetry install --all-extras --with dev,test,performance
	poetry run pre-commit install

setup: ## Run development environment setup
	poetry run python scripts/setup_dev.py setup

check-env: ## Check development environment
	poetry run python scripts/setup_dev.py check

# Code quality
format: ## Format code with black and isort
	poetry run black src tests scripts
	poetry run isort src tests scripts

lint: ## Run all linters
	poetry run ruff check src tests
	poetry run mypy src
	poetry run bandit -r src

check: format lint ## Format and lint code

# Testing
test: ## Run all tests
	poetry run pytest

test-unit: ## Run unit tests only
	poetry run pytest tests/unit -v

test-integration: ## Run integration tests
	poetry run pytest tests/integration -v --requires-ollama

test-e2e: ## Run end-to-end tests
	poetry run pytest tests/e2e -v --requires-ollama --requires-docker

test-coverage: ## Run tests with coverage report
	poetry run pytest --cov=devstream --cov-report=html --cov-report=term

test-performance: ## Run performance benchmarks
	poetry run pytest tests/unit -v --benchmark-only

# Development utilities
clean: ## Clean up temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf build/ dist/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/

docs: ## Generate documentation
	poetry run mkdocs serve

docs-build: ## Build documentation
	poetry run mkdocs build

# Database operations
db-init: ## Initialize database with schema
	poetry run python -c "from src.devstream.database.connection import DatabaseManager; import asyncio; asyncio.run(DatabaseManager.create_schema())"

db-migrate: ## Run database migrations
	poetry run devstream-migrate

db-reset: ## Reset database (WARNING: destroys data)
	rm -f data/*.db data/*.db-*
	$(MAKE) db-init

# Ollama operations
ollama-models: ## Install recommended Ollama models
	poetry run python scripts/setup_dev.py install-ollama-models

ollama-check: ## Check Ollama connectivity
	curl -s http://localhost:11434/api/tags | python -m json.tool

# CI/CD
ci-install: ## Install for CI environment
	poetry install --only=main,test

ci-test: ## Run CI test suite
	poetry run pytest tests/ --tb=short --maxfail=5

ci-lint: ## Run CI linting
	poetry run ruff check src tests --output-format=github
	poetry run mypy src --no-error-summary

# Release
build: ## Build package
	poetry build

version: ## Show current version
	poetry version

version-patch: ## Bump patch version
	poetry version patch

version-minor: ## Bump minor version
	poetry version minor

# Docker development
docker-build: ## Build Docker development image
	docker build -t devstream:dev .

docker-run: ## Run in Docker container
	docker run -it --rm \
		-v $(PWD):/workspace \
		-p 8000:8000 \
		devstream:dev

# Performance monitoring
profile: ## Run performance profiling
	poetry run python -m cProfile -o profile.stats -m devstream.cli.main --help
	poetry run python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

memory-profile: ## Run memory profiling
	poetry run mprof run python -m devstream.cli.main --help
	poetry run mprof plot

# Development shortcuts
quick-test: ## Quick test run (unit only, no coverage)
	poetry run pytest tests/unit -x -q

watch-tests: ## Watch files and run tests automatically
	poetry run ptw --runner "pytest tests/unit -x -q"

dev-server: ## Start development server with hot reload
	poetry run python -m devstream.cli.main serve --reload

# Debugging utilities
debug-config: ## Show current configuration
	poetry run python -c "from devstream.core.config import DevStreamConfig; print(DevStreamConfig.from_env().json(indent=2))"

debug-deps: ## Check dependency tree
	poetry show --tree

debug-env: ## Show environment information
	@echo "Python: $(shell python --version)"
	@echo "Poetry: $(shell poetry --version)"
	@echo "Platform: $(shell uname -a)"
	@echo "Working directory: $(PWD)"