from pathlib import Path
import subprocess
import sys


def _run_validator(tmp_path: Path, env_body: str) -> subprocess.CompletedProcess[str]:
    env_file = tmp_path / "prod.env"
    env_file.write_text(env_body, encoding="utf-8")
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "validate_deploy_env.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), str(env_file)],  # noqa: S607
        capture_output=True,
        check=False,
        text=True,
    )


def test_validate_deploy_env_accepts_supported_worker_value(tmp_path: Path) -> None:
    result = _run_validator(
        tmp_path,
        "\n".join(
            [
                "DATABASE_URL=sqlite+aiosqlite:///./data/pybot_itacadem.db",
                "GRAFANA_ADMIN_PASSWORD=strong-password",
                "TASKIQ_WORKERS=1",
            ]
        ),
    )

    assert result.returncode == 0
    assert result.stderr == ""


def test_validate_deploy_env_rejects_unsupported_worker_value(tmp_path: Path) -> None:
    result = _run_validator(
        tmp_path,
        "\n".join(
            [
                "DATABASE_URL=sqlite+aiosqlite:///./data/pybot_itacadem.db",
                "GRAFANA_ADMIN_PASSWORD=strong-password",
                "TASKIQ_WORKERS=2",
            ]
        ),
    )

    assert result.returncode == 1
    assert "TASKIQ_WORKERS must be omitted or equal to 1" in result.stderr


def test_validate_deploy_env_requires_grafana_password(tmp_path: Path) -> None:
    result = _run_validator(
        tmp_path,
        "DATABASE_URL=sqlite+aiosqlite:///./data/pybot_itacadem.db",
    )

    assert result.returncode == 1
    assert "GRAFANA_ADMIN_PASSWORD" in result.stderr
