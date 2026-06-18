from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.model_factories import UserSpec, create_user

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_postgresql_uses_native_enums_and_pending_request_index(db_session: AsyncSession) -> None:
    enum_result = await db_session.execute(
        text(
            """
            SELECT type.typname, array_agg(enum.enumlabel ORDER BY enum.enumsortorder)
            FROM pg_type AS type
            JOIN pg_enum AS enum ON enum.enumtypid = type.oid
            WHERE type.typname IN (
                'points_type_enum',
                'request_status_enum',
                'role_event_operand_enum'
            )
            GROUP BY type.typname
            """
        )
    )
    enum_values = {name: list(values) for name, values in enum_result.all()}

    assert enum_values == {
        "points_type_enum": ["ACADEMIC", "REPUTATION"],
        "request_status_enum": ["PENDING", "APPROVED", "REJECTED", "CANCELED"],
        "role_event_operand_enum": ["ADD", "DELETE", "REPLACE"],
    }

    index_definition = await db_session.scalar(
        text(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename = 'role_requests'
              AND indexname = 'uq_role_requests_pending_by_user'
            """
        )
    )

    assert index_definition is not None
    assert "CREATE UNIQUE INDEX" in index_definition
    assert "status" in index_definition
    assert "PENDING" in index_definition


@pytest.mark.asyncio
async def test_bigint_identity_sequence_restarts_after_truncate(db_session: AsyncSession) -> None:
    first_user = await create_user(db_session, spec=UserSpec(telegram_id=900_001))
    await db_session.commit()
    assert first_user.id == 1

    await db_session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
    await db_session.commit()
    db_session.expunge_all()

    second_user = await create_user(db_session, spec=UserSpec(telegram_id=900_002))
    await db_session.commit()

    column_type = await db_session.scalar(
        text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'users'
              AND column_name = 'id'
            """
        )
    )

    assert second_user.id == 1
    assert column_type == "bigint"
