import os
from pathlib import Path
import subprocess
import sys

from pybot.core.config import AppSettings


def test_app_settings_do_not_include_deploy_only_fields() -> None:
    for field_name in (
        "taskiq_workers",
        "grafana_admin_password",
        "nginx_port",
        "nginx_bind_host",
        "public_domain",
    ):
        assert field_name not in AppSettings.model_fields


def test_get_settings_succeeds_without_deploy_only_env(tmp_path: Path) -> None:
    runtime_env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[2]
    runtime_env["PYTHONPATH"] = os.pathsep.join(
        [
            str(project_root / "src"),
            str(project_root),
            runtime_env.get("PYTHONPATH", ""),
        ]
    )
    runtime_env["BOT_TOKEN"] = "123456:prod"
    runtime_env["BOT_MODE"] = "prod"
    runtime_env["ROLE_REQUEST_ADMIN_TG_ID"] = "1"
    runtime_env["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"
    for key in (
        "BOT_TOKEN_TEST",
        "TASKIQ_WORKERS",
        "GRAFANA_ADMIN_PASSWORD",
        "NGINX_PORT",
        "NGINX_BIND_HOST",
        "PUBLIC_DOMAIN",
    ):
        runtime_env.pop(key, None)

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "from pybot.core.config import get_settings; get_settings(); print('ok')"],  # noqa: S607
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=runtime_env,
        text=True,
    )

    assert result.returncode == 0
    assert "ok" in result.stdout


def test_get_settings_ignores_deploy_only_keys_from_dotenv(tmp_path: Path) -> None:
    runtime_env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[2]
    runtime_env["PYTHONPATH"] = os.pathsep.join(
        [
            str(project_root / "src"),
            str(project_root),
            runtime_env.get("PYTHONPATH", ""),
        ]
    )
    runtime_env["BOT_MODE"] = "prod"
    runtime_env["BOT_TOKEN"] = "123456:prod"
    runtime_env["ROLE_REQUEST_ADMIN_TG_ID"] = "1"
    runtime_env["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test.db"
    for key in (
        "BOT_TOKEN_TEST",
        "TASKIQ_WORKERS",
        "GRAFANA_ADMIN_PASSWORD",
        "NGINX_PORT",
        "NGINX_BIND_HOST",
        "PUBLIC_DOMAIN",
    ):
        runtime_env.pop(key, None)

    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TASKIQ_WORKERS=1",
                "GRAFANA_ADMIN_PASSWORD=strong-password",
                "NGINX_PORT=8080",
                "NGINX_BIND_HOST=0.0.0.0",
                "PUBLIC_DOMAIN=example.com",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "from pybot.core.config import get_settings; get_settings(); print('ok')"],  # noqa: S607
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=runtime_env,
        text=True,
    )

    assert result.returncode == 0
    assert "ok" in result.stdout
