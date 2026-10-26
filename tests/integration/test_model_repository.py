"""PostgreSQL integration tests for model_versions schema, repository, and lifecycle."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.core.config import Settings
from finsignal.core.database import create_db_resources
from finsignal.ml.constants import MODEL_FAMILY
from finsignal.ml.exceptions import ModelLifecycleError
from finsignal.ml.models import ModelVersion
from finsignal.ml.repository import ModelRepository


@pytest.fixture
async def async_session(
    disposable_db: dict[str, Any],
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to the disposable test database."""
    settings: Settings = disposable_db["settings"]
    engine, session_maker = create_db_resources(settings)
    async with session_maker() as session:
        yield session
        try:
            await session.rollback()
            await session.execute(text("TRUNCATE TABLE model_versions CASCADE;"))
            await session.commit()
        except Exception:
            await session.rollback()
    await engine.dispose()


def test_model_versions_migration_downgrade_and_upgrade(
    disposable_db: dict[str, Any],
) -> None:
    """Verify Alembic migration 0004 downgrades cleanly and re-applies."""
    alembic_cfg = disposable_db["alembic_cfg"]

    # Downgrade to 0003
    command.downgrade(alembic_cfg, "0003_account_import_namespace")

    # Verify table does not exist
    import psycopg

    params = disposable_db["settings"]
    conn = psycopg.connect(
        host=params.database_host,
        port=params.database_port,
        user=params.database_user,
        password=params.database_password.get_secret_value(),
        dbname=params.database_name,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'model_versions');"
        )
        row = cur.fetchone()
        assert row is not None and row[0] is False
    conn.close()

    # Re-upgrade to head (0004)
    command.upgrade(alembic_cfg, "head")

    conn = psycopg.connect(
        host=params.database_host,
        port=params.database_port,
        user=params.database_user,
        password=params.database_password.get_secret_value(),
        dbname=params.database_name,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'model_versions');"
        )
        row = cur.fetchone()
        assert row is not None and row[0] is True
    conn.close()


async def test_model_registration_and_lookup(async_session: AsyncSession) -> None:
    repo = ModelRepository()

    model = await repo.register(
        session=async_session,
        name=MODEL_FAMILY,
        version="1.0.0",
        algorithm="isolation_forest",
        feature_version="v1.0",
        parameters={"n_estimators": 100, "contamination": "auto"},
        metrics={"f1": 0.85, "pr_auc": 0.78},
        artifact_uri="models/test_model.joblib",
        artifact_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        status="EXPERIMENTAL",
    )
    await async_session.commit()

    assert model.id is not None
    assert model.name == MODEL_FAMILY
    assert model.version == "1.0.0"
    assert model.status == "EXPERIMENTAL"

    # Lookup by ID
    fetched = await repo.get_by_id(async_session, model.id)
    assert fetched is not None
    assert fetched.id == model.id
    assert fetched.version == "1.0.0"

    # Lookup by name and version
    by_version = await repo.get_by_name_and_version(
        async_session, MODEL_FAMILY, "1.0.0"
    )
    assert by_version is not None
    assert by_version.id == model.id


async def test_duplicate_name_and_version_rejected(async_session: AsyncSession) -> None:
    repo = ModelRepository()

    await repo.register(
        session=async_session,
        name=MODEL_FAMILY,
        version="1.0.0",
        algorithm="isolation_forest",
    )
    await async_session.commit()

    with pytest.raises(IntegrityError):
        await repo.register(
            session=async_session,
            name=MODEL_FAMILY,
            version="1.0.0",
            algorithm="isolation_forest",
        )
        await async_session.commit()
    await async_session.rollback()


