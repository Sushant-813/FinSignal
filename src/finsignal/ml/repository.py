"""PostgreSQL repository for ML model versions and lifecycle transitions."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.ml.constants import MODEL_FAMILY
from finsignal.ml.exceptions import (
    ModelLifecycleError,
    ModelNotFoundError,
)
from finsignal.ml.models import ModelVersion

# Valid status transitions
VALID_TRANSITIONS: dict[str, set[str]] = {
    "EXPERIMENTAL": {"VALIDATED", "RETIRED"},
    "VALIDATED": {"ACTIVE", "RETIRED"},
    "ACTIVE": {"RETIRED"},
    "RETIRED": set(),  # Terminal state
}


class ModelRepository:
    """Async repository managing model registration, active lookup, and atomic promotion."""

    async def register(
        self,
        session: AsyncSession,
        name: str,
        version: str,
        algorithm: str,
        feature_version: str | None = None,
        dataset_version_id: uuid.UUID | None = None,
        parameters: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        artifact_uri: str | None = None,
        artifact_hash: str | None = None,
        status: str = "EXPERIMENTAL",
    ) -> ModelVersion:
        """Register a new model version entity."""
        if status not in {"EXPERIMENTAL", "VALIDATED"}:
            raise ModelLifecycleError(
                f"Initial status must be EXPERIMENTAL or VALIDATED; got '{status}'."
            )

        model = ModelVersion(
            id=uuid.uuid4(),
            name=name,
            version=version,
            algorithm=algorithm,
            feature_version=feature_version,
            dataset_version_id=dataset_version_id,
            parameters=parameters,
            metrics=metrics,
            artifact_uri=artifact_uri,
            artifact_hash=artifact_hash,
            status=status,
        )
        session.add(model)
        await session.flush()
        return model

    async def get_by_id(
        self,
        session: AsyncSession,
        model_id: uuid.UUID,
        for_update: bool = False,
    ) -> ModelVersion | None:
        """Retrieve model version by primary key UUID."""
        stmt = select(ModelVersion).where(ModelVersion.id == model_id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_and_version(
        self,
        session: AsyncSession,
        name: str,
        version: str,
    ) -> ModelVersion | None:
        """Retrieve model version by unique family name and semantic version."""
        stmt = select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_model(
        self,
        session: AsyncSession,
        name: str = MODEL_FAMILY,
    ) -> ModelVersion | None:
        """Retrieve currently ACTIVE model version for a given model family."""
        stmt = select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.status == "ACTIVE",
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_models(
        self,
        session: AsyncSession,
        name: str | None = None,
        status: str | None = None,
    ) -> Sequence[ModelVersion]:
        """List model versions optionally filtered by family name or status."""
        stmt = select(ModelVersion).order_by(ModelVersion.created_at.desc())
        if name:
            stmt = stmt.where(ModelVersion.name == name)
        if status:
            stmt = stmt.where(ModelVersion.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def transition_status(
        self,
        session: AsyncSession,
        model_id: uuid.UUID,
        target_status: str,
    ) -> ModelVersion:
        """Transition model version status adhering strictly to the lifecycle state machine.

        Transitions:
        - EXPERIMENTAL -> VALIDATED, RETIRED
        - VALIDATED -> ACTIVE (via promote_to_active), RETIRED
        - ACTIVE -> RETIRED
        - RETIRED -> (none)
        """
        model = await self.get_by_id(session, model_id, for_update=True)
        if model is None:
            raise ModelNotFoundError(f"Model version {model_id} not found.")

        current = model.status
        allowed = VALID_TRANSITIONS.get(current, set())
        if target_status not in allowed:
            raise ModelLifecycleError(
                f"Invalid lifecycle transition: '{current}' -> '{target_status}' is not permitted."
            )

        if target_status == "ACTIVE":
            # Promotion to ACTIVE must be done via atomic promotion to retire previous active
            return await self.promote_to_active(session, model_id)

        model.status = target_status
        await session.flush()
        return model

    async def promote_to_active(
        self,
        session: AsyncSession,
        model_id: uuid.UUID,
    ) -> ModelVersion:
        """Atomically promote a VALIDATED model to ACTIVE, retiring the previous active model.

        Enforces:
        - Model must be VALIDATED prior to promotion.
        - Exactly one ACTIVE model per family via transaction locking and partial unique index.
        """
        model = await self.get_by_id(session, model_id, for_update=True)
        if model is None:
            raise ModelNotFoundError(f"Model version {model_id} not found.")

        if model.status != "VALIDATED":
            raise ModelLifecycleError(
                f"Cannot activate model {model_id} with status '{model.status}'. Must be 'VALIDATED'."
            )

        # 1. Lock and retrieve current active model in the family, if any
        active_stmt = (
            select(ModelVersion)
            .where(
                ModelVersion.name == model.name,
                ModelVersion.status == "ACTIVE",
            )
            .with_for_update()
        )
        active_res = await session.execute(active_stmt)
        current_active = active_res.scalar_one_or_none()

        # 2. Retire currently active model first and flush so index is cleared
        if current_active is not None and current_active.id != model.id:
            current_active.status = "RETIRED"
            await session.flush()

        # 3. Promote candidate to ACTIVE
        model.status = "ACTIVE"
        await session.flush()
        return model
