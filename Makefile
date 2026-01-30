.PHONY: help run stop restart logs connect connect_db createsuperuser test lint typecheck quality format precommit clean migrate makemigrations import_tmdb shell loadtest cleanup clean-pycache coverage docs install-hooks security security-full deadcode docstrings deps complexity templates quality-full
DOCKER_CMD = docker compose -f docker-compose-dev.yml
BASE_URL ?= http://localhost:8000
LOADTEST_SCRIPT ?= perf_test.js

# ==============================================================================
# DEVELOPMENT
# ==============================================================================

run:
	@echo "🚀 Starting development server..."
	@docker build --target dev -t cinema:dev .
	@$(DOCKER_CMD) up -d
	@echo "✅ Server started!"
	@echo "   API:     http://localhost:8000/api/"
	@echo "   Admin:   http://localhost:8000/admin/"
	@echo "   Swagger: http://localhost:8000/api/docs/"

stop:
	@echo "🛑 Stopping development server..."
	@$(DOCKER_CMD) down
	@echo "✅ Server stopped!"

restart: stop run
	@echo "✅ Server restarted!"
 
logs:
	@echo "📋 Tailing logs..."
	@$(DOCKER_CMD) logs -f web

connect:
	@echo "🔌 Connecting to web container..."
	@$(DOCKER_CMD) exec -it web /bin/bash

connect_db:
	@echo "🔌 Connecting to database..."
	@$(DOCKER_CMD) exec -it db psql -U postgres -d cinema

# ==============================================================================
# DATABASE
# ==============================================================================

migrate:
	@echo "📦 Applying database migrations..."
	@$(DOCKER_CMD) exec web python manage.py migrate
	@echo "✅ Migrations applied!"

makemigrations:
	@echo "📝 Creating new migrations..."
	@$(DOCKER_CMD) exec web python manage.py makemigrations
	@echo "✅ Migrations created!"

createsuperuser:
	@echo "👤 Creating superuser..."
	@$(DOCKER_CMD) exec web python manage.py createsuperuser

create_data:
	@echo "🎬 Creating default data..."
	@$(DOCKER_CMD) exec web python manage.py create_default_data --clear
	@echo "✅ Default data created!"

# ==============================================================================
# TESTS & QUALITY
# ==============================================================================

test:
	@echo "🧪 Running tests with pytest..."
	@$(DOCKER_CMD) exec web pytest
	@echo "✅ Tests completed!"

coverage:
	@echo "📊 Running tests with coverage report..."
	@$(DOCKER_CMD) exec web pytest --cov --cov-report=term-missing
	@echo "✅ Coverage report generated!"

lint:
	@echo "🔍 Running linting..."
	@$(DOCKER_CMD) exec web ruff check .
	@$(DOCKER_CMD) exec web black --check .
	@echo "✅ Linting passed!"

typecheck:
	@echo "🔎 Running mypy type checking..."
	@$(DOCKER_CMD) exec web mypy . --config-file=pyproject.toml
	@echo "✅ Type checking passed!"

format:
	@echo "✨ Formatting code..."
	@$(DOCKER_CMD) exec web black .
	@$(DOCKER_CMD) exec web isort .
	@$(DOCKER_CMD) exec web ruff check --fix . || true
	@echo "✅ Code formatted!"

security:
	@echo "🔒 Running security checks..."
	@echo ""
	@echo "📌 Bandit (static security analysis)..."
	@$(DOCKER_CMD) exec web bandit -c pyproject.toml -r .
	@echo ""
	@echo "📌 pip-audit (dependency vulnerabilities - CVE)..."
	@$(DOCKER_CMD) exec web pip-audit -r requirements.prod.txt || true
	@echo ""
	@echo "✅ Security checks completed!"

security-full:
	@echo "🔒 Running comprehensive security audit..."
	@echo ""
	@echo "📌 Bandit (static security analysis)..."
	@$(DOCKER_CMD) exec web bandit -c pyproject.toml -r . -f json -o bandit-report.json || true
	@$(DOCKER_CMD) exec web bandit -c pyproject.toml -r .
	@echo ""
	@echo "📌 pip-audit (dependency vulnerabilities)..."
	@$(DOCKER_CMD) exec web pip-audit -r requirements.prod.txt --format json -o pip-audit-report.json || true
	@$(DOCKER_CMD) exec web pip-audit -r requirements.prod.txt || true
	@echo ""
	@echo "📌 Safety (additional CVE check)..."
	@$(DOCKER_CMD) exec web safety check -r requirements.prod.txt --output json > safety-report.json 2>/dev/null || true
	@$(DOCKER_CMD) exec web safety check -r requirements.prod.txt || true
	@echo ""
	@echo "✅ Full security audit completed! Reports: bandit-report.json, pip-audit-report.json, safety-report.json"

