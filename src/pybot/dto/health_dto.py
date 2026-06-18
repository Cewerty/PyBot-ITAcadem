"""DTO for application health and readiness checks."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field

from .base_dto import BaseDTO


class HealthCheckDTO(BaseDTO):
    """Public details about a single readiness check."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "database",
                    "status": "fail",
                    "details": "Сервис базы данных временно недоступен.",
                    "latency_ms": 8,
                }
            ]
        }
    )

    name: str = Field(
        description="Name of the readiness check, for example database.",
        examples=["database"],
    )
    status: Literal["ok", "fail"] = Field(
        description="Status of the readiness check.",
        examples=["ok"],
    )
    details: str | None = Field(
        default=None,
        description="Safe public-facing description of the component state.",
        examples=["Сервис базы данных временно недоступен."],
    )
    latency_ms: int | None = Field(
        default=None,
        ge=0,
        description="Execution time of the readiness check in milliseconds.",
        examples=[8],
    )


class HealthStatusDTO(BaseDTO):
    """Overall liveness or readiness status payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "fail",
                    "checks": [
                        {
                            "name": "database",
                            "status": "fail",
                            "details": "Сервис базы данных временно недоступен.",
                            "latency_ms": 8,
                        }
                    ],
                    "timestamp": "2026-02-23T18:00:00Z",
                }
            ]
        }
    )

    status: Literal["ok", "fail"] = Field(
        description="Overall service status.",
        examples=["ok"],
    )
    checks: list[HealthCheckDTO] = Field(
        description="List of readiness checks.",
        examples=[
            [
                {
                    "name": "database",
                    "status": "fail",
                    "details": "Сервис базы данных временно недоступен.",
                    "latency_ms": 8,
                }
            ]
        ],
    )
    timestamp: datetime = Field(
        description="UTC timestamp when the status payload was produced.",
        examples=["2026-02-23T18:00:00Z"],
    )
