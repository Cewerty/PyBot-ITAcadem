from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass

_FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class DeployModeResolution:
    image_tag: str
    rollback_mode: bool
    run_migrations: bool


def resolve_deploy_mode(current_sha: str, rollback_image_tag: str | None = None) -> DeployModeResolution:
    normalized_current_sha = _normalize_sha(current_sha, field_name="current_sha")
    normalized_rollback_tag = (rollback_image_tag or "").strip()

    if not normalized_rollback_tag:
        return DeployModeResolution(
            image_tag=normalized_current_sha,
            rollback_mode=False,
            run_migrations=True,
        )

    normalized_rollback_sha = _normalize_sha(
        normalized_rollback_tag,
        field_name="rollback_image_tag",
    )
    return DeployModeResolution(
        image_tag=normalized_rollback_sha,
        rollback_mode=True,
        run_migrations=False,
    )


def _normalize_sha(value: str, *, field_name: str) -> str:
    normalized_value = value.strip().lower()
    if not _FULL_SHA_PATTERN.fullmatch(normalized_value):
        raise ValueError(f"{field_name} must be a full 40-character hexadecimal commit SHA")
    return normalized_value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve production deploy mode and selected immutable image tag.",
    )
    parser.add_argument(
        "--current-sha",
        required=True,
        help="Current checked-out commit SHA used for the standard deploy path.",
    )
    parser.add_argument(
        "--rollback-image-tag",
        default="",
        help="Optional immutable image tag for rollback mode.",
    )
    args = parser.parse_args(argv)

    try:
        resolution = resolve_deploy_mode(
            current_sha=args.current_sha,
            rollback_image_tag=args.rollback_image_tag,
        )
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1

    print(json.dumps(asdict(resolution)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
