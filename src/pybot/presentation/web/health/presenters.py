"""Presentation helpers for public Health API responses."""

from __future__ import annotations

from ....dto.health_dto import HealthCheckDTO, HealthStatusDTO

_SAFE_FAILURE_DETAILS_BY_CHECK_NAME = {
    "database": "Сервис базы данных временно недоступен.",
    "redis": "Сервис Redis временно недоступен.",
}
_DEFAULT_SAFE_FAILURE_DETAILS = "Зависимый сервис временно недоступен."


def sanitize_readiness_status(status: HealthStatusDTO) -> HealthStatusDTO:
    """Return a public-safe readiness payload."""
    sanitized_checks = [_sanitize_readiness_check(check) for check in status.checks]
    return status.model_copy(update={"checks": sanitized_checks})


def _sanitize_readiness_check(check: HealthCheckDTO) -> HealthCheckDTO:
    if check.status == "ok":
        return check.model_copy(update={"details": None})

    return check.model_copy(
        update={
            "details": _SAFE_FAILURE_DETAILS_BY_CHECK_NAME.get(
                check.name,
                _DEFAULT_SAFE_FAILURE_DETAILS,
            )
        }
    )
