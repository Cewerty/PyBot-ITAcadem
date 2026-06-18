import json
import subprocess
import sys
from pathlib import Path

import pytest


def _run_helper(*args: str) -> subprocess.CompletedProcess[str]:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "resolve_deploy_mode.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), *args],
        capture_output=True,
        check=False,
        text=True,
    )


def test_resolve_deploy_mode_defaults_to_standard_build_and_deploy() -> None:
    result = _run_helper("--current-sha", "a" * 40)

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "image_tag": "a" * 40,
        "rollback_mode": False,
        "run_migrations": True,
    }


def test_resolve_deploy_mode_selects_rollback_mode_for_full_sha_tag() -> None:
    result = _run_helper(
        "--current-sha",
        "a" * 40,
        "--rollback-image-tag",
        "B" * 40,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "image_tag": "b" * 40,
        "rollback_mode": True,
        "run_migrations": False,
    }


@pytest.mark.parametrize(
    "invalid_tag",
    [
        "abc123",
        "z" * 40,
        "a" * 39,
        "main",
    ],
)
def test_resolve_deploy_mode_rejects_invalid_rollback_tag(invalid_tag: str) -> None:
    result = _run_helper(
        "--current-sha",
        "a" * 40,
        "--rollback-image-tag",
        invalid_tag,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert "rollback_image_tag must be a full 40-character hexadecimal commit SHA" in result.stderr
