# API_GUIDELINES.md

# FinSignal — API Guidelines

## 1. Document Purpose

This document defines the HTTP API conventions for **FinSignal — Financial Transaction Intelligence & Investigation Platform**.

It establishes consistent rules for:

- API versioning
- authentication
- authorization
- resource naming
- request/response structures
- validation
- pagination
- filtering
- sorting
- error handling
- idempotency
- transaction ingestion
- risk-analysis endpoints
- investigation workflows
- evidence
- AI summaries
- auditability
- API documentation

The API should expose stable application capabilities without leaking internal implementation details.

---

# 2. API Design Principles

FinSignal APIs should follow these principles:

1. Resource-oriented design.
2. Explicit authentication and authorization.
3. Consistent response structures.
4. Predictable validation errors.
5. Stable identifiers.
6. Pagination for potentially large collections.
7. Server-authoritative financial and analytical values.
8. No frontend-side recreation of backend risk calculations.
9. Explicit lifecycle transitions.
10. Versioned contracts.
11. Safe handling of sensitive data.
12. Clear distinction between facts, intelligence, and human decisions.

---

# 3. API Technology

The backend API uses:

```text
Python
FastAPI
Pydantic
PostgreSQL
JWT authentication
```

FastAPI automatically exposes OpenAPI documentation.

Development documentation should normally be available through:

```text
/docs
/openapi.json
```

A separate production documentation exposure policy may be applied later.

---

# 4. API Base Path

The API should use a versioned base path:

```text
/api/v1
```

Example:

```text
/api/v1/auth/login
/api/v1/transactions
/api/v1/investigations
```

Versioning is explicit so future breaking API changes do not silently affect existing clients.

---

# 5. Resource Naming

Use plural nouns for collection resources.

Preferred:

```text
/accounts
/transactions
/merchants
/devices
/locations
/investigations
```

Avoid:

```text
/getAccounts
/createTransaction
/fetchInvestigations
```

HTTP methods express the operation.

---

# 6. HTTP Methods

Use standard HTTP semantics.

| Method | Purpose |
|---|---|
| `GET` | Retrieve resource(s) |
| `POST` | Create resource or execute non-idempotent operation |
| `PUT` | Full replacement when appropriate |
| `PATCH` | Partial update |
| `DELETE` | Delete resource where deletion is permitted |

For immutable financial transactions:

```text
POST /transactions
```

may create the transaction.

The transaction itself should not support arbitrary mutation.

---

# 7. HTTP Status Codes

Recommended status codes:

| Status | Meaning |
|---|---|
| `200 OK` | Successful retrieval/update/action |
| `201 Created` | Resource created |
| `202 Accepted` | Accepted for asynchronous processing |
| `204 No Content` | Successful operation with no body |
| `400 Bad Request` | Malformed request |
| `401 Unauthorized` | Missing/invalid authentication |
| `403 Forbidden` | Authenticated but insufficient permissions |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | State or uniqueness conflict |
| `422 Unprocessable Entity` | Validation failure |
| `429 Too Many Requests` | Rate limit exceeded |
| `500 Internal Server Error` | Unexpected server failure |
| `503 Service Unavailable` | Dependency/system unavailable |

FastAPI's validation behavior should be standardized rather than replaced inconsistently.

---

# 8. Authentication

Authentication uses:

```text
JWT access tokens
```

The normal flow is:

```text
POST /api/v1/auth/register
        ↓
POST /api/v1/auth/login
        ↓
access token
        ↓
Authorization: Bearer <token>
```

Protected endpoints require a valid access token.

---

# 9. Authentication Endpoints

## 9.1 Register

```http
POST /api/v1/auth/register
```

Request:

```json
{
  "email": "analyst@example.com",
  "password": "secure-password"
}
```

Response:

```json
{
  "id": "uuid",
  "email": "analyst@example.com",
  "role": "ANALYST"
}
```

The API must never return:

```text
password
password_hash
```

Duplicate registration attempts return `409 Conflict` with error code `STATE_CONFLICT`.

---

