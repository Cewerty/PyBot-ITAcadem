#!/bin/sh
set -eu

: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${POSTGRES_USER:?POSTGRES_USER must be set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"

test_database_name="${POSTGRES_DB}_test"

case "${test_database_name}" in
  *[!A-Za-z0-9_]*)
    echo "Refusing to use unsafe test database name: ${test_database_name}" >&2
    exit 1
    ;;
esac

database_exists="$(
  PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    --host=postgres \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --tuples-only \
    --no-align \
    --command="SELECT 1 FROM pg_database WHERE datname = '${test_database_name}';"
)"

if [ "${database_exists}" = "1" ]; then
  exit 0
fi

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  --host=postgres \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --command="CREATE DATABASE \"${test_database_name}\";"
