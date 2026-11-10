"""PostgreSQL repository for dataset import listing and namespace verification."""

import math
import uuid
from datetime import datetime

from sqlalchemy import ColumnElement, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from finsignal.dataset.models import DatasetImport


class DatasetImportRepository:
    """Async SQLAlchemy repository for paginated dataset import queries."""

    async def verify_namespace_exists(
        self, session: AsyncSession, namespace: str
    ) -> bool:
        """Check whether a source namespace exists in accounts or dataset_imports."""
        stmt_acc = text("SELECT 1 FROM accounts WHERE source_namespace = :ns LIMIT 1")
        res_acc = await session.execute(stmt_acc, {"ns": namespace})
        if res_acc.scalar_one_or_none() is not None:
            return True

        stmt_imp = text(
            "SELECT 1 FROM dataset_imports WHERE source_namespace = :ns LIMIT 1"
        )
        res_imp = await session.execute(stmt_imp, {"ns": namespace})
        return res_imp.scalar_one_or_none() is not None

    def _build_filter_conditions(
        self,
        *,
        source_namespace: str,
        status: str | None = None,
        source_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[ColumnElement[bool]]:
        """Assemble parameterized WHERE predicates shared by count and page queries."""
        conditions: list[ColumnElement[bool]] = [
            DatasetImport.source_namespace == source_namespace
        ]
        if status is not None:
            conditions.append(DatasetImport.status == status)
        if source_type is not None:
            conditions.append(DatasetImport.source_type == source_type)
        if from_time is not None:
            conditions.append(DatasetImport.started_at >= from_time)
        if to_time is not None:
            conditions.append(DatasetImport.started_at < to_time)
        return conditions

    async def list_imports(
        self,
        session: AsyncSession,
        *,
        source_namespace: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        source_type: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> tuple[list[DatasetImport], int, int]:
        """Execute count-first paginated dataset import listing ordered by started_at DESC, id DESC."""
        conditions = self._build_filter_conditions(
            source_namespace=source_namespace,
            status=status,
            source_type=source_type,
            from_time=from_time,
            to_time=to_time,
        )

        count_stmt = select(func.count(DatasetImport.id)).where(*conditions)
        total: int = (await session.execute(count_stmt)).scalar_one()
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        if total == 0 or offset >= total:
            return [], total, total_pages

        stmt = (
            select(DatasetImport)
            .where(*conditions)
            .order_by(DatasetImport.started_at.desc(), DatasetImport.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list((await session.execute(stmt)).scalars().all())
        return items, total, total_pages

    async def get_by_id(
        self, session: AsyncSession, import_id: uuid.UUID
    ) -> DatasetImport | None:
        """Retrieve a single dataset import record by UUID."""
        stmt = select(DatasetImport).where(DatasetImport.id == import_id)
        return (await session.execute(stmt)).scalar_one_or_none()
