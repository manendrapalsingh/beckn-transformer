# Schema Transformer - Makefile
# =============================

SHELL := /bin/bash
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTHON_VENV := $(VENV_BIN)/python

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help install setup venv deps run server test test-strict sync-schemas generate-responses clean clean-cache clean-ast-cache clean-schema-cache clean-all lint format check rebuild-asts cache-stats

# Default target
help:
	@echo ""
	@echo "$(GREEN)Schema Transformer - Available Commands$(NC)"
	@echo "========================================="
	@echo ""
	@echo "$(YELLOW)Setup:$(NC)"
	@echo "  make install          - Full setup (venv + dependencies + env file)"
	@echo "  make venv             - Create virtual environment"
	@echo "  make deps             - Install dependencies"
	@echo "  make setup-env        - Create .env from .env.example"
	@echo ""
	@echo "$(YELLOW)Run:$(NC)"
	@echo "  make run              - Start the API server"
	@echo "  make server           - Alias for 'make run'"
	@echo "  make run-dev          - Start server with auto-reload"
	@echo ""
	@echo "$(YELLOW)Testing:$(NC)"
	@echo "  make test             - Run all integration tests"
	@echo "  make test-strict      - Run tests in strict mode"
	@echo "  make test-single T=x  - Run single test (e.g., make test-single T=transform_support)"
	@echo "  make test-save        - Run tests and save results"
	@echo ""
	@echo "$(YELLOW)Schema Management:$(NC)"
	@echo "  make sync-schemas     - Sync test payloads from cached schemas"
	@echo "  make generate-responses - Generate expected responses from API"
	@echo "  make refresh-schemas  - Refresh schemas from GitHub"
	@echo ""
	@echo "$(YELLOW)Cache Management:$(NC)"
	@echo "  make cache-stats      - Show AST cache statistics"
	@echo "  make clean-ast-cache  - Clear AST cache only (force rebuild)"
	@echo "  make clean-schema-cache - Clear schema cache only"
	@echo "  make rebuild-asts     - Force rebuild all ASTs"
	@echo ""
	@echo "$(YELLOW)Cleanup:$(NC)"
	@echo "  make clean            - Remove Python cache files"
	@echo "  make clean-cache      - Remove all caches (schemas + ASTs)"
	@echo "  make clean-responses  - Remove generated response files"
	@echo "  make clean-all        - Full cleanup (cache + pycache + venv)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  make lint             - Check code with linters"
	@echo "  make format           - Format code"
	@echo "  make check            - Run all checks (lint + test)"
	@echo ""

# ============================================
# Setup Commands
# ============================================

venv:
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)✓ Virtual environment created$(NC)"

deps: venv
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

setup-env:
	@if [ ! -f .env ]; then \
		echo "$(GREEN)Creating .env from env.example...$(NC)"; \
		cp env.example .env; \
		echo "$(GREEN)✓ .env file created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env already exists, skipping$(NC)"; \
	fi

install: venv deps setup-env
	@echo ""
	@echo "$(GREEN)✓ Installation complete!$(NC)"
	@echo ""
	@echo "To activate the virtual environment:"
	@echo "  source $(VENV)/bin/activate"
	@echo ""
	@echo "To start the server:"
	@echo "  make run"

# ============================================
# Run Commands
# ============================================

run:
	@echo "$(GREEN)Starting API server...$(NC)"
	$(PYTHON_VENV) -m src.main

server: run

run-dev:
	@echo "$(GREEN)Starting API server with auto-reload...$(NC)"
	$(VENV_BIN)/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ============================================
# Testing Commands
# ============================================

test:
	@echo "$(GREEN)Running integration tests...$(NC)"
	cd integration_test && ../$(PYTHON_VENV) test_integration.py

test-strict:
	@echo "$(GREEN)Running integration tests (strict mode)...$(NC)"
	cd integration_test && ../$(PYTHON_VENV) test_integration.py --strict

test-single:
	@if [ -z "$(T)" ]; then \
		echo "$(RED)Error: Specify test name with T=<test_name>$(NC)"; \
		echo "Example: make test-single T=transform_support"; \
		exit 1; \
	fi
	@echo "$(GREEN)Running test: $(T)$(NC)"
	cd integration_test && ../$(PYTHON_VENV) test_integration.py --test $(T)

test-save:
	@echo "$(GREEN)Running tests and saving results...$(NC)"
	cd integration_test && ../$(PYTHON_VENV) test_integration.py --save

# ============================================
# Schema Management Commands
# ============================================

