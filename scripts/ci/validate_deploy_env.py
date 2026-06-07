from __future__ import annotations

import sys
from pathlib import Path

_REQUIRED_KEYS = ("DATABASE_URL", "GRAFANA_ADMIN_PASSWORD")
_WORKER_KEY = "TASKIQ_WORKERS"
_SUPPORTED_WORKER_VALUE = "1"


def parse_env_file(env_path: Path) -> dict[str, str]:
    env_values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_values[key.strip()] = value.strip()
    return env_values


def validate_deploy_env(env_values: dict[str, str]) -> list[str]:
    errors: list[str] = []

    for key in _REQUIRED_KEYS:
        if not env_values.get(key):
            errors.append(f"PROD_ENV_FILE must contain non-empty {key}=...")

    worker_value = env_values.get(_WORKER_KEY)
    if worker_value is not None and worker_value != _SUPPORTED_WORKER_VALUE:
        errors.append("TASKIQ_WORKERS must be omitted or equal to 1 until multi-instance runtime is supported")

    return errors


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 1:
        print("Usage: validate_deploy_env.py <env-file>", file=sys.stderr)
        return 2

    env_path = Path(args[0])
    env_values = parse_env_file(env_path)
    errors = validate_deploy_env(env_values)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
