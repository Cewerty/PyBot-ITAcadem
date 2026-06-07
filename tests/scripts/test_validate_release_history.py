import subprocess
import sys
from pathlib import Path


def _run_git(repository_path: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository_path,
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def _commit_file(repository_path: Path, filename: str, content: str, message: str) -> str:
    (repository_path / filename).write_text(content, encoding="utf-8")
    _run_git(repository_path, "add", filename)
    _run_git(repository_path, "commit", "-m", message)
    return _run_git(repository_path, "rev-parse", "HEAD")


def _initialize_repository(tmp_path: Path) -> Path:
    repository_path = tmp_path / "repository"
    repository_path.mkdir()
    _run_git(repository_path, "init")
    _run_git(repository_path, "config", "user.name", "Release History Test")
    _run_git(repository_path, "config", "user.email", "release-history@example.com")
    _commit_file(repository_path, "README.md", "initial\n", "initial commit")
    return repository_path


def _run_validator(repository_path: Path) -> subprocess.CompletedProcess[str]:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "validate_release_history.py"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script_path), str(repository_path)],
        capture_output=True,
        check=False,
        text=True,
    )


def test_validate_release_history_accepts_repository_without_release_tags(tmp_path: Path) -> None:
    repository_path = _initialize_repository(tmp_path)

    result = _run_validator(repository_path)

    assert result.returncode == 0
    assert "No release tags found" in result.stdout


def test_validate_release_history_accepts_latest_tag_in_head_history(tmp_path: Path) -> None:
    repository_path = _initialize_repository(tmp_path)
    _run_git(repository_path, "tag", "v0.1.0")
    _commit_file(repository_path, "feature.txt", "feature\n", "add feature")

    result = _run_validator(repository_path)

    assert result.returncode == 0
    assert "v0.1.0 is an ancestor of HEAD" in result.stdout


def test_validate_release_history_rejects_latest_tag_outside_head_history(tmp_path: Path) -> None:
    repository_path = _initialize_repository(tmp_path)
    common_commit = _run_git(repository_path, "rev-parse", "HEAD")
    _commit_file(repository_path, "release.txt", "release\n", "release commit")
    _run_git(repository_path, "tag", "v0.1.0")
    _run_git(repository_path, "checkout", "--detach", common_commit)
    _commit_file(repository_path, "rewritten.txt", "rewritten\n", "replacement commit")

    result = _run_validator(repository_path)

    assert result.returncode == 1
    assert "Latest release tag v0.1.0 is not an ancestor of HEAD" in result.stderr
