"""PostgreSQL repository for risk analyses and risk factors."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from finsignal.risk.models import RiskAnalysis, RiskFactor

IDENTITY_CONSTRAINT_NAME = "uq_risk_analyses_identity"


def is_risk_identity_conflict(exc: IntegrityError) -> bool:
    """Determine whether an IntegrityError was caused specifically by uq_risk_analyses_identity.

    Requires verified evidence that the failure is a PostgreSQL unique violation (SQLSTATE '23505')
    matching the exact identity constraint 'uq_risk_analyses_identity'.
    Fails closed (returns False) if structured constraint or SQLSTATE information is missing.
    """
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False

    # In SQLAlchemy asyncpg dialect, orig is AsyncAdapt_asyncpg_dbapi.UniqueViolationError,
    # and the underlying asyncpg exception is in orig.orig or orig.driver_exception.
    nested_orig = getattr(orig, "orig", None) or getattr(orig, "driver_exception", None)

    # 1. Resolve structured SQLSTATE (must be '23505')
    sqlstate = (
        getattr(orig, "sqlstate", None)
        or getattr(orig, "pgcode", None)
        or (getattr(nested_orig, "sqlstate", None) if nested_orig is not None else None)
    )
    if sqlstate != "23505":
        return False

    # 2. Resolve structured constraint name (must be 'uq_risk_analyses_identity')
    constraint_name = getattr(orig, "constraint_name", None) or (
        getattr(nested_orig, "constraint_name", None)
        if nested_orig is not None
        else None
    )
    return constraint_name == IDENTITY_CONSTRAINT_NAME


class RiskRepository:
    """Async SQLAlchemy repository managing atomic persistence and querying of risk analyses."""

    async def save_atomic(
        self,
        session: AsyncSession,
        analysis: RiskAnalysis,
        factors: list[RiskFactor],
    ) -> RiskAnalysis:
        """Persist a parent risk analysis and its associated factors atomically using a savepoint.

        Guarantees:
        - Parent and factors are committed or rolled back together.
        - If a unique constraint violation occurs (e.g. concurrent race on identity),
          rolls back the savepoint cleanly so the session remains usable.
        """
        async with session.begin_nested():
            session.add(analysis)
            for factor in factors:
                factor.risk_analysis = analysis
                session.add(factor)
            await session.flush()

        return analysis

    async def get_by_identity(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
        model_version_id: uuid.UUID,
        config_version: str,
        feature_vector_hash: str,
    ) -> RiskAnalysis | None:
        """Retrieve completed risk analysis by exact canonical 4-tuple identity."""
        stmt = (
            select(RiskAnalysis)
            .options(
                selectinload(RiskAnalysis.factors),
                selectinload(RiskAnalysis.model_version),
            )
            .where(
                RiskAnalysis.transaction_id == transaction_id,
                RiskAnalysis.model_version_id == model_version_id,
                RiskAnalysis.config_version == config_version,
                RiskAnalysis.feature_vector_hash == feature_vector_hash,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_transaction(
        self,
        session: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> RiskAnalysis | None:
        """Retrieve latest successfully persisted risk analysis for a transaction.

        Deterministic ordering: created_at DESC, id DESC.
        """
        stmt = (
            select(RiskAnalysis)
            .options(
                selectinload(RiskAnalysis.factors),
                selectinload(RiskAnalysis.model_version),
            )
            .where(RiskAnalysis.transaction_id == transaction_id)
            .order_by(RiskAnalysis.created_at.desc(), RiskAnalysis.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        analysis_id: uuid.UUID,
    ) -> RiskAnalysis | None:
        """Retrieve risk analysis by primary key UUID."""
        stmt = (
            select(RiskAnalysis)
            .options(
                selectinload(RiskAnalysis.factors),
                selectinload(RiskAnalysis.model_version),
            )
            .where(RiskAnalysis.id == analysis_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
