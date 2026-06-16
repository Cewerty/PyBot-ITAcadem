#!/bin/sh
set -eu

sh scripts/ci/ensure_compose_test_database.sh
uv run pytest --cov=src/pybot --cov-report=term-missing --cov-report=xml --cov-fail-under=80
