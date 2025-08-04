# Makefile
.PHONY: help install install-dev test test-unit test-integration test-e2e lint format type-check security-check pre-commit run run-dev run-prod build docker-build docker-run clean

# Default target
help: ## Show this help message
	@echo "EliteDynamicsAPI - Enterprise Development Commands"
	@echo "================================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -e ".[dev,test,docs]"
	pre-commit install

# Testing
test: ## Run all tests
	ENVIRONMENT=testing pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	ENVIRONMENT=testing pytest tests/unit/ -v

test-integration: ## Run integration tests only
	ENVIRONMENT=testing pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests only
	ENVIRONMENT=testing pytest tests/e2e/ -v

test-watch: ## Run tests in watch mode
	ENVIRONMENT=testing pytest-watch tests/

# Code Quality
lint: ## Run linting checks
	flake8 app tests
	mypy app

format: ## Format code with black and isort
	black app tests
	isort app tests

format-check: ## Check code formatting
	black --check app tests
	isort --check-only app tests

type-check: ## Run type checking
	mypy app

security-check: ## Run security checks
	bandit -r app/ -f json -o security-report.json
	bandit -r app/

pre-commit: ## Run pre-commit hooks
	pre-commit run --all-files

# Development
run: ## Run the application in development mode
	python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-dev: ## Run the application with debug logging
	ENVIRONMENT=development LOG_LEVEL=DEBUG python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Run the application in production mode
	ENVIRONMENT=production gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker
docker-build: ## Build Docker image
	docker build -t elitedynamics-api:latest .

docker-build-prod: ## Build production Docker image
	docker build --target production -t elitedynamics-api:prod .

docker-run: ## Run Docker container
	docker run -p 8000:8000 -e ENVIRONMENT=development elitedynamics-api:latest

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down

docker-compose-logs: ## View docker-compose logs
	docker-compose logs -f

# Database & Migrations (if needed in future)
db-upgrade: ## Run database migrations
	@echo "Database migrations not implemented yet"

db-downgrade: ## Rollback database migrations
	@echo "Database migrations not implemented yet"

# Documentation
docs-serve: ## Serve documentation locally
	mkdocs serve

docs-build: ## Build documentation
	mkdocs build

docs-deploy: ## Deploy documentation
	mkdocs gh-deploy

# Utilities
clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

health-check: ## Check API health
	curl -f http://localhost:8000/health || echo "API is not running"

detailed-health-check: ## Check detailed API health
	curl -f http://localhost:8000/api/v1/health | jq . || echo "API is not running"

# CI/CD
ci-test: ## Run tests for CI/CD
	ENVIRONMENT=testing pytest tests/ -v --cov=app --cov-report=xml --cov-report=term

ci-lint: ## Run linting for CI/CD
	flake8 app tests --exit-zero
	mypy app --ignore-missing-imports

ci-security: ## Run security checks for CI/CD
	bandit -r app/ -f json -o security-report.json || true

# Environment setup
setup-dev: install-dev ## Setup development environment
	@echo "Development environment setup complete!"
	@echo "Run 'make run-dev' to start the development server"

setup-prod: install ## Setup production environment
	@echo "Production environment setup complete!"
	@echo "Run 'make run-prod' to start the production server"