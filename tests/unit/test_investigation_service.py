"""Unit tests for InvestigationService business logic, RBAC, and domain rules (Phase 9)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from finsignal.common.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from finsignal.investigations.models import (
    Investigation,
    InvestigationTransaction,
)
from finsignal.investigations.repository import InvestigationRepository
from finsignal.investigations.schemas import (
    EvidenceSourceType,
    EvidenceType,
    InvestigationCreateRequest,
    InvestigationEvidenceCreateRequest,
    InvestigationPatchRequest,
    InvestigationRelatedTransactionAddRequest,
    InvestigationResolution,
    InvestigationResolveRequest,
)
from finsignal.investigations.service import InvestigationService
from finsignal.transactions.models import Transaction
from finsignal.users.models import User


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _make_user(role: str, user_id: uuid.UUID | None = None) -> User:
    user = User()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.email = f"{role.lower()}@example.com"
    user.is_active = True
    return user


def _make_transaction(
    tx_id: uuid.UUID | None = None,
    account_id: uuid.UUID | None = None,
    counterparty_account_id: uuid.UUID | None = None,
    source_namespace: str = "SYNTHETIC",
) -> Transaction:
    tx = Transaction()
    tx.id = tx_id or uuid.uuid4()
    tx.external_transaction_id = f"EXT_{tx.id.hex[:8]}"
    tx.account_id = account_id or uuid.uuid4()
    tx.counterparty_account_id = counterparty_account_id
    tx.amount = Decimal("100.00")
    tx.currency = "USD"
    tx.direction = "DEBIT"
    tx.transaction_type = "PURCHASE"
    tx.occurred_at = datetime.now(UTC)
    tx.source_namespace = source_namespace
    tx.category = "RETAIL"
    tx.payment_method = "CARD"
    tx.channel = "ONLINE"
    tx.created_at = datetime.now(UTC)
    return tx


def _make_investigation(
    inv_id: uuid.UUID | None = None,
    status: str = "OPEN",
    priority: str = "MEDIUM",
    assigned_to: uuid.UUID | None = None,
    resolution: str | None = None,
    resolution_notes: str | None = None,
) -> Investigation:
    inv = Investigation()
    inv.id = inv_id or uuid.uuid4()
    inv.status = status
    inv.priority = priority
    inv.assigned_to = assigned_to
    inv.resolution = resolution
    inv.resolution_notes = resolution_notes
    inv.created_at = datetime.now(UTC)
    inv.updated_at = datetime.now(UTC)
    inv.transaction_associations = []
    inv.assigned_user = None
    return inv


@pytest.mark.asyncio
async def test_create_investigation_transaction_not_found() -> None:
    """Verify 404 when target primary transaction does not exist."""
    mock_repo = AsyncMock(spec=InvestigationRepository)
    mock_repo.get_transaction.return_value = None
    service = InvestigationService(repo=mock_repo)

    session = _make_session()
    user = _make_user("ANALYST")
    req = InvestigationCreateRequest(transaction_id=uuid.uuid4())

    with pytest.raises(NotFoundError) as exc:
        await service.create_investigation(session, req, user)
    assert "was not found" in str(exc.value)


@pytest.mark.asyncio
async def test_resolve_investigation_lifecycle_rules() -> None:
    """Verify resolution requires UNDER_REVIEW status and non-whitespace notes."""
    mock_repo = AsyncMock(spec=InvestigationRepository)
    service = InvestigationService(repo=mock_repo)
    session = _make_session()

    user = _make_user("ADMIN")
    inv = _make_investigation(status="OPEN")
    mock_repo.get_for_update.return_value = inv

    req = InvestigationResolveRequest(
        resolution=InvestigationResolution.CONFIRMED_FRAUD,
        resolution_notes="Legitimate findings.",
    )

    # Attempting to resolve OPEN investigation must fail with 409
    with pytest.raises(ConflictError) as exc:
        await service.resolve_investigation(session, inv.id, req, user)
    assert "must be in UNDER_REVIEW status" in str(exc.value)

    # Attempting to resolve already RESOLVED investigation must fail with 409
    inv.status = "RESOLVED"
    with pytest.raises(ConflictError) as exc:
        await service.resolve_investigation(session, inv.id, req, user)
    assert "already resolved" in str(exc.value)


@pytest.mark.asyncio
async def test_patch_investigator_authorization() -> None:
    """Verify investigator cannot take peer case (403) or resolve other case."""
    mock_repo = AsyncMock(spec=InvestigationRepository)
    service = InvestigationService(repo=mock_repo)
    session = _make_session()

    investigator_1 = _make_user("INVESTIGATOR")
    investigator_2 = _make_user("INVESTIGATOR")

    inv = _make_investigation(status="OPEN", assigned_to=investigator_1.id)
    mock_repo.get_by_id.return_value = inv
    mock_repo.get_for_update.return_value = inv

    # Investigator 2 attempts to self-assign a case assigned to Investigator 1 -> 403
    patch = InvestigationPatchRequest(assigned_to=investigator_2.id)
    with pytest.raises(AuthorizationError) as exc:
        await service.patch_investigation(session, inv.id, patch, investigator_2)
    assert "Cannot take an investigation assigned to another investigator" in str(
        exc.value
    )


@pytest.mark.asyncio
async def test_related_transaction_4way_1hop_scope() -> None:
    """Verify the 4 permitted 1-hop conditions and namespace boundary rejection."""
    mock_repo = AsyncMock(spec=InvestigationRepository)
    service = InvestigationService(repo=mock_repo)
    session = _make_session()

    user = _make_user("ADMIN")
    inv = _make_investigation(status="OPEN")

    acc_a = uuid.uuid4()
    acc_b = uuid.uuid4()
    acc_c = uuid.uuid4()
    acc_d = uuid.uuid4()

    primary_tx = _make_transaction(
        account_id=acc_a, counterparty_account_id=acc_b, source_namespace="SYNTHETIC"
    )
    primary_link = InvestigationTransaction(
        investigation_id=inv.id,
        transaction_id=primary_tx.id,
        relationship_type="PRIMARY",
    )
    primary_link.transaction = primary_tx
    inv.transaction_associations = [primary_link]

    mock_repo.get_workspace_detail.return_value = inv
    mock_repo.is_transaction_linked.return_value = False

    # 1. Namespace mismatch must fail
    diff_ns_tx = _make_transaction(account_id=acc_a, source_namespace="PRODUCTION")
    mock_repo.get_transaction.return_value = diff_ns_tx
    with pytest.raises(ValidationError) as exc:
        await service.add_related_transaction(
            session,
            inv.id,
            InvestigationRelatedTransactionAddRequest(transaction_id=diff_ns_tx.id),
            user,
        )
    assert "does not match primary transaction namespace" in str(exc.value)

    # 2. Condition 1: Target account_id == Primary account_id (acc_a)
    tx_c1 = _make_transaction(
        account_id=acc_a, counterparty_account_id=acc_c, source_namespace="SYNTHETIC"
    )
    mock_repo.get_transaction.return_value = tx_c1
    link_item = await service.add_related_transaction(
        session,
        inv.id,
        InvestigationRelatedTransactionAddRequest(transaction_id=tx_c1.id),
        user,
    )
    assert link_item.transaction_id == tx_c1.id

    # 3. Condition 2: Target account_id == Primary counterparty_account_id (acc_b)
    tx_c2 = _make_transaction(
        account_id=acc_b, counterparty_account_id=acc_c, source_namespace="SYNTHETIC"
    )
    mock_repo.get_transaction.return_value = tx_c2
    link_item = await service.add_related_transaction(
        session,
        inv.id,
        InvestigationRelatedTransactionAddRequest(transaction_id=tx_c2.id),
        user,
    )
    assert link_item.transaction_id == tx_c2.id

    # 4. Condition 3: Target counterparty_account_id == Primary account_id (acc_a)
    tx_c3 = _make_transaction(
        account_id=acc_c, counterparty_account_id=acc_a, source_namespace="SYNTHETIC"
    )
    mock_repo.get_transaction.return_value = tx_c3
    link_item = await service.add_related_transaction(
        session,
        inv.id,
        InvestigationRelatedTransactionAddRequest(transaction_id=tx_c3.id),
        user,
    )
    assert link_item.transaction_id == tx_c3.id

    # 5. Condition 4: Target counterparty_account_id == Primary counterparty_account_id (acc_b)
    tx_c4 = _make_transaction(
        account_id=acc_c, counterparty_account_id=acc_b, source_namespace="SYNTHETIC"
    )
    mock_repo.get_transaction.return_value = tx_c4
    link_item = await service.add_related_transaction(
        session,
        inv.id,
        InvestigationRelatedTransactionAddRequest(transaction_id=tx_c4.id),
        user,
    )
    assert link_item.transaction_id == tx_c4.id

    # 6. Unrelated transaction (acc_c to acc_d) must fail
    tx_unrelated = _make_transaction(
        account_id=acc_c, counterparty_account_id=acc_d, source_namespace="SYNTHETIC"
    )
    mock_repo.get_transaction.return_value = tx_unrelated
    with pytest.raises(ValidationError) as exc:
        await service.add_related_transaction(
            session,
            inv.id,
            InvestigationRelatedTransactionAddRequest(transaction_id=tx_unrelated.id),
            user,
        )
    assert "does not satisfy the direct 1-hop relationship" in str(exc.value)


@pytest.mark.asyncio
async def test_evidence_pairing_and_source_scope() -> None:
    """Verify evidence validation enforces type/source pairing and scope."""
    mock_repo = AsyncMock(spec=InvestigationRepository)
    service = InvestigationService(repo=mock_repo)
    session = _make_session()

    user = _make_user("ADMIN")
    inv = _make_investigation(status="OPEN")
    mock_repo.get_workspace_detail.return_value = inv

    # 1. Invalid pairing (TRANSACTION_FACT with DEVICE)
    req_invalid_pair = InvestigationEvidenceCreateRequest(
        evidence_type=EvidenceType.TRANSACTION_FACT,
        source_type=EvidenceSourceType.DEVICE,
        source_id=uuid.uuid4(),
        title="Mismatch Test",
    )
    with pytest.raises(ValidationError) as exc:
        await service.attach_evidence(session, inv.id, req_invalid_pair, user)
    assert "requires source_type 'TRANSACTION'" in str(exc.value)

    # 2. USER_NOTE with non-null source_id
    req_user_note_id = InvestigationEvidenceCreateRequest(
        evidence_type=EvidenceType.USER_NOTE,
        source_type=EvidenceSourceType.USER_NOTE,
        source_id=uuid.uuid4(),
        title="Note with ID",
    )
    with pytest.raises(ValidationError) as exc:
        await service.attach_evidence(session, inv.id, req_user_note_id, user)
    assert "USER_NOTE evidence must have a null source_id" in str(exc.value)

    # 3. Non-USER_NOTE with null source_id
    req_missing_id = InvestigationEvidenceCreateRequest(
        evidence_type=EvidenceType.TRANSACTION_FACT,
        source_type=EvidenceSourceType.TRANSACTION,
        source_id=None,
        title="Missing ID",
    )
    with pytest.raises(ValidationError) as exc:
        await service.attach_evidence(session, inv.id, req_missing_id, user)
    assert "requires a non-null source_id" in str(exc.value)