## 9.2 Login

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "analyst@example.com",
  "password": "secure-password"
}
```

Response:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Exact token lifetime is controlled through configuration.

---

## 9.3 Current User

```http
GET /api/v1/auth/me
```

Response:

```json
{
  "id": "uuid",
  "email": "analyst@example.com",
  "role": "ANALYST",
  "is_active": true
}
```

This endpoint is used by the frontend to determine the authenticated user's identity and permissions.

---

## 9.4 Logout

JWT access tokens are stateless by default.

The MVP should define one explicit logout strategy rather than pretending that deleting a browser token invalidates an already-issued JWT server-side.

Possible strategies:

### Option A — Short-lived access token

Use short token lifetime and remove the token client-side.

### Option B — Token revocation

Maintain a server-side revoked-token identifier or token version.

### Option C — Refresh-token architecture

Introduce refresh tokens and server-side refresh-token revocation.

The initial implementation decision should be documented in `SECURITY.md` and `DECISIONS.md`.

---

# 10. Role-Based Authorization

Initial roles:

```text
ADMIN
ANALYST
INVESTIGATOR
```

Conceptual permissions:

| Capability | ADMIN | ANALYST | INVESTIGATOR |
|---|---:|---:|---:|
| View transactions | Yes | Yes | Yes |
| Import datasets | Yes | Yes | Optional |
| Run analytics | Yes | Yes | Yes |
| View risk results | Yes | Yes | Yes |
| Create investigations | Yes | Yes | Yes |
| Assign investigations | Yes | Limited | Yes |
| Add evidence | Yes | Yes | Yes |
| Resolve investigations | Yes | No/Configurable | Yes |
| Manage users | Yes | No | No |

Exact authorization policy is finalized in `SECURITY.md`.

Authorization must be enforced server-side.

---

# 11. Authentication vs Authorization

These concepts must remain separate.

Authentication answers:

```text
Who are you?
```

Authorization answers:

```text
What are you allowed to do?
```

A valid JWT does not automatically grant access to every endpoint.

---

# 12. Common Response Envelope

For single resources, the preferred response is a direct resource object.

Example:

```json
{
  "id": "uuid",
  "amount": 1250.50,
  "currency": "INR"
}
```

Avoid unnecessary nesting such as:

```json
{
  "success": true,
  "data": {
    ...
  }
}
```

unless the API has a strong reason to require a global envelope.

Consistency is more important than ceremony.

---

# 13. Collection Responses

Collection endpoints should use a consistent pagination structure.

Example:

```json
{
  "items": [
    {
      "id": "uuid"
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 250,
  "total_pages": 10
}
```

For very large datasets, cursor pagination may be introduced later.

---

# 14. Pagination

Collection endpoints must not return unlimited records.

Recommended parameters:

```text
page
page_size
```

Example:

```http
GET /api/v1/transactions?page=1&page_size=50
```

Suggested limits:

```text
default page_size = 25
maximum page_size = 100
```

The exact limits may be configuration-driven.

---

# 15. Cursor Pagination

Cursor pagination may be introduced for high-volume transaction feeds.

Example:

```http
GET /api/v1/transactions?cursor=<cursor>&limit=50
```

Cursor pagination is preferred when:

- data changes frequently
- deep pagination is required
- large transaction collections are queried

It is not necessary for every MVP endpoint.

---

# 16. Sorting

Use explicit query parameters.

Example:

```http
GET /api/v1/transactions?sort=occurred_at&order=desc
```

Only allow whitelisted sortable fields.

Do not pass raw client-provided column names directly into SQL.

---

# 17. Filtering

Filters should be explicit.

Example:

```http
GET /api/v1/transactions?
account_id=<uuid>
&risk_level=HIGH
&transaction_type=TRANSFER
&from=2026-09-01T00:00:00Z
&to=2026-09-30T23:59:59Z
```

The API should validate:

- supported filter names
- value types
- date formats
- allowed enum values
- maximum query complexity where necessary

---

# 18. Search

Search should be scoped to meaningful fields.

Examples:

```text
merchant_name
external_transaction_id
account identifier
investigation identifier
```

Do not expose unrestricted database search through a generic:

```text
?q=<anything>
```

endpoint.

---

# 19. Date and Time Parameters

API timestamps use ISO-8601 format.

Example:

```text
2026-09-15T14:30:00Z
```

All backend timestamps should be timezone-aware.

Clients should not assume server-local time.

---

# 20. Monetary Values

Monetary values should be returned as decimal-safe representations.

Example:

```json
{
  "amount": "1250.50",
  "currency": "INR"
}
```

Returning monetary values as strings avoids accidental floating-point interpretation in JavaScript clients.

The exact API representation should be standardized across all financial endpoints.

---

# 21. Transaction API

## 21.1 List Transactions

```http
GET /api/v1/transactions
```

Supported filters may include:

```text
account_id
merchant_id
device_id
location_id
transaction_type
direction
category
risk_level
from
to
min_amount
max_amount
```

Example:

```http
GET /api/v1/transactions?account_id=<uuid>&risk_level=HIGH
```

---

## 21.2 Get Transaction

```http
GET /api/v1/transactions/{transaction_id}
```

Response should include core transaction facts.

Example:

```json
{
  "id": "uuid",
  "source_namespace": "SYNTHETIC",
  "external_transaction_id": "TXN_00012345",
  "account_id": "uuid",
  "merchant_id": "uuid",
  "occurred_at": "2026-09-15T14:30:00Z",
  "amount": "75000.00",
  "currency": "INR",
  "transaction_type": "TRANSFER",
  "direction": "DEBIT",
  "category": "OTHER"
}
```

Risk intelligence should be returned separately or as an explicitly named nested representation.

---

# 22. Transaction Creation

For controlled ingestion:

```http
POST /api/v1/transactions
```

However, bulk transaction import should generally use the dataset ingestion workflow rather than exposing unrestricted transaction creation.

The API must distinguish:

```text
single controlled transaction creation
```

from:

```text
bulk dataset ingestion
```

---

# 23. Dataset Import API

## 23.1 Create Import

```http
POST /api/v1/datasets/imports
```

Accepts multipart form-data containing:
- `file`: CSV file payload (max 50 MB, must be valid UTF-8).
- `source_namespace`: Target namespace string (default: `"SYNTHETIC"`).
- `source_type`: Origin type (default: `"SYNTHETIC"`).

### RBAC Requirement
Requires role `ADMIN` or `ANALYST`.

### Validation and Deduplication Guarantees
- Validates file extension (`.csv`), file size ($\le 50$ MB), non-empty payload, and UTF-8 encoding.
- Computes SHA-256 stream hash over uploaded bytes.
- Acquires transaction-scoped PostgreSQL advisory lock on `(source_namespace, file_hash)`.
- If an import for `(source_namespace, file_hash)` is currently `PENDING` or `PROCESSING`, returns `HTTP 409 Conflict` with code `"IMPORT_IN_PROGRESS"`.
- If an import with identical bytes has already reached `COMPLETED` in the same namespace, returns `HTTP 200 OK` with the existing import summary and `is_duplicate = true` without reprocessing.
- If the import is new, ingests rows in bounded batches, committing row-level provenance to `transaction_import_records` and returning `HTTP 201 Created` with `is_duplicate = false`.

### Response Schema (`DatasetImportResponse`)

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "source_namespace": "SYNTHETIC",
  "filename": "transactions.csv",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "source_type": "SYNTHETIC",
  "status": "COMPLETED",
  "total_rows": 250000,
  "valid_rows": 249700,
  "invalid_rows": 300,
  "started_at": "2026-10-22T00:00:00Z",
  "completed_at": "2026-10-22T00:01:30Z",
  "is_duplicate": false
}
```

---

## 23.2 Import Details & Errors

```http
GET /api/v1/datasets/imports/{import_id}
```

### RBAC Requirement
Requires role `ADMIN`, `ANALYST`, or `INVESTIGATOR`.

### Response Schema (`DatasetImportDetailResponse`)
Returns import status, summary counters, and an embedded list of recorded validation/quarantine errors (up to 100 items from `dataset_import_errors`):

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "source_namespace": "SYNTHETIC",
  "filename": "transactions.csv",
  "file_hash": "e3b0c442...",
  "source_type": "SYNTHETIC",
  "status": "COMPLETED",
  "total_rows": 250000,
  "valid_rows": 249700,
  "invalid_rows": 300,
  "started_at": "2026-10-22T00:00:00Z",
  "completed_at": "2026-10-22T00:01:30Z",
  "is_duplicate": false,
  "errors": [
    {
      "row_number": 1482,
      "field_name": "amount",
      "error_code": "INVALID_AMOUNT",
      "message": "Amount must be a positive decimal."
    }
  ]
}
```

---

## 23.3 Import Recovery

```http
POST /api/v1/datasets/imports/{import_id}/recover
```

Accepts multipart form-data with the original `file` payload to resume a previously `FAILED` or interrupted import.

### RBAC Requirement
Requires role `ADMIN` or `ANALYST`.

### Recovery Guarantees
- Verifies uploaded file SHA-256 matches `import.file_hash`.
- Acquires transaction-scoped advisory lock on `(source_namespace, file_hash)`.
- Reconciles previously committed row ordinals via `SELECT source_row_number FROM transaction_import_records WHERE dataset_import_id = :id`.
- Processes only uncommitted rows, guaranteeing zero row duplication or gap skipping even across non-contiguous batch commits.
- Returns `HTTP 200 OK` with updated `DatasetImportResponse`.

---

# 24. Analytics API

Financial analytics provide deterministic server-computed intelligence directly over persisted transaction data. All analytics endpoints require Bearer JWT authentication and are accessible by users with roles: `ADMIN`, `ANALYST`, and `INVESTIGATOR`. All monetary amounts are formatted as two-decimal strings (`"0.00"`) via `ROUND_HALF_UP`.

The implemented endpoint inventory:
```text
GET /api/v1/analytics/overview
GET /api/v1/analytics/trends
GET /api/v1/analytics/categories
GET /api/v1/analytics/merchants
GET /api/v1/analytics/accounts/{account_id}
GET /api/v1/analytics/accounts/{account_id}/unusual-spending
```

---

# 25. Analytics Endpoint Specifications

## 25.1 Global Overview (`GET /api/v1/analytics/overview`)

Retrieves macro-aggregates across transactions for a given namespace and currency over a half-open window `[from_time, to_time)`.

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `source_namespace` | `string` | Query | No | `"SYNTHETIC"` | Target namespace pattern `^[A-Z0-9_]{3,64}$` |
| `namespace` | `string` | Query | No | `null` | Alias for `source_namespace` |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `from_time` | `datetime` | Query | No | `null` | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | No | `null` | End boundary (exclusive); must be `> from_time` |
| `timezone` | `string` | Query | No | `"UTC"` | Reporting timezone (informational) |

### Status Codes
- `200 OK`: Successful response.
- `401 Unauthorized`: Missing or invalid Bearer token.
- `403 Forbidden`: Authenticated user lacks required role.
- `404 Not Found`: Namespace does not exist (`NAMESPACE_NOT_FOUND`).
- `422 Unprocessable Entity`: Validation failure (syntax, range).

### Response Example (`OverviewAnalyticsResponse`)
```json
{
  "source_namespace": "SYNTHETIC",
  "currency": "INR",
  "from_time": "2026-02-01T00:00:00Z",
  "to_time": "2026-03-01T00:00:00Z",
  "total_transaction_count": 80651,
  "debit_transaction_count": 52400,
  "credit_transaction_count": 28251,
  "total_volume_amount": "24501230.50",
  "total_debit_amount": "14201200.00",
  "total_credit_amount": "10300030.50",
  "net_cash_flow": "-3901169.50",
  "average_transaction_amount": "303.79",
  "median_transaction_amount": "145.50",
  "debit_average_amount": "271.02",
  "debit_median_amount": "130.00",
  "credit_average_amount": "364.59",
  "credit_median_amount": "180.00",
  "min_transaction_amount": "5.00",
  "max_transaction_amount": "50000.00"
}
```

---

## 25.2 Periodic Trends (`GET /api/v1/analytics/trends`)

Retrieves contiguous, zero-filled financial trend buckets grouped by day or month in the client's specified IANA timezone over `[from_time, to_time)`.

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `from_time` | `datetime` | Query | Yes | — | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | Yes | — | End boundary (exclusive); must be `> from_time` |
| `source_namespace` | `string` | Query | No | `"SYNTHETIC"` | Namespace pattern `^[A-Z0-9_]{3,64}$` |
| `namespace` | `string` | Query | No | `null` | Alias for `source_namespace` |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `interval` | `string` | Query | No | `"day"` | `"day"` or `"month"` |
| `timezone` | `string` | Query | No | `"UTC"` | Valid IANA timezone or `"UTC"` |

### Bucket Count Limits
- `interval=day`: max 366 buckets (`MAX_DAILY_BUCKETS`). Exceeding returns HTTP 422 (`TREND_BUCKET_COUNT_EXCEEDS_LIMIT`).
- `interval=month`: max 120 buckets (`MAX_MONTHLY_BUCKETS`). Exceeding returns HTTP 422 (`TREND_BUCKET_COUNT_EXCEEDS_LIMIT`).

### Response Example (`TrendAnalyticsResponse`)
```json
{
  "source_namespace": "SYNTHETIC",
  "currency": "INR",
  "interval": "day",
  "timezone": "UTC",
  "from_time": "2026-02-01T00:00:00Z",
  "to_time": "2026-02-03T00:00:00Z",
  "total_buckets": 2,
  "buckets": [
    {
      "bucket_start": "2026-02-01T00:00:00Z",
      "transaction_count": 2740,
      "debit_count": 1810,
      "credit_count": 930,
      "total_debit_amount": "485200.00",
      "total_credit_amount": "392100.00",
      "net_cash_flow": "-93100.00"
    },
    {
      "bucket_start": "2026-02-02T00:00:00Z",
      "transaction_count": 2680,
      "debit_count": 1750,
      "credit_count": 930,
      "total_debit_amount": "472150.00",
      "total_credit_amount": "381000.00",
      "net_cash_flow": "-91150.00"
    }
  ]
}
```

---

## 25.3 Category Distribution (`GET /api/v1/analytics/categories`)

Aggregates spending or volume grouped by transaction category for a specified direction (`DEBIT` or `CREDIT`).

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `direction` | `string` | Query | No | `"DEBIT"` | `"DEBIT"` or `"CREDIT"` |
| `source_namespace` | `string` | Query | No | `"SYNTHETIC"` | Namespace pattern `^[A-Z0-9_]{3,64}$` |
| `namespace` | `string` | Query | No | `null` | Alias for `source_namespace` |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `from_time` | `datetime` | Query | No | `null` | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | No | `null` | End boundary (exclusive) |
| `timezone` | `string` | Query | No | `"UTC"` | Reporting timezone (informational) |

### Response Example (`CategoryAnalyticsResponse`)
```json
{
  "source_namespace": "SYNTHETIC",
  "currency": "INR",
  "direction": "DEBIT",
  "total_directional_amount": "14201200.00",
  "categories": [
    {
      "category_name": "GROCERY",
      "transaction_count": 15420,
      "total_amount": "4260360.00",
      "percentage_of_total": "30.00",
      "average_amount": "276.29"
    },
    {
      "category_name": "UNCATEGORIZED",
      "transaction_count": 412,
      "total_amount": "142012.00",
      "percentage_of_total": "1.00",
      "average_amount": "344.69"
    }
  ]
}
```

---

## 25.4 Merchant Analytics (`GET /api/v1/analytics/merchants`)

Ranks top merchants by debit volume (`amount`) or frequency (`count`) with dual percentage metrics.

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `sort_by` | `string` | Query | No | `"amount"` | `"amount"` or `"count"` |
| `limit` | `integer` | Query | No | `20` | `1 <= limit <= 100` |
| `offset` | `integer` | Query | No | `0` | `offset >= 0` |
| `source_namespace` | `string` | Query | No | `"SYNTHETIC"` | Namespace pattern `^[A-Z0-9_]{3,64}$` |
| `namespace` | `string` | Query | No | `null` | Alias for `source_namespace` |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `from_time` | `datetime` | Query | No | `null` | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | No | `null` | End boundary (exclusive) |
| `timezone` | `string` | Query | No | `"UTC"` | Reporting timezone (informational) |

### Response Example (`MerchantAnalyticsResponse`)
```json
{
  "source_namespace": "SYNTHETIC",
  "currency": "INR",
  "total_debit_amount": "14201200.00",
  "total_merchant_debit_amount": "12500000.00",
  "non_merchant_debit_amount": "1701200.00",
  "returned_merchant_count": 1,
  "merchants": [
    {
      "merchant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "merchant_name": "FreshMart Supermarket",
      "merchant_category": "GROCERY",
      "transaction_count": 3200,
      "total_amount": "1420120.00",
      "average_amount": "443.79",
      "percentage_of_total_debit": "10.00",
      "percentage_of_merchant_spend": "11.36"
    }
  ]
}
```

---

## 25.5 Account Activity (`GET /api/v1/analytics/accounts/{account_id}`)

Retrieves account financial summaries, temporal milestones, active days, top categories, and top merchants.

### Behavior & Authoritative Scoping
- **Authoritative Namespace:** Derives namespace from the persisted `Account.source_namespace`. Caller overrides are ignored.
- **Empty Currency (HTTP 200):** If the account exists but has no transactions in the requested currency, returns HTTP 200 with zeroed metrics and the complete list of `available_currencies` transacted by that account.
- **Account Not Found (HTTP 404):** Returns HTTP 404 (`RESOURCE_NOT_FOUND`) if `account_id` does not exist.

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `account_id` | `uuid` | Path | Yes | — | Valid account UUID |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `timezone` | `string` | Query | No | `"UTC"` | Valid IANA timezone |
| `from_time` | `datetime` | Query | No | `null` | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | No | `null` | End boundary (exclusive) |

### Response Example (`AccountActivityResponse`)
```json
{
  "account_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "external_account_id": "ACC_00001001",
  "source_namespace": "SYNTHETIC",
  "account_type": "SAVINGS",
  "status": "ACTIVE",
  "currency": "INR",
  "available_currencies": ["INR", "USD"],
  "first_transaction_at": "2026-01-15T10:30:00Z",
  "last_transaction_at": "2026-02-28T18:45:00Z",
  "active_days_count": 24,
  "summary": {
    "total_transaction_count": 52,
    "debit_transaction_count": 38,
    "credit_transaction_count": 14,
    "total_volume_amount": "45200.00",
    "total_debit_amount": "22100.00",
    "total_credit_amount": "23100.00",
    "net_cash_flow": "1000.00",
    "average_transaction_amount": "869.23",
    "median_transaction_amount": "450.00",
    "debit_average_amount": "581.58",
    "debit_median_amount": "320.00",
    "credit_average_amount": "1650.00",
    "credit_median_amount": "1200.00",
    "min_transaction_amount": "25.00",
    "max_transaction_amount": "8500.00"
  },
  "top_categories": [
    {
      "category_name": "GROCERY",
      "transaction_count": 18,
      "total_amount": "8200.00",
      "percentage_of_total": "37.10"
    }
  ],
  "top_merchants": [
    {
      "merchant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "merchant_name": "FreshMart Supermarket",
      "merchant_category": "GROCERY",
      "transaction_count": 12,
      "total_amount": "5400.00",
      "percentage_of_total_debit": "24.43",
      "percentage_of_merchant_spend": "38.57"
    }
  ]
}
```

---

## 25.6 Account Unusual Spending Outliers (`GET /api/v1/analytics/accounts/{account_id}/unusual-spending`)

Detects statistical outlier debit transactions exceeding an inclusive multiple of the account's historical debit median over the requested window.

### Mathematical Formulation
$$\text{threshold} = \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$$
A debit transaction is flagged if $\text{amount} \ge \text{threshold}$ (inclusive).

### Parameters
| Name | Type | In | Required | Default | Validation / Description |
|---|---|---|:---:|---|---|
| `account_id` | `uuid` | Path | Yes | — | Valid account UUID |
| `multiplier` | `decimal` | Query | No | `3.0` | `1.5 <= multiplier <= 10.0` |
| `threshold_multiplier` | `decimal` | Query | No | `null` | Alias for `multiplier` |
| `currency` | `string` | Query | No | `"INR"` | ISO-4217 3-letter currency code |
| `limit` | `integer` | Query | No | `50` | `1 <= limit <= 100` |
| `offset` | `integer` | Query | No | `0` | `offset >= 0` |
| `from_time` | `datetime` | Query | No | `null` | Start boundary (inclusive) |
| `to_time` | `datetime` | Query | No | `null` | End boundary (exclusive) |
| `timezone` | `string` | Query | No | `"UTC"` | Reporting timezone (informational) |

### Response Example (`UnusualSpendingResponse`)
```json
{
  "account_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "currency": "INR",
  "account_median_debit": "320.00",
  "multiplier": "3.0",
  "outlier_threshold_amount": "960.00",
  "unusual_transaction_count": 2,
  "returned_count": 2,
  "transactions": [
    {
      "transaction_id": "c1d2e3f4-a5b6-7890-1234-567890abcdef",
      "external_transaction_id": "TXN_00098124",
      "occurred_at": "2026-02-14T21:15:00Z",
      "amount": "4500.00",
      "currency": "INR",
      "transaction_type": "PURCHASE",
      "direction": "DEBIT",
      "category": "ELECTRONICS",
      "deviation_ratio": "14.06"
    },
    {
      "transaction_id": "e5f6a1b2-c3d4-5678-90ab-cdef12345678",
      "external_transaction_id": "TXN_00098412",
      "occurred_at": "2026-02-18T14:20:00Z",
      "amount": "1250.00",
      "currency": "INR",
      "transaction_type": "PURCHASE",
      "direction": "DEBIT",
      "category": "APPAREL",
      "deviation_ratio": "3.91"
    }
  ]
}
```

---

# 26. Risk API

## 26.1 Transaction Risk

```http
GET /api/v1/transactions/{transaction_id}/risk
```

Example:

```json
{
  "score": 91.4,
  "risk_level": "CRITICAL",
  "model_version": "transaction-anomaly-1.0.0",
  "factors": [
    {
      "code": "AMOUNT_ANOMALY",
      "severity": "HIGH",
      "description": "Amount is 7.8x the account's 30-day median."
    },
    {
      "code": "NEW_DEVICE",
      "severity": "HIGH",
      "description": "Device has not previously been associated with this account."
    }
  ]
}
```

---

# 27. Risk Reprocessing

Model reprocessing should be an explicit operation.

Potential endpoint:

```http
POST /api/v1/transactions/{transaction_id}/risk/analyze
```

This may be restricted to authorized users or internal service workflows.

The endpoint should never silently replace historical model results.

Each analysis is associated with a model version.

---

# 28. Investigation API

## 28.1 List Investigations

```http
GET /api/v1/investigations
```

Filters may include:

```text
status
priority
assigned_to
resolution
risk_level
created_from
created_to
```

---

## 28.2 Get Investigation

```http
GET /api/v1/investigations/{investigation_id}
```

The response should provide enough context for the investigation workspace.

Potential sections:

```text
case metadata
primary transaction
related transactions
risk result
risk factors
assignment
status
resolution
```

---

## 28.3 Create Investigation

```http
POST /api/v1/investigations
```

Request:

```json
{
  "transaction_id": "uuid",
  "priority": "HIGH"
}
```

The server should:

1. validate the transaction
2. create the investigation
3. create the primary transaction relationship
4. record the relevant audit event

These operations should occur transactionally.

---

# 29. Investigation Assignment

```http
PATCH /api/v1/investigations/{investigation_id}
```

Example:

```json
{
  "assigned_to": "uuid"
}
```

Authorization must verify that the acting user is allowed to assign cases.

---

# 30. Investigation Status

Allowed transitions should be explicit.

Example:

```text
OPEN
  ↓
UNDER_REVIEW
  ↓
RESOLVED
```

Invalid transitions should return:

```text
409 Conflict
```

rather than silently changing the case.

---

# 31. Investigation Resolution

Example:

```http
PATCH /api/v1/investigations/{investigation_id}
```

Request:

```json
{
  "resolution": "LEGITIMATE",
  "resolution_notes": "Verified as annual insurance payment."
}
```

Valid resolutions:

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

A resolved investigation should generally require a resolution.

---

# 32. Related Transactions

```http
GET /api/v1/investigations/{investigation_id}/transactions
```

This endpoint returns:

- primary transaction
- related transactions
- relationship type

Example:

```json
{
  "items": [
    {
      "transaction_id": "uuid",
      "relationship_type": "PRIMARY"
    },
    {
      "transaction_id": "uuid",
      "relationship_type": "RELATED"
    }
  ]
}
```

---

# 33. Evidence API

## 33.1 List Evidence

```http
GET /api/v1/investigations/{investigation_id}/evidence
```

---

## 33.2 Add Evidence

```http
POST /api/v1/investigations/{investigation_id}/evidence
```

Example:

```json
{
  "evidence_type": "BEHAVIOR_DEVIATION",
  "title": "Unusual transaction amount",
  "description": "Amount is significantly above the account baseline.",
  "payload": {
    "current_amount": "75000.00",
    "baseline_median": "2100.00"
  }
}
```

Evidence should be traceable and should not be silently overwritten.

---

# 34. Evidence Immutability

Investigation evidence is strictly append-only and immutable after creation.

There are no `PUT` or `PATCH` endpoints for evidence records:
```text
PUT   /api/v1/investigations/{id}/evidence/{evidence_id}  -> Not Implemented / 405 Method Not Allowed
PATCH /api/v1/investigations/{id}/evidence/{evidence_id}  -> Not Implemented / 405 Method Not Allowed
```

If an evidence interpretation changes or an investigator adds new observations, create a new evidence record (`POST /api/v1/investigations/{id}/evidence`) rather than mutating existing historical evidence.

This preserves investigative audit integrity and prevents evidence tampering.

---

# 35. AI Summary API

## 35.1 Generate Summary

```http
POST /api/v1/investigations/{investigation_id}/ai-summary
```

Possible response:

```json
{
  "id": "uuid",
  "status": "PENDING"
}
```

If generation is synchronous for the MVP, the API may return the completed summary directly.

If asynchronous:

```text
202 Accepted
```

should be used.

---

## 35.2 Get Summary

```http
GET /api/v1/investigations/{investigation_id}/ai-summary
```

Example:

```json
{
  "id": "uuid",
  "provider": "provider-name",
  "model": "model-name",
  "status": "COMPLETED",
  "summary": "The transaction shows several deviations..."
}
```

The response should clearly distinguish:

```text
AI-generated content
```

from:

```text
verified evidence
```

---

# 36. AI Safety in API Contracts

AI endpoints must not expose an API contract implying that the model decides:

```text
fraud = true
```

Preferred outputs:

```text
summary
key_observations
uncertainties
supporting_evidence
```

The final investigation resolution remains a human-controlled field.

---

# 37. Account API

## 37.1 List Accounts

```http
GET /api/v1/accounts
```

Supported filters may include:

```text
account_type
status
home_location
```

---

## 37.2 Account Details

```http
GET /api/v1/accounts/{account_id}
```

Potential response sections:

```text
account metadata
transaction summary
behavioral summary
risk summary
recent transactions
```

The API should avoid returning unnecessary sensitive customer data.

---

# 38. Account Behavioral Summary

Potential endpoint:

```http
GET /api/v1/accounts/{account_id}/behavior
```

Possible response:

```json
{
  "average_transaction_amount": "1850.00",
  "median_transaction_amount": "1200.00",
  "transactions_last_30_days": 84,
  "preferred_categories": [
    "FOOD",
    "GROCERIES"
  ],
  "known_device_count": 2,
  "known_location_count": 3
}
```

These values must be calculated server-side.

---

# 39. Merchant API

```http
GET /api/v1/merchants
GET /api/v1/merchants/{merchant_id}
GET /api/v1/merchants/{merchant_id}/transactions
```

Merchant analytics may include:

```text
transaction count
total volume
average transaction amount
category
location
risk-related activity
```

---

# 40. Device API

```http
GET /api/v1/devices
GET /api/v1/devices/{device_id}
GET /api/v1/devices/{device_id}/accounts
GET /api/v1/devices/{device_id}/transactions
```

Access may be restricted because device relationships can reveal investigative information.

---

# 41. Health Endpoints

The backend exposes health and readiness checks at both root and versioned API paths:

```http
GET /health
GET /ready
GET /api/v1/health
GET /api/v1/ready
```

Responses also include `X-Request-ID` (or configured correlation header) and `X-Process-Time` headers.

### `/health` and `/api/v1/health`

Answers:

```text
Is the process running?
```

Returns HTTP 200 `{"status": "healthy"}` independently of downstream database availability.

### `/ready` and `/api/v1/ready`

Answers:

```text
Can the service accept requests?
```

Readiness verifies dependencies such as PostgreSQL. Returns HTTP 200 `{"status": "ready", "database": "connected"}` when connected, and HTTP 503 `{"status": "unhealthy", "database": "disconnected"}` when unreachable.

Health endpoints should not expose secrets or detailed infrastructure information.

---

# 42. Error Response Format

Errors should follow a consistent structure.

Example:

```json
{
  "error": {
    "code": "INVESTIGATION_STATE_CONFLICT",
    "message": "The investigation cannot be resolved from its current state.",
    "details": {
      "current_status": "OPEN"
    },
    "request_id": "request-id"
  }
}
```

---

# 43. Error Codes

Error codes should be stable machine-readable identifiers.

Examples:

```text
INVALID_CREDENTIALS
ACCOUNT_NOT_FOUND
TRANSACTION_NOT_FOUND
INVESTIGATION_NOT_FOUND
INVESTIGATION_STATE_CONFLICT
INVALID_TRANSACTION
DATASET_IMPORT_FAILED
MODEL_NOT_AVAILABLE
AI_SUMMARY_FAILED
FORBIDDEN_OPERATION
```

Human-readable messages may change without breaking clients.

The error code should remain stable.

---

# 44. Validation Errors

Validation failures should identify the affected field.

Example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "amount": [
        "Amount must be greater than zero."
      ],
      "currency": [
        "Currency must contain exactly three characters."
      ]
    }
  }
}
```

---

# 45. Request IDs

Every API request should have a request/correlation ID.

Default header:

```text
X-Request-ID
```

The correlation header name is configurable via application settings (`Settings.request_id_header`).

Client-supplied IDs are validated against `^[a-zA-Z0-9_-]{1,64}$`. If valid, the ID is preserved as a correlation hint; otherwise a 32-character hex UUID4 is generated. Client IDs are never treated as an authentication or authorization signal.

Authoritative request ID and `X-Process-Time` (in milliseconds) headers are attached to responses. Pre-existing duplicate instances of these headers are stripped.

The ID should appear in logs and error responses.

This is especially important for:

- ingestion failures
- ML failures
- AI failures
- investigation operations

---

# 46. HTTP Request Idempotency

Idempotency headers protect against duplicate API operations caused by network retries.

Dataset import creation and other potentially state-modifying `POST` operations support the standard header:

```http
Idempotency-Key: <client-generated-uuid-or-key>
```

### Scope Boundary
`Idempotency-Key` operates strictly at the HTTP transport layer to ensure a retried HTTP request returns the cached response rather than executing a duplicate server operation. It is completely distinct from:
1. **Dataset file deduplication** (detecting byte-identical files via `dataset_imports.file_hash`).
2. **Canonical transaction identity** (resolving identical financial events across imports via natural keys).
3. **Import-row provenance** (recording row-level observation history in `transaction_import_records`).

---

# 47. Transaction Identity, Lineage & Ingestion Idempotency

Bulk and standalone ingestion must preserve canonical financial facts, track row-level provenance, and prevent duplicate or conflicting records across imports.

### 47.1 Canonical Transaction Identity
A canonical transaction is uniquely identified across all imports and APIs by:
```text
(source_namespace, account_id, external_transaction_id)
```
- **Namespace:** Identifies the origin system or generator contract (default: `'SYNTHETIC'`). Non-synthetic imports must supply an explicit namespace; a default must never silently misclassify external feeds.
- **Account Resolution (ADR-065 Decision D):** Incoming source account identifiers are resolved deterministically using `(source_namespace, external_account_id)`. Missing or ambiguous account references cause immediate row rejection (`ACCOUNT_NOT_FOUND` or `AMBIGUOUS_ACCOUNT_REFERENCE`); the ingestion service must never arbitrarily select an account.
- **Namespace Consistency:** The transaction's `source_namespace` must strictly agree with the referenced account's `source_namespace`.
- **External Transaction ID:** The source-assigned identifier, guaranteed unique per account within the source namespace.

### 47.2 Material Equivalence vs Conflict Quarantine
When an incoming row matches an existing `(source_namespace, account_id, external_transaction_id)`:
1. **Normalization:** Timestamps are normalized to UTC `TIMESTAMPTZ`, string fields trimmed, monetary amounts parsed as exact `Decimal(18,2)`, and codes uppercased.
2. **Equivalent Row:** If all material attributes (`account_id`, `amount`, `currency`, `occurred_at`, `transaction_type`, `direction`, `counterparty_account_id`) match the canonical transaction, the existing canonical record is reused. The observation is recorded in `transaction_import_records` with outcome `MATCHED_EXISTING` (or `DUPLICATE_IN_IMPORT` if repeated within the same file). The canonical transaction is **never overwritten**.
3. **Contextual Metadata Divergence:** Per ADR-065 Decision A, if all seven core material attributes match the canonical transaction, but one or more contextual fields differ (`merchant_id`, `device_id`, `location_id`, `category`, `payment_method`, `channel`), the canonical record is preserved strictly unchanged in `transactions`. The incoming row is recorded in `transaction_import_records` with outcome `MATCHED_EXISTING` and `row_hash` computed over the complete normalized 15-key payload. It does **not** trigger `MATERIAL_CONFLICT` or `QUARANTINED`. Alternate contextual plaintext is not retained in relational storage and cannot be reconstructed from `row_hash`.
4. **Material Conflict:** If any of the seven core material attributes differ, the canonical transaction row is preserved strictly unchanged. The incoming row is quarantined with outcome `QUARANTINED` in `transaction_import_records` (with `transaction_id = NULL`), and a row-level error is recorded in `dataset_import_errors` with persisted `error_code = 'MATERIAL_CONFLICT'`. (When exposed via direct synchronous transactional endpoints, this condition maps to the public API error code `TRANSACTION_IDENTITY_CONFLICT` with HTTP 409 Conflict). Conflicting data is **never silently applied or overwritten**.

### 47.3 Repeated File Upload & Concurrency Policy
When a file payload is uploaded to a specified `source_namespace` (verified via SHA-256 `file_hash`):

1. **Namespace-Scoped Deduplication Scope:** Deduplication is strictly scoped to `(source_namespace, file_hash)`. Uploading identical file bytes under different source namespaces (e.g., initial upload under `SYNTHETIC` versus subsequent upload under `PUBLIC_DATASET_A`) represents distinct import identities that are ingested independently into their respective namespaces. Deduplication must never be global on `file_hash` alone.

2. **Transaction-Scoped Advisory Lock:** Storing `file_hash` alone and relying solely on a partial unique index on active statuses (`PENDING`, `PROCESSING`) cannot prevent duplicate imports if Request A completes quickly and transitions to `COMPLETED` before Request B attempts its insertion. To eliminate all read-then-insert race conditions, the ingestion registration endpoint opens a database transaction and immediately acquires a transaction-scoped PostgreSQL advisory lock.
   - *Application Key Derivation (Python):* The 64-bit signed integer key is computed in Python by hashing `(source_namespace || ':' || file_hash)` via SHA-256 and taking the first 8 bytes as a signed big-endian integer:
     ```python
     key_bytes = hashlib.sha256(f"{source_namespace}:{file_hash}".encode("utf-8")).digest()[:8]
     lock_key = int.from_bytes(key_bytes, byteorder="big", signed=True)
     ```
     Acquired via: `SELECT pg_advisory_xact_lock(:lock_key);`.
   - *Pure SQL Alternative (PostgreSQL 16+):*
     ```sql
     SELECT pg_advisory_xact_lock(('x' || substring(encode(sha256((:source_namespace || ':' || :file_hash)::bytea), 'hex') FROM 1 FOR 16))::bit(64)::bigint);
     ```
   - *Collision Semantics:* A 64-bit advisory lock key space has negligible collision probability. If two distinct uploads produce a hash collision, it causes a brief serial queuing delay; correctness is strictly guaranteed by the query `WHERE source_namespace = :source_namespace AND file_hash = :file_hash` and the partial unique index `uq_dataset_imports_active_hash`.
   - This lock is acquired *before* querying existing imports and held continuously through lookup and creation of a new `dataset_imports` record within the same transaction. Uploads targeting different namespaces do not serialize.

3. **Completed vs. Failed Precedence & Perpetual Retention:**
   - **Applicable Completed Import Takes Precedence (Perpetual Deduplication):** If any existing import with matching `(source_namespace, file_hash)` has status `COMPLETED`, it takes precedence indefinitely (per ADR-065). The API commits the transaction (releasing the lock) and returns `HTTP 200 OK` with the existing completed import summary rather than executing redundant parsing or generating duplicate rows.
   - **Administrative Reprocessing Safeguards:** An explicit reprocessing workflow cannot bypass advisory locking, active import conflict behavior (`HTTP 409`), canonical transaction uniqueness, or the row-level recovery contract. Any future reprocessing request must be restricted to `ADMIN`, explicitly audited in `audit_events`, and create a new import attempt record. The exact API parameter or command shape remains unspecified until its request/response and authorization contract is formally designed; undocumented bypass flags are strictly forbidden.
   - **Active In-Progress Import:** If an existing import has status `PENDING` or `PROCESSING` within the target namespace, the API returns `HTTP 409 Conflict` with machine-readable error code `IMPORT_IN_PROGRESS`, preventing concurrent ingestion of identical files in the same namespace.
   - **Failed Import Retry:** A new import attempt (`dataset_imports` row with status `PENDING`) is permitted **only when no applicable completed import exists** in that namespace and the documented retry policy allows it (e.g. prior attempts reached terminal status `FAILED`). The previous failed record is preserved for audit lineage.

4. **Lock Timeout & Failure Behavior:** Lock acquisition is bounded by `SET LOCAL lock_timeout = '5s'`. If the lock cannot be acquired or an error occurs during lookup/insert, the transaction immediately rolls back and releases the lock. An unsuccessful registration is **never** reported as successful; the endpoint returns a transient failure (e.g. `HTTP 503 Service Unavailable` or `HTTP 408 Request Timeout`).

5. **Secondary Partial Unique Index Safeguard:** As a secondary defense-in-depth database constraint, `uq_dataset_imports_active_hash` on `dataset_imports(source_namespace, file_hash) WHERE status IN ('PENDING', 'PROCESSING')` prevents concurrent active rows even if application locking is bypassed.

6. **Nullable Hash Handling:** If an upload does not supply or compute a `file_hash` (`NULL`), advisory locking and file lookup are bypassed, allowing unhashed uploads without constraint.

7. **Intentional Re-analysis:** Re-evaluating previously imported transactions against newer ML models or rules must use explicit re-analysis endpoints (e.g. `POST /api/v1/transactions/{id}/risk/analyze`), never re-uploading duplicate raw files.

### 47.4 Idempotent Import Recovery
If an import fails midway, resuming that import attempt must use row-level idempotent tracking against `transaction_import_records`. The recovery engine does not assume contiguous row completion (`MAX + 1`); it queries unvisited or failed row ordinals within that `dataset_import_id` and safely reprocesses them without skipping or duplicating data. Duplicate and quarantined rows remain fully traceable via `dataset_import_id`, `source_row_number`, and `row_hash` in `transaction_import_records` even when `transaction_id` is null.

---

# 48. Concurrency

Concurrent updates to investigations must be handled explicitly.

Possible approach:

```text
If-Match
```

or an application-managed version field.

A stale update should return:

```text
409 Conflict
```

rather than silently overwriting another investigator's change.

---

# 49. Immutability Rules

The following should generally be immutable after creation:

```text
transactions
risk analyses
risk factors
investigation_evidence (append-only; mutation/updates rejected)
audit events
historical evidence snapshots
```

Mutable workflow objects include:

```text
investigations
user assignments
investigation status
investigation resolution
```

Even mutable changes should be auditable where appropriate.

---

# 50. API and Database Separation

The API should not expose database tables directly.

For example:

```text
database:
risk_analyses
risk_factors
```

does not require:

```text
GET /risk_analyses
GET /risk_factors
```

as raw CRUD endpoints.

The API should expose domain-oriented representations.

---

# 51. DTO / Schema Separation

FastAPI/Pydantic schemas should be separated from persistence models.

Conceptually:

```text
SQLAlchemy model
        |
        v
Service/domain logic
        |
        v
Pydantic response schema
```

Do not expose ORM entities directly as public API contracts.

This reduces accidental coupling between database changes and API clients.

---

# 52. API Versioning Strategy

The initial version:

```text
v1
```

Breaking changes require:

```text
v2
```

Non-breaking changes may include:

- optional response fields
- new endpoints
- new optional query parameters

Breaking changes include:

- removing fields
- changing field meanings
- changing data types
- changing required request fields
- changing endpoint semantics

---

# 53. OpenAPI Documentation

All public endpoints must have:

- summary
- description
- request schema
- response schema
- authentication requirements
- possible error responses

Examples should be included for important workflows.

The OpenAPI schema becomes a contract between:

```text
FastAPI backend
        |
        v
React frontend
```

---

# 54. API Security

The API must implement:

- JWT authentication
- RBAC
- request validation
- upload restrictions
- rate limiting where appropriate
- safe error messages
- secure password handling
- CORS configuration
- no secret leakage
- audit logging for important actions

Detailed controls are defined in `SECURITY.md`.

---

# 55. File Upload Security

Dataset uploads are untrusted input.

The API should enforce:

```text
maximum file size
allowed extension
allowed MIME type
CSV structure validation
encoding validation
row limits
processing timeout
```

Uploaded filenames must not be used directly to construct filesystem paths.

Temporary files should be safely isolated and removed after processing when no longer required.

---

# 56. Query Performance

API endpoints must avoid unbounded queries.

For example, this should not be allowed:

```http
GET /transactions
```

to return hundreds of thousands of rows.

Use:

```text
pagination
filters
date ranges
limits
```

The database indexing strategy is defined in `DATABASE_DESIGN.md`.

---

# 57. N+1 Query Prevention

List endpoints should avoid executing one database query per returned record.

Examples:

```text
transactions + merchants
investigations + assignments
risk analyses + risk factors
```

should use appropriate eager loading, joins, or batched queries.

The API response structure should not dictate inefficient database access.

---

# 58. Analytics Query Boundaries

Analytics endpoints may execute more expensive queries than standard CRUD endpoints.

However:

- date ranges should be bounded
- pagination should be used where appropriate
- expensive aggregations should be measured
- materialized views should not be introduced without evidence

---

# 59. ML API Boundaries

The API should expose ML capabilities through domain endpoints rather than raw model internals.

Preferred:

```text
GET /transactions/{id}/risk
POST /transactions/{id}/risk/analyze
```

Avoid exposing:

```text
POST /models/isolation-forest/predict
```

to normal application clients.

The latter leaks implementation details.

---

# 60. AI API Boundaries

Similarly, the API should expose:

```text
POST /investigations/{id}/ai-summary
```

rather than:

```text
POST /llm/generate
```

The application controls the context sent to the AI provider.

Clients should not directly provide arbitrary prompts to the production investigation-summary endpoint.

---

# 61. API Transaction Boundaries

Important multi-step operations should execute atomically.

Example investigation creation:

```text
validate transaction
       ↓
create investigation
       ↓
create primary relationship
       ↓
create audit event
       ↓
commit
```

If any required step fails, the transaction should roll back.

---

# 62. Asynchronous Operations

The MVP may use synchronous processing where workloads are small enough.

Asynchronous processing should be introduced for operations such as:

- large CSV ingestion
- large batch risk analysis
- AI summary generation if latency is significant

The API should return:

```text
202 Accepted
```

and expose a status endpoint.

Celery/Redis are deferred until actual workload requires them.

---

# 63. Rate Limiting

Rate limits should be considered for:

```text
login
registration
AI summary generation
dataset imports
expensive analytics
```

The exact mechanism may be introduced during security implementation.

Rate limits should not interfere with normal investigator workflows.

---

# 64. CORS

CORS should allow only configured frontend origins.

Development may use:

```text
http://localhost:<frontend-port>
```

Production must use the deployed frontend origin.

Wildcard production CORS should not be used for authenticated APIs.

---

# 65. Environment Configuration

API behavior requiring deployment-specific values must use configuration.

Examples:

```text
DATABASE_URL
JWT_SECRET
JWT_EXPIRATION
CORS_ORIGINS
MAX_UPLOAD_SIZE
LLM_PROVIDER
LLM_MODEL
```

Secrets must never be hard-coded into source code.

---

# 66. Logging

API logs should include:

```text
timestamp
request_id
method
path
status_code
duration
authenticated user ID where appropriate
```

Logs must not include:

```text
passwords
JWT tokens
database passwords
API keys
unnecessary sensitive financial details
```

---

# 67. API Observability

Important metrics include:

```text
request count
latency
error rate
authentication failures
dataset import failures
risk-analysis failures
AI-summary failures
```

The initial implementation may rely on structured application logging before introducing a full observability platform.

---

# 68. Frontend Integration Principles

The React frontend should treat the API as authoritative.

The frontend must not independently calculate:

```text
risk scores
account balances
fraud probability
financial totals
behavioral feature values
```

The backend returns the authoritative values.

Frontend state management and caching may use TanStack Query or an equivalent mechanism.

---

# 69. API Contract Testing

The project should validate that:

```text
request schema
response schema
status codes
error formats
```

remain consistent.

FastAPI's OpenAPI schema should be used as part of integration testing where practical.

---

# 70. Recommended Endpoint Summary

### Authentication

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
POST   /api/v1/auth/logout
```

### Accounts

```text
GET    /api/v1/accounts
GET    /api/v1/accounts/{account_id}
GET    /api/v1/accounts/{account_id}/behavior
```

### Transactions

```text
GET    /api/v1/transactions
GET    /api/v1/transactions/{transaction_id}
POST   /api/v1/transactions
GET    /api/v1/transactions/{transaction_id}/risk
POST   /api/v1/transactions/{transaction_id}/risk/analyze
```

### Dataset Imports

```text
POST   /api/v1/datasets/imports
GET    /api/v1/datasets/imports/{import_id}
POST   /api/v1/datasets/imports/{import_id}/recover
```

### Analytics

```text
GET    /api/v1/analytics/overview
GET    /api/v1/analytics/trends
GET    /api/v1/analytics/categories
GET    /api/v1/analytics/merchants
GET    /api/v1/analytics/accounts/{account_id}
GET    /api/v1/analytics/accounts/{account_id}/unusual-spending
```

### Merchants

```text
GET    /api/v1/merchants
GET    /api/v1/merchants/{merchant_id}
GET    /api/v1/merchants/{merchant_id}/transactions
```

### Devices

```text
GET    /api/v1/devices
GET    /api/v1/devices/{device_id}
GET    /api/v1/devices/{device_id}/accounts
GET    /api/v1/devices/{device_id}/transactions
```

### Investigations

```text
GET    /api/v1/investigations
POST   /api/v1/investigations
GET    /api/v1/investigations/{investigation_id}
PATCH  /api/v1/investigations/{investigation_id}
GET    /api/v1/investigations/{investigation_id}/transactions
GET    /api/v1/investigations/{investigation_id}/evidence
POST   /api/v1/investigations/{investigation_id}/evidence
POST   /api/v1/investigations/{investigation_id}/ai-summary
GET    /api/v1/investigations/{investigation_id}/ai-summary
```

### System

```text
GET    /health
GET    /ready
GET    /api/v1/health
GET    /api/v1/ready
```

This list is the initial API surface, not a requirement to implement every endpoint simultaneously.

---

# 71. API Implementation Order

Recommended implementation sequence:

```text
1. API foundation
       ↓
2. Authentication
       ↓
3. Users / RBAC
       ↓
4. Accounts / reference entities
       ↓
5. Transactions
       ↓
6. Dataset ingestion
       ↓
7. Analytics
       ↓
8. Risk analysis
       ↓
9. Investigations
       ↓
10. Evidence
       ↓
11. AI summaries
       ↓
12. Audit and observability
```

This follows the dependency structure of the platform.

---

# 72. API Acceptance Criteria

The API design is considered complete when:

- [ ] API uses `/api/v1`.
- [ ] Authentication endpoints are defined.
- [ ] RBAC requirements are defined.
- [ ] Resource naming is consistent.
- [ ] HTTP methods and status codes are defined.
- [ ] Pagination is defined.
- [ ] Filtering and sorting are defined.
- [ ] Error responses use stable error codes.
- [ ] Monetary values avoid floating-point ambiguity.
- [ ] Transaction endpoints are defined.
- [ ] Dataset ingestion endpoints are defined.
- [ ] Analytics endpoints are defined.
- [ ] Risk-analysis endpoints are defined.
- [ ] Investigation lifecycle endpoints are defined.
- [ ] Evidence endpoints are defined.
- [ ] AI-summary endpoints are defined.
- [ ] Request IDs are supported.
- [ ] Important operations have idempotency considerations.
- [ ] Concurrency conflicts are explicitly handled.
- [ ] File upload security requirements are defined.
- [ ] API/database separation is maintained.
- [ ] OpenAPI documentation is generated.
- [ ] ML and AI implementation details are not unnecessarily exposed.
- [ ] Frontend receives server-authoritative financial and analytical values.

---

# 73. Open API Decisions

The following decisions should be finalized during implementation:

1. Exact JWT expiration time.
2. Logout/revocation strategy.
3. Refresh-token usage.
4. Exact RBAC matrix.
5. Default and maximum pagination size.
6. Cursor pagination requirements.
7. Exact idempotency implementation.
8. Optimistic concurrency mechanism.
9. Async job infrastructure.
10. Exact analytics endpoint response shapes.
11. Exact AI-summary response structure.
12. API rate limits.
13. Production OpenAPI exposure.
14. API request/response naming conventions for nested resources.

Final decisions should be recorded in `DECISIONS.md`.

---

# 74. Relationship to Other Documents

| Document | Relationship |
|---|---|
| `PRD.md` | Defines product capabilities exposed through the API |
| `DATASET_SPECIFICATION.md` | Defines imported transaction data |
| `TRD.md` | Defines API technology and implementation constraints |
| `ARCHITECTURE.md` | Defines service/module boundaries |
| `DATABASE_DESIGN.md` | Defines persistence structures represented by the API |
| `ML_DESIGN.md` | Defines risk and intelligence capabilities exposed through API endpoints |
| `SECURITY.md` | Defines authentication, authorization, and security controls |
| `CODING_STANDARDS.md` | Defines API implementation conventions |
| `TESTING_STRATEGY.md` | Defines API testing requirements |
| `PROJECT_ROADMAP.md` | Defines implementation sequencing |
| `DECISIONS.md` | Records finalized API decisions |

---

# 75. Final API Principle

The FinSignal API should provide a stable bridge between:

```text
Frontend
   |
   v
Application/API Layer
   |
   +---- Financial Data
   +---- Analytics
   +---- Risk Intelligence
   +---- Investigations
   +---- Evidence
   +---- AI Summaries
   |
   v
Persistence / Intelligence Layers
```

The API must preserve a clear distinction between:

```text
financial facts
      ↓
derived intelligence
      ↓
investigative evidence
      ↓
AI interpretation
      ↓
human decision
```

The final principle is:

> **Expose authoritative facts and structured intelligence through stable contracts, while keeping business rules, ML internals, database details, and AI provider implementation behind the API boundary.**