async def test_lifecycle_transitions_and_atomic_promotion(
    async_session: AsyncSession,
) -> None:
    """Validate EXPERIMENTAL -> VALIDATED -> ACTIVE -> RETIRED lifecycle."""
    repo = ModelRepository()

    # Zero active models initially
    active_initial = await repo.get_active_model(async_session, MODEL_FAMILY)
    assert active_initial is None

    # Register m1
    m1 = await repo.register(
        session=async_session,
        name=MODEL_FAMILY,
        version="1.0.0",
        algorithm="isolation_forest",
        status="EXPERIMENTAL",
    )
    await async_session.commit()

    # Validate m1
    m1 = await repo.transition_status(async_session, m1.id, "VALIDATED")
    await async_session.commit()
    assert m1.status == "VALIDATED"

    # Promote m1 to ACTIVE
    m1 = await repo.promote_to_active(async_session, m1.id)
    await async_session.commit()
    assert m1.status == "ACTIVE"

    # Check active model lookup
    active_now = await repo.get_active_model(async_session, MODEL_FAMILY)
    assert active_now is not None
    assert active_now.id == m1.id

    # Register and validate m2
    m2 = await repo.register(
        session=async_session,
        name=MODEL_FAMILY,
        version="1.1.0",
        algorithm="isolation_forest",
        status="EXPERIMENTAL",
    )
    await async_session.commit()
    m2 = await repo.transition_status(async_session, m2.id, "VALIDATED")
    await async_session.commit()

    # Promote m2 to ACTIVE -> should atomically retire m1!
    m2 = await repo.promote_to_active(async_session, m2.id)
    await async_session.commit()
    assert m2.status == "ACTIVE"

    # Refresh m1
    m1_refreshed = await repo.get_by_id(async_session, m1.id)
    assert m1_refreshed is not None
    assert m1_refreshed.status == "RETIRED"

    # Active model is now m2
    active_latest = await repo.get_active_model(async_session, MODEL_FAMILY)
    assert active_latest is not None
    assert active_latest.id == m2.id


async def test_invalid_lifecycle_transitions(async_session: AsyncSession) -> None:
    """TG-05: Enforce strict rejection of unauthorized lifecycle jumps."""
    repo = ModelRepository()

    m = await repo.register(
        session=async_session,
        name=MODEL_FAMILY,
        version="2.0.0",
        algorithm="isolation_forest",
        status="EXPERIMENTAL",
    )
    await async_session.commit()

    # Cannot jump EXPERIMENTAL -> ACTIVE directly (must be VALIDATED first)
    with pytest.raises(ModelLifecycleError, match="not permitted"):
        await repo.transition_status(async_session, m.id, "ACTIVE")

    # Transition to VALIDATED
    m = await repo.transition_status(async_session, m.id, "VALIDATED")
    await async_session.commit()

    # Cannot transition backwards VALIDATED -> EXPERIMENTAL
    with pytest.raises(ModelLifecycleError, match="not permitted"):
        await repo.transition_status(async_session, m.id, "EXPERIMENTAL")

    # Transition to RETIRED
    m = await repo.transition_status(async_session, m.id, "RETIRED")
    await async_session.commit()

    # RETIRED is terminal: cannot transition RETIRED -> ACTIVE or VALIDATED
    with pytest.raises(ModelLifecycleError, match="not permitted"):
        await repo.transition_status(async_session, m.id, "ACTIVE")

    with pytest.raises(ModelLifecycleError, match="not permitted"):
        await repo.transition_status(async_session, m.id, "VALIDATED")


async def test_active_model_partial_unique_index(async_session: AsyncSession) -> None:
    """Verify DB enforces at most one ACTIVE model per family if bypassed via direct SQL."""
    m1 = ModelVersion(
        id=uuid.uuid4(),
        name=MODEL_FAMILY,
        version="3.0.0",
        algorithm="isolation_forest",
        status="ACTIVE",
    )
    m2 = ModelVersion(
        id=uuid.uuid4(),
        name=MODEL_FAMILY,
        version="3.1.0",
        algorithm="isolation_forest",
        status="ACTIVE",
    )

    async_session.add(m1)
    await async_session.flush()

    async_session.add(m2)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()
