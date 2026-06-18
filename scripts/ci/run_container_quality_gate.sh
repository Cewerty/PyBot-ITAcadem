#!/bin/sh
set -eu

uv run ruff format --check --diff .
uv run ruff check .
uv run ty check --python=/opt/pybot-tooling/.venv --output-format github --target-version 3.14 src/ tests/
uv run --frozen tach check
sh scripts/ci/run_container_test_coverage.sh