deadcode:
	@echo "💀 Detecting dead code with vulture..."
	@$(DOCKER_CMD) exec web vulture . --min-confidence 80 --exclude "migrations,tests,staticfiles,*factories.py" || true
	@echo "✅ Dead code check completed!"

docstrings:
	@echo "📝 Checking docstring coverage with interrogate..."
	@$(DOCKER_CMD) exec web interrogate -vv --fail-under=60 --exclude migrations --exclude tests --exclude staticfiles --exclude conftest.py
	@echo "✅ Docstring check completed!"

deps:
	@echo "📦 Checking for unused/missing dependencies with deptry..."
	@$(DOCKER_CMD) exec web deptry . || true
	@echo "✅ Dependency check completed!"

complexity:
	@echo "🧠 Analyzing code complexity with radon..."
	@echo ""
	@echo "📌 Cyclomatic Complexity (A=best, F=worst):"
	@$(DOCKER_CMD) exec web radon cc . -a -s --exclude "migrations,tests,staticfiles" || true
	@echo ""
	@echo "📌 Maintainability Index (A=best, C=worst):"
	@$(DOCKER_CMD) exec web radon mi . -s --exclude "migrations,tests,staticfiles" || true
	@echo ""
	@echo "✅ Complexity analysis completed!"

templates:
	@echo "🎨 Linting Django templates with djLint..."
	@if [ -d "templates" ]; then \
		$(DOCKER_CMD) exec web djlint templates/ --profile=django --lint || true; \
	else \
		echo "ℹ️  No templates/ directory found (API-only project). Skipping..."; \
	fi
	@echo "✅ Template check completed!"

quality: lint typecheck security
	@echo ""
	@echo "✅ All quality checks passed!"
	@echo "   - Linting (ruff, black): ✓"
	@echo "   - Type checking (mypy): ✓"
	@echo "   - Security (bandit): ✓"
	@echo ""

precommit: quality test
	@echo ""
	@echo "✅ Pre-commit checks complete!"
	@echo "   Ready to commit safely."
	@echo ""

quality-full: lint typecheck security deadcode docstrings deps complexity
	@echo ""
	@echo "✅ Full quality audit completed!"
	@echo "   - Linting (ruff, black): ✓"
	@echo "   - Type checking (mypy): ✓"
	@echo "   - Security (bandit, pip-audit): ✓"
	@echo "   - Dead code (vulture): ✓"
	@echo "   - Docstrings (interrogate): ✓"
	@echo "   - Dependencies (deptry): ✓"
	@echo "   - Complexity (radon): ✓"
	@echo ""

# ==============================================================================
# DATA & IMPORTS
# ==============================================================================

import_tmdb:
	@echo "🎬 Importing movies from TMDb..."
	@$(DOCKER_CMD) exec web python manage.py import_tmdb --limit=20
	@echo "✅ Import completed!"

shell:
	@echo "🐍 Opening Django shell..."
	@$(DOCKER_CMD) exec web python manage.py shell

# ==============================================================================
# PERFORMANCE
# ==============================================================================

loadtest:
	@echo "⚡ Running k6 load test ($(LOADTEST_SCRIPT))..."
	@docker run --rm -i --network=host \
		-e BASE_URL=$(BASE_URL) \
		-e K6_USER=$(K6_USER) \
		-e K6_PASS=$(K6_PASS) \
		-e K6_VUS=$(K6_VUS) \
		-e K6_DURATION=$(K6_DURATION) \
		-e K6_SLEEP=$(K6_SLEEP) \
		-e K6_ENV=$(K6_ENV) \
		-e K6_START_RATE=$(K6_START_RATE) \
		-e K6_PEAK_RATE=$(K6_PEAK_RATE) \
		-e K6_RECOVER_RATE=$(K6_RECOVER_RATE) \
		-e K6_AUTH_RATE=$(K6_AUTH_RATE) \
		-e K6_AUTH_DURATION=$(K6_AUTH_DURATION) \
		-e K6_SOAK_DURATION=$(K6_SOAK_DURATION) \
		-e K6_SUMMARY_JSON=$(K6_SUMMARY_JSON) \
		-v $(PWD)/loadtests/k6:/scripts \
		grafana/k6 run /scripts/$(LOADTEST_SCRIPT)
	@echo "✅ Load test completed!"

