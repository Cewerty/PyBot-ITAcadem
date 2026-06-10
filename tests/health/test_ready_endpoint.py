from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.responses import JSONResponse

from pybot.dto.health_dto import HealthStatusDTO
from pybot.presentation.web import health_endpoint, ready_endpoint
from pybot.services.health import HealthService
from pybot.services.ports.health_probe import SupportsExecute, SupportsPing

DATABASE_UNAVAILABLE_DETAILS = "Сервис базы данных временно недоступен."
REDIS_UNAVAILABLE_DETAILS = "Сервис Redis временно недоступен."


class _FakeSession(SupportsExecute):
    def __init__(self, should_fail: bool, error: Exception | None = None) -> None:
        self._should_fail = should_fail
        self._error = error or RuntimeError("database is not reachable")

    async def execute(
        self,
        statement: Any,
        params: Mapping[str, object] | None = None,
        *,
        execution_options: Mapping[str, object] | None = None,
        bind_arguments: Mapping[str, object] | None = None,
        **kwargs: object,
    ) -> object:
        _ = statement, params, execution_options, bind_arguments, kwargs
        if self._should_fail:
            raise self._error
        return object()


class _FakeRedisProbe(SupportsPing):
    def __init__(self, should_fail: bool, error: Exception | None = None) -> None:
        self._should_fail = should_fail
        self._error = error or RuntimeError("redis is not reachable")

    async def ping(self) -> object:
        if self._should_fail:
            raise self._error
        return True


@pytest.mark.asyncio
async def test_health_service_ready_ok_reports_dependency_checks() -> None:
    """Readiness should report successful checks for both database and Redis."""
    service = HealthService(_FakeSession(should_fail=False), _FakeRedisProbe(should_fail=False))

    status, is_ready = await service.ready()

    assert is_ready is True, "Ready must be True when dependencies are reachable."
    assert status.status == "ok", "Overall status should be ok for successful dependency checks."
    assert [check.name for check in status.checks] == ["database", "redis"]
    assert all(check.status == "ok" for check in status.checks)


@pytest.mark.asyncio
async def test_health_service_ready_fail_hides_database_exception_details() -> None:
    """When DB is down, readiness must fail without exposing raw DB exception text."""
    service = HealthService(
        _FakeSession(should_fail=True, error=RuntimeError("db down")),
        _FakeRedisProbe(should_fail=False),
    )

    status, is_ready = await service.ready()

    assert is_ready is False, "Ready must be False when DB is not reachable."
    assert status.status == "fail", "Overall status should be fail when DB check fails."
    assert status.checks[0].status == "fail", "DB check should be marked as fail."
    assert status.checks[0].details is None, "Service must not expose raw DB failure details."
    assert status.checks[1].status == "ok", "Redis check should still report its own status."


@pytest.mark.asyncio
async def test_health_service_ready_fail_hides_redis_exception_details() -> None:
    """When Redis is down, readiness must fail without exposing raw Redis exception text."""
    service = HealthService(
        _FakeSession(should_fail=False),
        _FakeRedisProbe(should_fail=True, error=RuntimeError("redis down")),
    )

    status, is_ready = await service.ready()

    assert is_ready is False, "Ready must be False when Redis is not reachable."
    assert status.status == "fail", "Overall status should be fail when Redis check fails."
    assert status.checks[1].status == "fail", "Redis check should be marked as fail."
    assert status.checks[1].details is None, "Service must not expose raw Redis failure details."


@pytest.mark.asyncio
async def test_ready_endpoint_returns_200_on_ok() -> None:
    """Friendly test: /ready should return DTO directly when ready."""
    service = HealthService(_FakeSession(should_fail=False), _FakeRedisProbe(should_fail=False))
    response = await ready_endpoint(service)

    assert isinstance(response, HealthStatusDTO), "Expected DTO response when service is ready."
    assert response.status == "ok", "DTO should carry ok status."


@pytest.mark.asyncio
async def test_ready_endpoint_returns_503_on_fail() -> None:
    """Friendly test: /ready should return 503 with sanitized details when Redis is down."""
    service = HealthService(
        _FakeSession(should_fail=False),
        _FakeRedisProbe(should_fail=True, error=RuntimeError("redis down")),
    )
    response = await ready_endpoint(service)

    assert isinstance(response, JSONResponse), "Expected JSONResponse when service is not ready."
    assert response.status_code == 503, "HTTP status must be 503 for readiness failure."

    payload = json.loads(bytes(response.body).decode("utf-8"))
    assert payload["status"] == "fail", "Payload should report fail status."
    assert payload["checks"][1]["details"] == REDIS_UNAVAILABLE_DETAILS, "Payload should include safe details."
    assert "redis down" not in json.dumps(payload, ensure_ascii=False), "Payload must not leak raw exception text."


@pytest.mark.asyncio
async def test_health_endpoint_returns_200_payload() -> None:
    """Ensure /health endpoint function returns a healthy DTO payload."""
    service = HealthService(_FakeSession(should_fail=False), _FakeRedisProbe(should_fail=False))

    response = await health_endpoint(service)

    assert isinstance(response, HealthStatusDTO), "Expected DTO response from /health endpoint."
    assert response.status == "ok", "Health endpoint must always report process liveness as ok."
    assert response.checks == [], "Liveness payload should not include dependency checks."


@pytest.mark.asyncio
async def test_ready_endpoint_can_hide_checks_when_requested() -> None:
    """Ensure include_checks=False removes checks from readiness response payload."""
    service = HealthService(_FakeSession(should_fail=False), _FakeRedisProbe(should_fail=False))

    response = await ready_endpoint(service, include_checks=False)

    assert isinstance(response, HealthStatusDTO), "Expected DTO response when service is ready."
    assert response.status == "ok", "Readiness status should stay ok."
    assert response.checks == [], "Checks list should be removed when include_checks is false."


@pytest.mark.asyncio
async def test_ready_endpoint_returns_sanitized_database_failure_details() -> None:
    """Database readiness failures should expose only fixed public-safe details."""
    service = HealthService(
        _FakeSession(should_fail=True, error=RuntimeError("db down")),
        _FakeRedisProbe(should_fail=False),
    )

    response = await ready_endpoint(service)

    assert isinstance(response, JSONResponse), "Expected JSONResponse when service is not ready."
    payload = json.loads(bytes(response.body).decode("utf-8"))
    assert payload["checks"][0]["details"] == DATABASE_UNAVAILABLE_DETAILS
    assert "db down" not in json.dumps(payload, ensure_ascii=False)


@pytest.mark.asyncio
async def test_ready_endpoint_hides_failed_checks_when_requested() -> None:
    """include_checks=False should remove checks even for failure responses."""
    service = HealthService(
        _FakeSession(should_fail=True, error=RuntimeError("db down")),
        _FakeRedisProbe(should_fail=False),
    )

    response = await ready_endpoint(service, include_checks=False)

    assert isinstance(response, JSONResponse), "Expected JSONResponse when service is not ready."
    payload = json.loads(bytes(response.body).decode("utf-8"))
    assert payload["status"] == "fail"
    assert payload["checks"] == []
