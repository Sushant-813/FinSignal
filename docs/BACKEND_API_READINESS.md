# FinSignal — Backend API Readiness Specification

**Document:** `BACKEND_API_READINESS.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.0  
**Status:** Approved Architectural Specification (Implementation Scheduled for Phase F0)  
**Scope:** Backend Read Endpoints for Transaction Exploration, Detail Context & Dataset Import Visibility  
**Prerequisites:** ADR-077, `API_GUIDELINES.md`, `DATABASE_DESIGN.md`, `FRONTEND_PRD.md`

---

## 1. Purpose & Authority

Following the formal release of Backend + ML v1.0.0, the comprehensive frontend documentation audit established that while the backend platform possesses full transactional persistence, row-level ingestion provenance, and transaction-scoped risk intelligence, three collection/detail read endpoints documented in `API_GUIDELINES.md` (§21, §23, §70) were not implemented in the FastAPI router during Backend Phases 1–12:

1. `GET /api/v1/transactions` (Paginated Transaction Exploration & Multi-Field Filtering)
2. `GET /api/v1/transactions/{id}` (Single Transaction Fact Retrieval)
3. `GET /api/v1/datasets/imports` (Paginated Dataset Ingestion History)

Per **ADR-077 (ACCEPTED)**, these endpoints are approved as a separately scoped **Backend API Readiness Enhancement** executed within Phase F0. This specification establishes the exact engineering requirements, query boundaries, Pydantic schemas, database index evaluations, and security controls for these three endpoints prior to implementation.

**Authority & History Rule:** This document does not rewrite backend release history. Backend + ML v1.0.0 remains the released backend milestone. These endpoints expand the API surface to support the approved frontend MVP workflows without compromising raw-fact immutability, temporal integrity, or domain boundaries.

---

## 2. Endpoint 1: Transaction List (`GET /api/v1/transactions`)

### 2.1 Operational Purpose
Enables analysts and investigators to explore, paginate, sort, and filter financial transaction records across operational namespaces. This endpoint directly powers the primary **Transaction List** screen (`FRONTEND_PRD.md` Screen 7.1, §8.2).

### 2.2 Protocol & Route
- **Method:** `GET`
- **Path:** `/api/v1/transactions`
- **Tags:** `["Transactions"]`
- **Summary:** List and filter transactions with deterministic ordering
- **Authorization:** Authenticated user with role `ADMIN`, `ANALYST`, or `INVESTIGATOR`.

### 2.3 Query Parameters & Supported Filters

| Parameter | Type | Required | Default | Validation & Rules | Feasibility & Query Implementation |
|---|---|---|---|---|---|
| `page` | `int` | No | `1` | `ge=1` | 1-indexed pagination. Offset = `(page - 1) * page_size`. |
| `page_size` | `int` | No | `50` | `ge=1, le=100` | Bounded items per page. |
| `source_namespace` | `str` | No | `"SYNTHETIC"` | Pattern `^[A-Z0-9_]{3,64}$` | **Mandatory namespace fence.** Queries are strictly scoped to the evaluated namespace. Format validated by regex, and existence verified against the database via `verify_namespace_exists(session, namespace)`. Nonexistent namespace returns HTTP 404 `NAMESPACE_NOT_FOUND`. |
| `account_id` | `UUID` | No | `None` | Valid UUIDv4 | Filters transactions where `account_id = :account_id`. Fully supported by existing index `ix_transactions_account_id`. |
| `merchant_id` | `UUID` | No | `None` | Valid UUIDv4 | Filters transactions where `merchant_id = :merchant_id`. Supported by existing index `ix_transactions_merchant_id`. |
| `device_id` | `UUID` | No | `None` | Valid UUIDv4 | Filters transactions where `device_id = :device_id`. Supported by existing index `ix_transactions_device_id`. |
| `location_id` | `UUID` | No | `None` | Valid UUIDv4 | Filters transactions where `location_id = :location_id`. Supported by existing index `ix_transactions_location_id`. |
| `transaction_type` | `str` | No | `None` | String (max 32) | Filters transactions where `transaction_type = :transaction_type` (e.g. `PAYMENT`, `TRANSFER`). |
| `direction` | `str` | No | `None` | Pattern `^(DEBIT\|CREDIT)$` | Filters by flow direction. Fully supported by column constraint `chk_transactions_direction`. |
| `category` | `str` | No | `None` | String (max 64) | Filters by transaction category (e.g. `GROCERY`, `TRAVEL`). Matches `transactions.category`. |
| `currency` | `str` | No | `None` | Length = 3, uppercase | ISO 4217 currency code (e.g. `INR`). |
| `from_time` | `datetime` | No | `None` | UTC ISO 8601 | Start boundary (inclusive): `occurred_at >= :from_time`. Supported by index `ix_transactions_occurred_at`. |
| `to_time` | `datetime` | No | `None` | UTC ISO 8601 | End boundary (exclusive): `occurred_at < :to_time`. Inverted intervals (`from_time >= to_time`) return HTTP 422. |
| `min_amount` | `Decimal` | No | `None` | `ge=0.01` | Minimum transaction amount: `amount >= :min_amount`. |
| `max_amount` | `Decimal` | No | `None` | `ge=0.01` | Maximum transaction amount: `amount <= :max_amount`. `min_amount > max_amount` returns HTTP 422. |
| `risk_level` | `str` | No | `None` | Pattern `^(LOW\|MEDIUM\|HIGH\|CRITICAL)$` | Filters by latest evaluated risk tier. **Feasibility note:** `risk_level` is not a column on `transactions` (ADR-009). See §2.4 for query execution architecture. |
| `sort_by` | `str` | No | `"occurred_at"` | Whitelist: `occurred_at`, `amount`, `created_at` | Sort column. Unlisted values return HTTP 422 `UNSUPPORTED_SORT_FIELD`. |
| `sort_order` | `str` | No | `"desc"` | Pattern `^(asc\|desc)$` | Sort direction (case-insensitive). |

### 2.4 Filter Feasibility & `risk_level` Query Architecture
Per ADR-009 ("Separate Raw Facts from Derived Intelligence"), the `transactions` table stores only raw financial facts. Risk levels are computed asynchronously or on-demand and stored in `risk_analyses`.

- **Direct Facts:** Filters on `account_id`, `merchant_id`, `device_id`, `location_id`, `direction`, `category`, `currency`, `occurred_at`, and `amount` operate directly on indexed columns of the `transactions` table.
- **`risk_level` Filter Evaluation:**
  - A transaction may have zero, one, or multiple risk analyses across different model versions.
  - When `risk_level` is specified as a query parameter, the query must match transactions whose **latest** persisted risk analysis has `risk_analyses.risk_level = :risk_level`.
  - **SQL Query Strategy:** Execute via a correlated `EXISTS` subquery or a lateral join on `risk_analyses`:
    ```sql
    EXISTS (
        SELECT 1 FROM risk_analyses ra
        WHERE ra.transaction_id = transactions.id
          AND ra.risk_level = :risk_level
          AND ra.created_at = (
              SELECT MAX(ra_inner.created_at)
              FROM risk_analyses ra_inner
              WHERE ra_inner.transaction_id = transactions.id
          )
    )
    ```
  - **Constraint:** Transactions that have never undergone risk scoring will not match any `risk_level` filter. If `risk_level` is omitted, the query executes as a standard relational scan over `transactions` without joining `risk_analyses`.

### 2.5 Ordering & Deterministic Tie-Breaking
To prevent non-deterministic page shifts when transactions share identical timestamps or amounts:
- Default sorting: `ORDER BY transactions.occurred_at DESC, transactions.id DESC`
- Explicit sorting by `amount`: `ORDER BY transactions.amount [ASC|DESC], transactions.occurred_at DESC, transactions.id DESC`
- Explicit sorting by `created_at`: `ORDER BY transactions.created_at [ASC|DESC], transactions.id DESC`

### 2.6 Response Schema (`TransactionListResponse`)

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "source_namespace": "SYNTHETIC",
      "external_transaction_id": "TXN_00012345",
      "account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
      "counterparty_account_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
      "merchant_id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
      "device_id": "d4e5f6a7-b89c-0d1e-2f3a-4b5c6d7e8f9a",
      "location_id": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "occurred_at": "2026-09-15T14:30:00Z",
      "amount": "75000.00",
      "currency": "INR",
      "transaction_type": "TRANSFER",
      "direction": "DEBIT",
      "category": "OTHER",
      "payment_method": "IMPS",
      "channel": "MOBILE_APP",
      "first_seen_import_id": "f6a7b89c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
      "created_at": "2026-09-15T14:30:05.123456Z"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1420,
  "total_pages": 29
}
```