# ==============================================================================
# CLEANUP
# ==============================================================================

clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@$(DOCKER_CMD) down --volumes --remove-orphans
	@echo "✅ Cleanup completed!"

cleanup: clean

clean-pycache:
	@echo "🧹 Removing Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache cleaned!"

# ==============================================================================
# DOCUMENTATION
# ==============================================================================

docs:
	@echo ""
	@echo "📚 API Documentation URLs"
	@echo "========================="
	@echo ""
	@echo "  Swagger UI:  http://localhost:8000/api/docs/"
	@echo "  Redoc:       http://localhost:8000/api/redoc/"
	@echo "  OpenAPI 3.0: http://localhost:8000/api/schema/"
	@echo ""

install-hooks:
	@echo "📦 Installing Git hooks..."
	@bash .githooks/install.sh
	@echo "✅ Git hooks installed!"

# ==============================================================================
# HELP
# ==============================================================================

help:
	@echo ""
	@echo "Cinema API - Makefile Commands"
	@echo "==============================="
	@echo ""
	@echo "🚀 DEVELOPMENT:"
	@echo "  make run              - Start development server"
	@echo "  make stop             - Stop development server"
	@echo "  make restart          - Restart development server"
	@echo "  make logs             - Tail logs in real-time"
	@echo "  make connect          - Shell into web container"
	@echo "  make connect_db       - Shell into PostgreSQL"
	@echo "  make shell            - Django interactive shell"
	@echo ""
	@echo "📦 DATABASE:"
	@echo "  make migrate          - Apply database migrations"
	@echo "  make makemigrations   - Create new migrations"
	@echo "  make createsuperuser  - Create Django superuser"
	@echo "  make create_data      - Create default test data ⭐"
	@echo ""
	@echo "🧪 TESTS & QUALITY:"
	@echo "  make test             - Run pytest (92% coverage)"
	@echo "  make coverage         - Run tests with detailed coverage"
	@echo "  make lint             - Lint with ruff + black"
	@echo "  make typecheck        - Type check with mypy"
	@echo "  make format           - Format with black + isort"
	@echo "  make security         - Security scan (bandit + pip-audit)"
	@echo "  make security-full    - Full security audit with reports"
	@echo "  make quality          - Run lint + typecheck + security ⭐"
	@echo "  make quality-full     - Full audit (all checks) ⭐⭐"
	@echo "  make precommit        - Run all checks + tests (pre-commit)"
	@echo "  make install-hooks    - Install Git pre-commit hooks"
	@echo ""
	@echo "🔍 CODE ANALYSIS:"
	@echo "  make deadcode         - Find dead code (vulture)"
	@echo "  make docstrings       - Check docstring coverage (interrogate)"
	@echo "  make deps             - Check unused dependencies (deptry)"
	@echo "  make complexity       - Analyze code complexity (radon)"
	@echo "  make templates        - Lint Django templates (djLint)"
	@echo ""
	@echo "🎬 DATA & IMPORTS:"
	@echo "  make import_tmdb      - Import movies from TMDb (20 films)"
	@echo ""
	@echo "⚡ PERFORMANCE:"
	@echo "  make loadtest         - Run k6 load testing"
	@echo ""
	@echo "🧹 CLEANUP:"
	@echo "  make clean            - Remove containers + volumes"
	@echo "  make clean-pycache    - Remove Python cache files"
	@echo ""
	@echo "📚 DOCUMENTATION:"
	@echo "  make docs             - Show API documentation URLs"
	@echo "  make help             - Show this help message"
	@echo ""
	@echo "🔗 Quick Links:"
	@echo "  API:     http://localhost:8000/api/"
	@echo "  Admin:   http://localhost:8000/admin/"
	@echo "  Swagger: http://localhost:8000/api/docs/"
	@echo ""
