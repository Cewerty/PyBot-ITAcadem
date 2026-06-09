import subprocess
import sys
from pathlib import Path

import pytest


def _valid_env(*overrides: str) -> str:
    values = {
        "DATABASE_URL": ("postgresql+asyncpg://pybot%40ci:p%40ss%3Aword@postgres:5432/pybot%20prod"),
        "GRAFANA_ADMIN_PASSWORD": "strong-password",
        "POSTGRES_DB": "pybot prod",
        "POSTGRES_USER": "pybot@ci",
        "POSTGRES_PASSWORD": "p@ss:word",
        "TASKIQ_WORKERS": "1",
    }
    for override in overrides:
        key, value = override.split("=", 1)
        values[key] = value
    return "\n".join(f"{key}={value}" for key, value in values.items())


def _run_validator(tmp_path: Path, env_body: str) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / "prod.env"
    env_file.write_text(env_body, encoding="utf-8")
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "validate_deploy_env.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), str(env_file)],
        capture_output=True,
        check=False,
        text=True,
    )


def test_validate_deploy_env_accepts_supported_worker_value(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, _valid_env())

    assert result.returncode == 0
    assert result.stderr == ""


def test_validate_deploy_env_rejects_unsupported_worker_value(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, _valid_env("TASKIQ_WORKERS=2"))

    assert result.returncode == 1
    assert "TASKIQ_WORKERS must be omitted or equal to 1" in result.stderr


def test_validate_deploy_env_requires_grafana_password(tmp_path: Path) -> None:
    result = _run_validator(tmp_path, _valid_env("GRAFANA_ADMIN_PASSWORD="))

    assert result.returncode == 1
    assert "GRAFANA_ADMIN_PASSWORD" in result.stderr


@pytest.mark.parametrize(
    "missing_key",
    ["DATABASE_URL", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
)
def test_validate_deploy_env_requires_database_values(tmp_path: Path, missing_key: str) -> None:
    result = _run_validator(tmp_path, _valid_env(f"{missing_key}="))

    assert result.returncode == 1
    assert missing_key in result.stderr


@pytest.mark.parametrize(
    ("database_url", "expected_error"),
    [
        (
            "postgresql://pybot%40ci:p%40ss%3Aword@postgres:5432/pybot%20prod",
            "DATABASE_URL must use the postgresql+asyncpg scheme",
        ),
        (
            "postgresql+asyncpg://pybot%40ci:p%40ss%3Aword@localhost:5432/pybot%20prod",
            "DATABASE_URL hostname must be postgres",
        ),
        (
            "postgresql+asyncpg://other:p%40ss%3Aword@postgres:5432/pybot%20prod",
            "DATABASE_URL user does not match POSTGRES_USER",
        ),
        (
            "postgresql+asyncpg://pybot%40ci:wrong@postgres:5432/pybot%20prod",
            "DATABASE_URL password does not match POSTGRES_PASSWORD",
        ),
        (
            "postgresql+asyncpg://pybot%40ci:p%40ss%3Aword@postgres:5432/other",
            "DATABASE_URL database does not match POSTGRES_DB",
        ),
    ],
)
def test_validate_deploy_env_rejects_inconsistent_database_url(
    tmp_path: Path,
    database_url: str,
    expected_error: str,
) -> None:
    result = _run_validator(tmp_path, _valid_env(f"DATABASE_URL={database_url}"))

    assert result.returncode == 1
    assert expected_error in result.stderr