- **Empty Result:** When no transactions match the query filters, return `HTTP 200 OK` with `"items": []`, `"total": 0`, and `"total_pages": 0`. An empty collection is not an error.
- **Monetary Precision:** The `amount` field must strictly serialize as a two-decimal fixed-point string (`MoneyStr`, e.g. `"75000.00"`), never a JavaScript IEEE 754 floating-point number.

---

## 3. Endpoint 2: Transaction Detail (`GET /api/v1/transactions/{id}`)

### 3.1 Operational Purpose
Retrieves the complete, authoritative record of a single transaction fact and its relational reference entities. Serves the **Transaction Detail** workspace (`FRONTEND_PRD.md` Screen 7.1, §8.3).

### 3.2 Protocol & Route
- **Method:** `GET`
- **Path:** `/api/v1/transactions/{transaction_id}`
- **Tags:** `["Transactions"]`
- **Summary:** Get complete transaction fact context
- **Authorization:** Authenticated user with role `ADMIN`, `ANALYST`, or `INVESTIGATOR`.

### 3.3 Identifier Format & Validation
- Path parameter: `transaction_id: uuid.UUID`
- Invalid UUID strings return `HTTP 422 Unprocessable Entity` with `ErrorResponse`.

### 3.4 Namespace Scoping & Fencing
- **Query Parameter:** Optional `source_namespace: str | None = None` (Pattern `^[A-Z0-9_]{3,64}$`).
- When provided or when namespace scoping is enforced by user session context, the query executes as `WHERE id = :transaction_id AND source_namespace = :source_namespace`.
- **Anti-Enumeration & Isolation:** If the transaction ID exists in the database but belongs to another namespace, return `HTTP 404 Not Found` with `TRANSACTION_NOT_FOUND`. Do not disclose whether the ID exists in an unauthorized or unselected namespace.

