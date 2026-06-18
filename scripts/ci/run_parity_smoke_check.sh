#!/usr/bin/env bash
set -euo pipefail

compose_files=(
  -f docker-compose.yml
  -f docker-compose.ci.parity.override.yml
)

profile_args=(--profile health)
required_services=(bot taskiq-worker taskiq-scheduler postgres redis health)

print_debug() {
  echo "::group::Parity smoke-check docker compose ps"
  docker compose "${compose_files[@]}" "${profile_args[@]}" ps || true
  echo "::endgroup::"

  echo "::group::Parity smoke-check docker compose logs"
  docker compose "${compose_files[@]}" "${profile_args[@]}" logs --no-color --tail 200 || true
  echo "::endgroup::"
}

cleanup() {
  docker compose "${compose_files[@]}" "${profile_args[@]}" down -v --remove-orphans || true
}

trap cleanup EXIT

docker compose "${compose_files[@]}" up -d --wait --wait-timeout 120 postgres redis
docker compose "${compose_files[@]}" --profile migration run --rm --build migrate
docker compose "${compose_files[@]}" "${profile_args[@]}" up -d --build \
  bot taskiq-worker taskiq-scheduler health

for attempt in {1..30}; do
  running_services="$(docker compose "${compose_files[@]}" "${profile_args[@]}" ps --services --status running || true)"
  missing_services=()

  for service in "${required_services[@]}"; do
    if ! grep -qx "${service}" <<<"${running_services}"; then
      missing_services+=("${service}")
    fi
  done

  if [[ ${#missing_services[@]} -eq 0 ]]; then
    break
  fi

  if [[ ${attempt} -eq 30 ]]; then
    echo "Parity runtime did not reach running state for services: ${missing_services[*]}" >&2
    print_debug
    exit 1
  fi

  sleep 3
done

if ! curl --fail --silent --show-error --retry 20 --retry-all-errors --retry-delay 3 \
  http://127.0.0.1:8001/ >/dev/null; then
  echo "Liveness probe failed for local parity health endpoint" >&2
  print_debug
  exit 1
fi

if ! curl --fail --silent --show-error --retry 20 --retry-all-errors --retry-delay 3 \
  http://127.0.0.1:8001/ready >/dev/null; then
  echo "Readiness probe failed for local parity health endpoint" >&2
  print_debug
  exit 1
fi

docker compose "${compose_files[@]}" "${profile_args[@]}" ps
