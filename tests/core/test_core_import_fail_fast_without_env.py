import os
from pathlib import Path
import subprocess
import sys


def test_import_pybot_core_fails_fast_without_required_env(tmp_path: Path) -> None:
    runtime_env = os.environ.copy()
    project_root = Path(__file__).resolve().parents[2]
    runtime_env["PYTHONPATH"] = os.pathsep.join(
        [
            str(project_root / "src"),
            str(project_root),
            runtime_env.get("PYTHONPATH", ""),
        ]
    )
    for key in ("BOT_TOKEN", "BOT_TOKEN_TEST", "ROLE_REQUEST_ADMIN_TG_ID", "DATABASE_URL"):
        runtime_env.pop(key, None)

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "from pybot.core import logger, settings; print('ok')"],  # noqa: S607
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=runtime_env,
        text=True,
    )

    # settings is instantiated during module import, so missing required env vars
    # must fail fast with a clear validation error.
    assert result.returncode != 0
    assert "ValidationError" in result.stderr
    for env_name in ("BOT_TOKEN", "BOT_TOKEN_TEST", "ROLE_REQUEST_ADMIN_TG_ID", "DATABASE_URL"):
        assert env_name in result.stderr
