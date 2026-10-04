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

The endpoint accepts the supported dataset file format, initially:

```text
CSV
```

The API should validate:

- file type
- file size
- required columns
- row structure
- encoding
- field types

---

## 23.2 Import Response

Large imports may be asynchronous.

Example:

```json
{
  "id": "uuid",
  "status": "PROCESSING",
  "filename": "transactions.csv",
  "total_rows": 250000,
  "valid_rows": 0,
  "invalid_rows": 0
}
```

HTTP status:

```text
202 Accepted
```

when processing continues after the request.

---

## 23.3 Import Status

```http
GET /api/v1/datasets/imports/{import_id}
```

Response:

```json
{
  "id": "uuid",
  "status": "COMPLETED",
  "total_rows": 250000,
  "valid_rows": 249700,
  "invalid_rows": 300
}
```

---

## 23.4 Import Errors

```http
GET /api/v1/datasets/imports/{import_id}/errors
```

This endpoint is paginated.

Example:

```json
{
  "items": [
    {
      "row_number": 1482,
      "field_name": "amount",
      "error_code": "INVALID_AMOUNT",
      "message": "Amount must be greater than zero."
    }
  ]
}
```

Sensitive raw field values should not be returned unless explicitly required.

---

# 24. Analytics API

Financial analytics are distinct from ML risk analysis.

Potential endpoints:

```text
GET /api/v1/analytics/overview
GET /api/v1/analytics/transactions/trends
GET /api/v1/analytics/spending/categories
GET /api/v1/analytics/merchants
GET /api/v1/analytics/accounts/{account_id}
```

Analytics responses should contain server-computed values.

The frontend must not independently recreate financial calculations.

---

# 25. Analytics Overview

Example:

```http
GET /api/v1/analytics/overview?from=...&to=...
```

Possible response:

```json
{
  "transaction_count": 125000,
  "total_debit": "45000000.00",
  "total_credit": "52000000.00",
  "flagged_transaction_count": 842,
  "open_investigation_count": 137
}
```

The exact metrics depend on the final product dashboard.

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

The backend should expose:

```http
GET /health
GET /ready
```

### `/health`

Answers:

```text
Is the process running?
```

### `/ready`

Answers:

```text
Can the service accept requests?
```

Readiness may verify dependencies such as PostgreSQL.

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

Example header:

```text
X-Request-ID
```

If the client provides a valid ID, the server may preserve it.

Otherwise the server generates one.

The ID should appear in logs and error responses.

This is especially important for:

- ingestion failures
- ML failures
- AI failures
- investigation operations

---

# 46. Idempotency

Idempotency is important for operations that may be retried.

Dataset import creation and other potentially expensive POST operations may support:

```text
Idempotency-Key
```

Example:

```http
Idempotency-Key: 2c7d...
```

The exact idempotency mechanism will be implemented only where retry duplication is a realistic risk.

---

# 47. Transaction Idempotency

Bulk imports must avoid duplicate transactions.

Recommended logical uniqueness:

```text
(dataset_import_id, external_transaction_id)
```

or an equivalent source-system identity strategy.

The ingestion layer must define how duplicate files and repeated uploads are handled.

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
GET    /api/v1/datasets/imports
GET    /api/v1/datasets/imports/{import_id}
GET    /api/v1/datasets/imports/{import_id}/errors
```

### Analytics

```text
GET    /api/v1/analytics/overview
GET    /api/v1/analytics/transactions/trends
GET    /api/v1/analytics/spending/categories
GET    /api/v1/analytics/merchants
GET    /api/v1/analytics/accounts/{account_id}
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
