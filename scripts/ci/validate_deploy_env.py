from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

_REQUIRED_KEYS = (
    "DATABASE_URL",
    "GRAFANA_ADMIN_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)
_WORKER_KEY = "TASKIQ_WORKERS"
_SUPPORTED_WORKER_VALUE = "1"
_DATABASE_SCHEME = "postgresql+asyncpg"
_DATABASE_HOSTNAME = "postgres"


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

    if all(env_values.get(key) for key in ("DATABASE_URL", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")):
        errors.extend(_validate_database_url(env_values))

    worker_value = env_values.get(_WORKER_KEY)
    if worker_value is not None and worker_value != _SUPPORTED_WORKER_VALUE:
        errors.append("TASKIQ_WORKERS must be omitted or equal to 1 until multi-instance runtime is supported")

    return errors


def _validate_database_url(env_values: dict[str, str]) -> list[str]:
    try:
        database_url = urlsplit(env_values["DATABASE_URL"])
        database_name = database_url.path.removeprefix("/")
        checks = (
            (database_url.scheme == _DATABASE_SCHEME, "DATABASE_URL must use the postgresql+asyncpg scheme"),
            (database_url.hostname == _DATABASE_HOSTNAME, "DATABASE_URL hostname must be postgres"),
            (
                unquote(database_url.username or "") == env_values["POSTGRES_USER"],
                "DATABASE_URL user does not match POSTGRES_USER",
            ),
            (
                unquote(database_url.password or "") == env_values["POSTGRES_PASSWORD"],
                "DATABASE_URL password does not match POSTGRES_PASSWORD",
            ),
            (
                unquote(database_name) == env_values["POSTGRES_DB"],
                "DATABASE_URL database does not match POSTGRES_DB",
            ),
        )
    except ValueError:
        return ["DATABASE_URL is not a valid PostgreSQL URL"]

    return [message for is_valid, message in checks if not is_valid]


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
