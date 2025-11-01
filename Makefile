# Makefile for easy development workflows.
# See development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

# =============================================================================
# Variables
# =============================================================================

.DEFAULT_GOAL:=help
.ONESHELL:
.EXPORT_ALL_VARIABLES:
MAKEFLAGS += --no-print-directory

# Define colors and formatting
BLUE := $(shell printf "\033[1;34m")
GREEN := $(shell printf "\033[1;32m")
RED := $(shell printf "\033[1;31m")
YELLOW := $(shell printf "\033[1;33m")
NC := $(shell printf "\033[0m")
INFO := $(shell printf "$(BLUE)ℹ$(NC)")
OK := $(shell printf "$(GREEN)✓$(NC)")
WARN := $(shell printf "$(YELLOW)⚠$(NC)")
ERROR := $(shell printf "$(RED)✖$(NC)")

PYDANTIC_ERRORS_INCLUDE_URL := 0
SRC_PATHS := "src" "tests"
DOC_PATHS := "README.md"

.PHONY: help
help: 		   										## Display this help text for Makefile
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

%:
	@:

# =============================================================================
# Developer Utils
# =============================================================================
.PHONY: install-uv
install-uv: 										## Install latest version of uv
	@echo "${INFO} Installing uv..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
	@echo "${OK} UV installed successfully 📦"

.PHONY: install
install:												## Install the project, dependencies, and pre-commit for local development
	@echo "${INFO} Starting installation..."
	@uv sync --all-extras
	@echo "${OK} Installation complete! 🎉"

.PHONY: upgrade
upgrade:       									## Upgrade all dependencies to the latest stable versions
	@echo "${INFO} Updating all dependencies 🆙"
	@uv sync --upgrade --all-extras
	@echo "${OK} Dependencies Updated 🎉"

# =============================================================================
# Tests, Linting, Coverage
# =============================================================================
.PHONY: lint
lint:
	@echo "${INFO} Running ruff checks... 🔎"
	@uv run ruff check --exit-non-zero-on-fix ${SRC_PATHS}
	@echo "${OK} Ruff checks complete ✨"
	@echo "${INFO} Running ruff format... 🔧"
	@uv run ruff format --check ${SRC_PATHS}
	@echo "${OK} Ruff format complete ✨"
	@echo "${INFO} Running basedpyright... 🌀"
	@uv run basedpyright --stats ${SRC_PATHS}
	@echo "${OK} Basedpyright complete ✨"

.PHONY: format
fmt format: 										## Runs code formatting utilities
	@echo "${INFO} Running code formatters... 🔧"
	@uv run ruff format ${SRC_PATHS}
	@echo "${OK} Code formatting complete 📐"

.PHONY: test
test:  													## Run the tests
	@echo "${INFO} Running all test cases... 🧪"
	@uv run pytest
	@echo "${OK} All tests passed 🏅"

.PHONY: coverage
coverage:  											## Run the tests and generate coverage report
	@echo "${INFO} Running tests with coverage... 📊"
	@make test-db
	@uv run pytest tests --cov=src --cov-report=term-missing:skip-covered --cov-report=html --cov-config=pyproject.toml --no-cov-on-fail
	@echo "${OK} Coverage report generated ✅"

.PHONY: build
build:
	@echo "${INFO} Running build... 🚀"
	@uv build
	@echo "${OK} Project is built 📦"

agent-rules: CLAUDE.md AGENTS.md QWEN.md

# Use .cursor/rules for sources of rules.
# Create Claude and Codex rules from these.
CLAUDE.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	cat .cursor/rules/general.mdc .cursor/rules/python.mdc > CLAUDE.md

AGENTS.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	cat .cursor/rules/general.mdc .cursor/rules/python.mdc > AGENTS.md

QWEN.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	cat .cursor/rules/general.mdc .cursor/rules/python.mdc > QWEN.md

.PHONY: clean
clean: 												## Cleanup temporary build artifacts
	@echo "${INFO} Cleaning working directory... ♻️"
	@rm -rf .pytest_cache .ruff_cache .hypothesis build/ -rf dist/ .eggs/ .coverage coverage.xml coverage.json htmlcov/ .mypy_cache .ropeproject/
	@rm -rf CLAUDE.md AGENTS.md QWEN.md
	@find . -name '*.egg-info' -exec rm -rf {} +
	@find . -name '*.egg' -exec rm -f {} +
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -rf {} +
	@find . -name '.ipynb_checkpoints' -exec rm -rf {} +
	@echo "${OK} Working directory cleaned 🧹"