sync-schemas:
	@echo "$(GREEN)Syncing test payloads from cached schemas...$(NC)"
	cd integration_test && ../$(PYTHON_VENV) sync_from_schemas.py

generate-responses:
	@echo "$(GREEN)Generating expected responses from API...$(NC)"
	@echo "$(YELLOW)Note: Make sure the API server is running!$(NC)"
	cd integration_test && ../$(PYTHON_VENV) generate_response_templates.py

refresh-schemas:
	@echo "$(GREEN)Refreshing schemas from GitHub...$(NC)"
	curl -s -X POST http://localhost:8000/refresh-schemas | $(PYTHON_VENV) -m json.tool

list-schemas:
	@echo "$(GREEN)Listing available schemas...$(NC)"
	curl -s http://localhost:8000/schemas | $(PYTHON_VENV) -m json.tool

health:
	@echo "$(GREEN)Checking API health...$(NC)"
	curl -s http://localhost:8000/health | $(PYTHON_VENV) -m json.tool

# ============================================
# Cleanup Commands
# ============================================

clean:
	@echo "$(GREEN)Removing Python cache files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

clean-cache:
	@echo "$(GREEN)Removing all caches (schemas + ASTs)...$(NC)"
	rm -rf cache/schemas/*.json 2>/dev/null || true
	rm -rf cache/asts/*.json 2>/dev/null || true
	@echo "$(GREEN)✓ All caches cleaned$(NC)"

clean-ast-cache:
	@echo "$(GREEN)Removing AST cache...$(NC)"
	rm -rf cache/asts/*.json 2>/dev/null || true
	@echo "$(GREEN)✓ AST cache cleaned$(NC)"

clean-schema-cache:
	@echo "$(GREEN)Removing schema cache...$(NC)"
	rm -rf cache/schemas/*.json 2>/dev/null || true
	@echo "$(GREEN)✓ Schema cache cleaned$(NC)"

cache-stats:
	@echo "$(GREEN)Cache Statistics:$(NC)"
	@echo "Schema cache:"
	@ls -la cache/schemas/*.json 2>/dev/null | wc -l | xargs -I {} echo "  Files: {}"
	@du -sh cache/schemas 2>/dev/null | cut -f1 | xargs -I {} echo "  Size: {}" || echo "  Size: 0"
	@echo "AST cache:"
	@ls -la cache/asts/*.json 2>/dev/null | wc -l | xargs -I {} echo "  Files: {}"
	@du -sh cache/asts 2>/dev/null | cut -f1 | xargs -I {} echo "  Size: {}" || echo "  Size: 0"

rebuild-asts:
	@echo "$(GREEN)Rebuilding all ASTs...$(NC)"
	@rm -rf cache/asts/*.json 2>/dev/null || true
	@echo "$(YELLOW)AST cache cleared. ASTs will rebuild on next server start.$(NC)"
	@echo "Run 'make run' to rebuild ASTs."

clean-responses:
	@echo "$(GREEN)Removing generated response files...$(NC)"
	rm -rf integration_test/responses/*.json 2>/dev/null || true
	@echo "$(GREEN)✓ Response files cleaned$(NC)"

clean-venv:
	@echo "$(GREEN)Removing virtual environment...$(NC)"
	rm -rf $(VENV)
	@echo "$(GREEN)✓ Virtual environment removed$(NC)"

clean-all: clean clean-cache clean-venv
	@echo "$(GREEN)✓ Full cleanup complete$(NC)"

# ============================================
# Development Commands
# ============================================

lint:
	@echo "$(GREEN)Running linters...$(NC)"
	$(PYTHON_VENV) -m py_compile src/**/*.py || true
	@echo "$(GREEN)✓ Lint check complete$(NC)"

format:
	@echo "$(GREEN)Formatting code...$(NC)"
	@if $(PIP) show black > /dev/null 2>&1; then \
		$(VENV_BIN)/black src/ integration_test/; \
	else \
		echo "$(YELLOW)Black not installed. Install with: pip install black$(NC)"; \
	fi

check: lint test
	@echo "$(GREEN)✓ All checks passed$(NC)"

# ============================================
# Quick Workflow Commands
# ============================================

# Full test workflow: sync schemas, generate responses, run tests
full-test: sync-schemas
	@echo ""
	@echo "$(YELLOW)Starting API server in background for response generation...$(NC)"
	@$(PYTHON_VENV) -m src.main &
	@sleep 3
	@$(MAKE) generate-responses
	@pkill -f "src.main" || true
	@echo ""
	@$(MAKE) test-strict

# Development workflow: start server and watch for changes
dev: run-dev

