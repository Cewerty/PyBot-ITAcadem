from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_SEMVER_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$")


def find_latest_release_tag(repository_path: Path) -> str | None:
    result = _run_git(repository_path, "tag", "--list", "v*", "--sort=-version:refname")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to read Git tags")

    return next(
        (tag for tag in result.stdout.splitlines() if _SEMVER_TAG_PATTERN.fullmatch(tag)),
        None,
    )


def is_tag_in_head_history(repository_path: Path, tag: str) -> bool:
    result = _run_git(repository_path, "merge-base", "--is-ancestor", tag, "HEAD")
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or f"Unable to inspect history for {tag}")
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) > 1:
        print("Usage: validate_release_history.py [repository-path]", file=sys.stderr)
        return 2

    repository_path = Path(args[0] if args else ".").resolve()
    try:
        latest_tag = find_latest_release_tag(repository_path)
        if latest_tag is None:
            print("No release tags found; release history validation skipped.")
            return 0

        if not is_tag_in_head_history(repository_path, latest_tag):
            print(
                f"Latest release tag {latest_tag} is not an ancestor of HEAD. "
                "Restore the tagged commit through a merge before publishing another release.",
                file=sys.stderr,
            )
            return 1
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1

    print(f"Release history is valid: {latest_tag} is an ancestor of HEAD.")
    return 0


def _run_git(repository_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository_path,
        capture_output=True,
        check=False,
        text=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