### 3.5 Risk Intelligence Separation Boundary
In strict adherence to `API_GUIDELINES.md` §21.2 and architectural guidelines:
- **No Risk Payload Duplication:** The detail response does **not** duplicate the full 34-feature vector, model normalization parameters, or risk factor lists. Those reside authoritatively in the dedicated risk endpoint (`GET /api/v1/transactions/{id}/risk`).
- **Lightweight Reference:** The transaction detail response includes a lightweight nullable snapshot reference:
  - `latest_risk_analysis_id: uuid.UUID | None`
  - `latest_risk_score: float | None`
  - `latest_risk_level: str | None` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- This allows the frontend to render the status badge immediately while lazily fetching the explainability factor breakdown if the user opens the risk inspection panel.

### 3.6 Response Schema (`TransactionDetailResponse`)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source_namespace": "SYNTHETIC",
  "external_transaction_id": "TXN_00012345",
  "first_seen_import_id": "f6a7b89c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
  "account_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "counterparty_account_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
  "merchant_id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
  "device_id": "d4e5f6a7-b89c-0d1e-2f3a-4b5c6d7e8f9a",
  "location_id": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
  "occurred_at": "2026-09-15T14:30:00Z",
  "amount": "75000.00",
  "currency": "INR",
  "transaction_type": "TRANSFER",
  "direction": "DEBIT",
  "category": "OTHER",
  "payment_method": "IMPS",
  "channel": "MOBILE_APP",
  "created_at": "2026-09-15T14:30:05.123456Z",
  "account": {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "external_account_id": "ACC_001234",
    "account_type": "SAVINGS",
    "status": "ACTIVE"
  },
  "counterparty_account": {
    "id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
    "external_account_id": "ACC_005678",
    "account_type": "CHECKING",
    "status": "ACTIVE"
  },
  "merchant": {
    "id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
    "external_merchant_id": "MERCH_00012",
    "name": "Acme Electronics",
    "merchant_category_code": "5732"
  },
  "device": {
    "id": "d4e5f6a7-b89c-0d1e-2f3a-4b5c6d7e8f9a",
    "external_device_id": "DEV_00089",
    "device_type": "SMARTPHONE"
  },
  "location": {
    "id": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
    "external_location_id": "LOC_00045",
    "city": "Mumbai",
    "country_code": "IND"
  },
  "latest_risk": {
    "analysis_id": "8899aabb-ccdd-eeff-0011-223344556677",
    "score": 82.50,
    "risk_level": "CRITICAL",
    "model_version": "1.0.0",
    "evaluated_at": "2026-09-15T14:30:06Z"
  }
}
```

### 3.7 Not-Found Behavior
If `transaction_id` does not exist in the database, return:
- **HTTP Status:** `404 Not Found`
- **Error Response Envelope:**
  ```json
  {
    "error": {
      "code": "TRANSACTION_NOT_FOUND",
      "message": "Transaction '550e8400-e29b-41d4-a716-446655440000' not found.",
      "details": {
        "transaction_id": "550e8400-e29b-41d4-a716-446655440000"
      },
      "request_id": "req-abcdef123456"
    }
  }
  ```

---

## 4. Endpoint 3: Dataset Import Listing (`GET /api/v1/datasets/imports`)

### 4.1 Operational Purpose
Enables administrators and analysts to view historical ingestion runs, inspect processing counts (valid vs invalid rows), identify duplicate upload attempts, and select interrupted imports for recovery. Powers the **Dataset Management** screen (`FRONTEND_PRD.md` Screen 7.1, §8.5).

### 4.2 Protocol & Route
- **Method:** `GET`
- **Path:** `/api/v1/datasets/imports`
- **Tags:** `["Datasets"]`
- **Summary:** List and filter dataset import executions
- **Authorization:** Authenticated user with role `ADMIN`, `ANALYST`, or `INVESTIGATOR`.

### 4.3 Query Parameters & Filters

| Parameter | Type | Required | Default | Validation & Rules |
|---|---|---|---|---|
| `page` | `int` | No | `1` | `ge=1` |
| `page_size` | `int` | No | `20` | `ge=1, le=100` |
| `source_namespace` | `str` | No | `"SYNTHETIC"` | Pattern `^[A-Z0-9_]{3,64}$` |
| `status` | `str` | No | `None` | Pattern `^(PENDING\|PROCESSING\|COMPLETED\|FAILED)$` |
| `source_type` | `str` | No | `None` | String (max 32, e.g. `SYNTHETIC`) |
| `from_time` | `datetime` | No | `None` | UTC ISO 8601; filters `started_at >= :from_time` |
| `to_time` | `datetime` | No | `None` | UTC ISO 8601; filters `started_at < :to_time` |

### 4.4 Default Ordering
`ORDER BY dataset_imports.started_at DESC, dataset_imports.id DESC`

### 4.5 Exclusion of Large Validation Error Collections
**Strict Mandate:** Individual validation error records from `dataset_import_errors` **must not** be included in list results. Ingestion runs with thousands of bad rows would otherwise bloat collection responses into multi-megabyte payloads.
- List items return `DatasetImportResponse` summaries (row counts, statuses, hashes, and timestamps).
- Granular error records remain accessible exclusively via `GET /api/v1/datasets/imports/{import_id}` (`DatasetImportDetailResponse`).

### 4.6 Response Schema (`DatasetImportListResponse`)

```json
{
  "items": [
    {
      "id": "f6a7b89c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
      "source_namespace": "SYNTHETIC",
      "status": "COMPLETED",
      "source_type": "SYNTHETIC",
      "filename": "transactions_sample_250k.csv",
      "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "total_rows": 250000,
      "valid_rows": 249850,
      "invalid_rows": 150,
      "started_at": "2026-10-20T10:00:00Z",
      "completed_at": "2026-10-20T10:04:12Z",
      "is_duplicate": false
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 12,
  "total_pages": 1
}
```

---

## 5. Database Performance & Index Analysis

Before authoring code or proposing migrations, existing indexes across tables were audited against the expected query patterns.

### 5.1 Transactions Table (`transactions`)
- **Existing Indexes (from `0002_core_operational_schema.py` and `0003_account_import_namespace.py`):**
  1. `uq_transactions_canonical_id`: `("source_namespace", "account_id", "external_transaction_id")`
  2. `ix_transactions_account_id`: `("account_id")`
  3. `ix_transactions_occurred_at`: `("occurred_at")`
  4. `ix_transactions_account_occurred`: `("account_id", "occurred_at")`
  5. `ix_transactions_first_seen_import_id`: `("first_seen_import_id")`
  6. `ix_transactions_merchant_id`: `("merchant_id")`
  7. `ix_transactions_device_id`: `("device_id")`
  8. `ix_transactions_location_id`: `("location_id")`

- **Performance Evaluation for List Queries:**
  - Single-entity queries (e.g. `account_id + occurred_at`, `merchant_id`, `device_id`) are covered by existing btree indexes.
  - General list query: `WHERE source_namespace = :ns ORDER BY occurred_at DESC, id DESC LIMIT :limit OFFSET :offset`.
  - **Query Plan Expectations:** In PostgreSQL, the query engine can leverage `ix_transactions_occurred_at` combined with a bitmap index or sequential filter on `source_namespace`. Target operational latency is `< 50 ms` (p95) at the MVP dataset volume of 250,000 rows.
  - **Pagination Count Considerations:** Calculating `SELECT COUNT(*)` for total page calculation across 250k rows requires evaluating the filter conditions. During Phase F0 implementation, query latency for both data and count queries must be validated using `EXPLAIN (ANALYZE, BUFFERS)` under realistic MVP data loads.
  - **Migration Verdict:** **No new index or migration is required for MVP baseline.** Speculatively introducing a composite `(source_namespace, occurred_at DESC)` index prior to empirical execution analysis is avoided. If `EXPLAIN (ANALYZE)` during Phase F0 testing shows excessive buffer reads or latency exceeding the 50 ms budget, an index migration may be introduced at that time.

### 5.2 Risk Analyses Table (`risk_analyses`)
- **Existing Indexes (from `0005_risk_scoring_schema.py`):**
  1. `ix_risk_analyses_tx_created`: `("transaction_id", "created_at")`
  2. `ix_risk_analyses_level_created`: `("risk_level", "created_at")`
  3. `ix_risk_analyses_model_score`: `("model_version_id", "score")`
  4. `uq_risk_analyses_identity`: `("transaction_id", "model_version_id", "config_version", "feature_vector_hash")`

- **Performance Evaluation:**
  - Correlated lookups for the latest risk score (`ra.transaction_id = transactions.id`) utilize `ix_risk_analyses_tx_created` `("transaction_id", "created_at")` via index condition lookups.
  - **Filter & Subquery Cost:** Filtering transaction lists by `risk_level` requires evaluating the latest risk record for each transaction candidate. When combined with pagination count queries, this subquery introduces additional cost. The Phase F0 implementation must profile this query pattern with `EXPLAIN (ANALYZE, BUFFERS)` to verify whether an additional composite index on `(transaction_id, created_at DESC, risk_level)` is warranted.
  - **Migration Verdict:** No migration required prior to empirical profiling.

### 5.3 Dataset Imports Table (`dataset_imports`)
- **Existing Indexes:**
  1. `ix_dataset_imports_status`: `("status")`
  2. `ix_dataset_imports_dataset_version_id`: `("dataset_version_id")`
  3. `uq_dataset_imports_active_hash`: `("source_namespace", "file_hash") WHERE status IN ('PENDING', 'PROCESSING')`

- **Performance Evaluation:**
  - Ingestion runs are low-cardinality in operational environments (dozens to hundreds of records).
  - Sorting by `started_at DESC` across < 1,000 rows is performed efficiently by PostgreSQL in memory (using `work_mem` Sort node) well within target latency (< 20 ms) without requiring a dedicated btree index on `started_at`.
  - **Migration Verdict:** No migration required.

---

## 6. Security, RBAC & Query Boundary Defense

### 6.1 Role-Based Access Control (RBAC)
- All three endpoints are protected by `require_roles("ADMIN", "ANALYST", "INVESTIGATOR")`.
- Anonymous requests return `HTTP 401 Unauthorized` with `AUTHENTICATION_REQUIRED`.
- Non-internal roles (if added in future) return `HTTP 403 Forbidden` with `INSUFFICIENT_PERMISSIONS`.

### 6.2 Mandatory Namespace Isolation
- FinSignal strictly segregates transaction facts and dataset imports by `source_namespace`.
- Callers cannot query across namespaces in a single request.
- **List Endpoints:** The `source_namespace` parameter is validated against regex `^[A-Z0-9_]{3,64}$` and verified against the database via `verify_namespace_exists(session, namespace)`. Nonexistent namespaces return `HTTP 404 Not Found` with `NAMESPACE_NOT_FOUND`.
- **Detail Endpoints:** Detail lookup (`GET /api/v1/transactions/{id}`) validates namespace scoping to prevent cross-namespace information disclosure. If a transaction belongs to another namespace, return `HTTP 404 Not Found` (`TRANSACTION_NOT_FOUND`).

### 6.3 Anti-Enumeration & Query Abuse Protection
- **UUID Identifiers:** Primary keys are non-sequential UUIDv4 values. Attackers cannot enumerate transactions sequentially.
- **Strict Pagination Bounds:** `page_size` is strictly clamped to `min=1, max=100`. Unlimited queries (`SELECT *`) are impossible.
- **SQL Injection Prevention:** Sorting columns and directions are verified against compile-time static whitelists before constructing SQLAlchemy expressions. Raw SQL string concatenation is strictly forbidden.
- **N+1 Query Prevention:** For `GET /api/v1/transactions/{id}`, relational associations (`account`, `counterparty_account`, `merchant`, `device`, `location`) must be eagerly loaded using SQLAlchemy `joinedload` or `selectinload` to prevent N+1 queries.

---

## 7. Recommended Implementation Sequence for Phase F0

When implementation begins in Phase F0, developers must follow this strict internal sequence:

```text
Step 1: Pydantic DTOs & Schemas
  ├── src/finsignal/transactions/schemas.py (TransactionSummaryItem, TransactionListResponse, TransactionDetailResponse)
  └── src/finsignal/dataset/schemas.py (DatasetImportListResponse)
        ↓
Step 2: Database Repositories
  ├── src/finsignal/transactions/repository.py (TransactionRepository: list_transactions, get_transaction_detail)
  └── src/finsignal/dataset/repository.py (DatasetImportRepository: list_imports)
        ↓
Step 3: Domain Services
  ├── src/finsignal/transactions/service.py (TransactionService)
  └── src/finsignal/dataset/service.py (DatasetImportService.list_imports)
        ↓
Step 4: Router Assembly & Registration
  ├── src/finsignal/api/v1/transactions.py (Mount GET /, GET /{id})
  ├── src/finsignal/api/v1/datasets.py (Mount GET /imports)
  └── src/finsignal/api/router.py (Register transactions router)
        ↓
Step 5: Automated Regression Testing
  ├── tests/unit/test_transaction_schemas.py
  ├── tests/api/test_transactions_api.py (Auth, filters, pagination, 404, tie-breaking)
  └── tests/api/test_dataset_imports_api.py (Auth, status filters, pagination)
        ↓
Step 6: Contract Drift & OpenAPI Verification
  └── Generate updated types via openapi-typescript (ADR-076)
```

**Verification Gate:** Phase F0 cannot be marked complete until all three endpoints achieve 100% test pass rate with zero Mypy/Ruff errors and verified OpenAPI output.

