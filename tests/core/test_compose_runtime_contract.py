from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "compose_file",
    ("docker-compose.yml", "docker-compose.prod.yml"),
)
def test_taskiq_worker_command_preserves_container_shell_variable(compose_file: str) -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_config = (project_root / compose_file).read_text(encoding="utf-8")

    assert "TASKIQ_WORKERS='${TASKIQ_WORKERS:-1}'" in compose_config
    assert '\\"$$TASKIQ_WORKERS\\" != \\"1\\"' in compose_config
    assert '--workers \\"$$TASKIQ_WORKERS\\"' in compose_config


def test_ci_parity_override_mounts_existing_bot_smoke_helper_read_only() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parity_override = (project_root / "docker-compose.ci.parity.override.yml").read_text(encoding="utf-8")

    assert (project_root / "scripts/ci/bot_runtime_parity_smoke.py").is_file()
    assert 'command: ["python", "scripts/ci/bot_runtime_parity_smoke.py"]' in parity_override
    assert "./scripts/ci:/app/scripts/ci:ro" in parity_override
