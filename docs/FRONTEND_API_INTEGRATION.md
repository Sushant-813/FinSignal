# FinSignal — Frontend API Integration Document

**Document:** `FRONTEND_API_INTEGRATION.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.0  
**Status:** Draft for contract verification  
**Scope:** Integration between the browser frontend and FastAPI `/api/v1` API  
**Prerequisites:** `FRONTEND_PRD.md`, `FRONTEND_TRD.md`, `FRONTEND_ARCHITECTURE.md`

---

## 1. Purpose

This document defines how the FinSignal frontend integrates with the backend REST API. It records the documented endpoints, request patterns, response handling, pagination, filters, authentication headers, error behavior, and feature-level integration requirements.

The primary source for endpoint definitions in this document is the project's `API_GUIDELINES.md`. That document describes the intended API contract, but it is not automatically proof that every route and schema in the running backend matches the documentation.

**Contract rule:** before implementing an API operation, verify its route, method, request model, response model, status codes, and security requirements against the running backend's `/openapi.json` and implementation. Where the documentation is incomplete or contradictory, record the gap instead of inventing a contract.

## 2. Integration Principles

1. The backend API is the source of truth for financial and domain data.
2. All application API routes use the versioned `/api/v1` prefix.
3. All protected requests use the approved authentication/session adapter.
4. API calls are centralized; page components must not construct arbitrary URLs.
5. Generated TypeScript types should come from the verified OpenAPI schema.
6. Frontend validation improves usability; backend validation is authoritative.
7. The frontend must preserve server pagination, filtering, ordering, and status semantics.
8. Monetary values must preserve decimal-safe representations.
9. Mutations must handle authorization, validation, conflict, and concurrency failures.
10. The frontend must not infer endpoint behavior from a similar endpoint or a product requirement.

## 3. API Base URL and Environment

### 3.1 Base path

The documented API prefix is:

```text
/api/v1
```

Examples:

```text
/api/v1/auth/login
/api/v1/transactions
/api/v1/investigations
```

### 3.2 Configuration

Suggested public Vite configuration:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Rules:

- Keep the API origin configurable by environment.
- Do not hard-code hostnames in feature modules.
- Do not put secrets in `VITE_` variables; Vite exposes these values to browser code.
- Ensure the configured base URL includes the version prefix exactly once.
- Production must use HTTPS.
- Backend CORS must explicitly allow the deployed frontend origin.

### 3.3 Local development

Choose and document one of the following:

- Vite development proxy to the local backend, or
- Direct requests to a configured backend origin with backend CORS configured.

Do not configure both approaches inconsistently. The selected setup must work with the authentication strategy finalized in `FRONTEND_SECURITY.md`.

## 4. Authentication Integration

### 4.1 Documented endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate credentials |
| GET | `/auth/me` | Retrieve current user |
| POST | `/auth/logout` | Documented in endpoint summary; semantics require verification |

### 4.2 Login

**Request**

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "analyst@example.com",
  "password": "secure-password"
}
```

**Documented response**

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

The `expires_in` value in the example is illustrative. The frontend must use the actual returned value and the backend's configured token policy.

### 4.3 Current user

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

Documented response:

```json
{
  "id": "uuid",
  "email": "analyst@example.com",
  "role": "ANALYST",
  "is_active": true
}
```

Use this endpoint as the current identity context after session establishment. Do not rely only on locally decoded JWT claims for role-aware presentation.

### 4.4 Registration

The API guidelines document:

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "email": "analyst@example.com",
  "password": "secure-password"
}
```

Documented response:

```json
{
  "id": "uuid",
  "email": "analyst@example.com",
  "role": "ANALYST"
}
```

The product decision to expose public registration versus administratively provisioned accounts remains open. Do not expose a registration page until that policy is approved.

### 4.5 Logout and token lifecycle

The API guidelines explicitly state that JWT access tokens are stateless by default and list three possible strategies:

- Short-lived access token with client-side removal.
- Server-side token revocation.
- Refresh-token architecture.

The frontend must not claim that calling logout invalidates a token unless the backend implements revocation. The exact `/auth/logout` request/response behavior and token/session storage are unresolved and must be finalized in `FRONTEND_SECURITY.md` and `DECISIONS.md`.

### 4.6 Protected request behavior

Protected requests use:

```http
Authorization: Bearer <access_token>
```

The token must be supplied through a centralized session adapter. Ordinary feature components should not read or manipulate token storage directly.

## 5. Role and Endpoint Authorization

The following matrix reflects endpoint-specific rules explicitly documented in `API_GUIDELINES.md`. It supersedes broad conceptual role assumptions in frontend presentation, but the live backend remains authoritative.

| Operation | ADMIN | ANALYST | INVESTIGATOR |
|---|---:|---:|---:|
| Read transaction | Yes | Yes | Yes |
| Read transaction risk | Yes | Yes | Yes |
| Analyze with ACTIVE model | Yes | Yes | Yes |
| Analyze with VALIDATED model | Yes | No | No |
| Dataset import | Yes | Yes | No |
| Read import detail | Yes | Yes | Yes |
| Import recovery | Yes | Yes | No |
| List/create/read investigations | Yes | Yes | Yes |
| Update investigation | Admin authority | Restricted by endpoint policy | Assignment-scoped |
| Resolve investigation | Yes | No | Assigned case only |
| List associated transactions | Yes | Yes | Yes |
| Link related transaction | Yes | No | Assigned case only |
| List evidence | Yes | Yes | Yes, subject to object scope |
| Attach evidence | Yes | No | Assigned case only |
| Generate AI summary | Yes | No | Assigned case only |
| Read latest AI summary/history | Yes | Yes | Assigned case only |

Important details:

- `GET /investigations/{id}` is role-accessible, but investigator object access may be scoped by assignment rules in the implementation.
- AI summary generation is Admin or assigned Investigator only.
- Analysts have read-only AI summary access.
- Evidence listing and evidence attachment have different permissions.
- Risk analysis permission depends on model lifecycle as well as role.
- A frontend permission helper is only a presentation convenience. Handle server `403` responses.

## 6. Common Request and Response Conventions

### 6.1 Single-resource responses

The API guidelines prefer direct resource objects rather than wrapping every response in a global `{ "success": true, "data": ... }` envelope.

Do not assume a global success envelope.

### 6.2 Collection responses

A common documented collection shape is:

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "total_pages": 0
}
```

Not every collection uses the same exact shape. For example, evidence and investigation transaction collections have their own documented response fields. Use the generated endpoint-specific schema rather than a universal handwritten collection type.

### 6.3 Pagination

Documented page pagination convention:

```text
page       default 1
page_size  suggested default 25
page_size  suggested maximum 100
```

Examples:

```http
GET /api/v1/transactions?page=1&page_size=50
GET /api/v1/investigations?page=1&page_size=25
```

Endpoint-specific defaults may differ. Investigation evidence documents `page_size=50`; AI summary history documents `page_size=20`. Use the actual endpoint contract.

Cursor pagination is described as a possible future option for high-volume transaction feeds, not a universal MVP requirement. Do not send `cursor` or `limit` unless the live endpoint supports them.

### 6.4 Sorting

The API guidelines describe:

```text
sort=<whitelisted_field>
order=asc|desc
```

Example:

```http
GET /api/v1/transactions?sort=occurred_at&order=desc
```

Only send sorting parameters supported by the endpoint's actual OpenAPI schema.

### 6.5 Filtering and search

The guidelines describe explicit filters, including transaction fields such as:

- `account_id`
- `merchant_id`
- `device_id`
- `location_id`
- `transaction_type`
- `direction`
- `category`
- `risk_level`
- `from`
- `to`
- `min_amount`
- `max_amount`

Do not assume every endpoint supports every filter. Search must be scoped to documented fields; do not invent a generic `q` parameter.

### 6.6 Date/time

- API timestamps use ISO-8601 and are timezone-aware.
- Preserve timezone offsets and use explicit display timezone rules.
- Analytics time windows use the documented half-open interval `[from_time, to_time)`.
- Do not silently convert a user-selected inclusive end date into an incorrect timestamp boundary. Implement date-range serialization in one tested utility based on each endpoint's contract.

### 6.7 Monetary values

The API guidelines specify decimal-safe monetary strings, for example:

```json
{
  "amount": "1250.50",
  "currency": "INR"
}
```

Keep monetary strings intact at the API boundary. Do not use JavaScript floating-point arithmetic for authoritative financial values. Do not combine amounts across currencies unless the backend explicitly returns a normalized aggregate and defines its currency semantics.

## 7. Endpoint Integration Catalogue

The tables below summarize routes documented in `API_GUIDELINES.md`. They are an integration inventory, not proof of current runtime availability.

### 7.1 Authentication

| Method | Path | Frontend use |
|---|---|---|
| POST | `/auth/register` | Registration only if product policy enables it |
| POST | `/auth/login` | Sign-in |
| GET | `/auth/me` | Current-user context |
| POST | `/auth/logout` | Verify exact behavior before use |

### 7.2 Transactions and risk

> [!IMPORTANT]
> **Endpoint Implementation Status:**
> - `GET /transactions`: **APPROVED REQUIREMENT — NOT YET IMPLEMENTED** (Per ADR-077, scheduled for implementation in Phase F0 per `docs/BACKEND_API_READINESS.md`).
> - `GET /transactions/{transaction_id}`: **APPROVED REQUIREMENT — NOT YET IMPLEMENTED** (Per ADR-077, scheduled for implementation in Phase F0 per `docs/BACKEND_API_READINESS.md`).
> - `POST /transactions`: Unimplemented / Deferred (Creation occurs via dataset CSV ingestion; individual transaction creation is not an MVP workflow).
> - `GET /transactions/{transaction_id}/risk`: **IMPLEMENTED** (Phase 8).
> - `POST /transactions/{transaction_id}/risk/analyze`: **IMPLEMENTED** (Phase 8).

| Method | Path | Frontend use | Documented access / behavior |
|---|---|---|---|
| GET | `/transactions` | Transaction list | **Approved Requirement — Not Yet Implemented.** Paginated & filterable; see `BACKEND_API_READINESS.md` |
| GET | `/transactions/{transaction_id}` | Transaction detail | **Approved Requirement — Not Yet Implemented.** Returns core transaction facts; see `BACKEND_API_READINESS.md` |
| POST | `/transactions` | Transaction creation | Not implemented; not a frontend MVP workflow |
| GET | `/transactions/{transaction_id}/risk` | Latest persisted risk | Implemented (Phase 8). Admin, Analyst, Investigator; pure read; 404 if no analysis |
| POST | `/transactions/{transaction_id}/risk/analyze` | On-demand risk analysis | Implemented (Phase 8). Role and model-lifecycle restrictions |

Risk analysis specifics:

- Omitted `model_version_id` resolves the currently `ACTIVE` model.
- `ACTIVE`: Admin, Analyst, Investigator.
- `VALIDATED`: Admin only.
- `EXPERIMENTAL` and `RETIRED`: ineligible for new analysis.
- Note: `RiskAnalyzeRequest` accepts only `model_version_id` (optional). It does not accept `force_recalculate` (`extra="forbid"`). Idempotency is enforced by canonical analysis identity (re-evaluating identical inputs returns existing record).
- The backend may return an existing identical analysis idempotently.
- A successful analysis request is documented as `200 OK`, whether generated or retrieved.
- A `404` from the risk read endpoint may mean no analysis exists; do not render that as low risk.

Documented risk response includes score, risk level, model/config versions, ML score fields, rule score, normalization parameters, creation time, and risk factors. Render only fields actually returned by the current schema.

### 7.3 Dataset imports

> [!IMPORTANT]
> **Endpoint Implementation Status:**
> - `POST /datasets/imports`: **IMPLEMENTED** (Phase 4).
> - `GET /datasets/imports`: **APPROVED REQUIREMENT — NOT YET IMPLEMENTED** (Per ADR-077, scheduled for implementation in Phase F0 per `docs/BACKEND_API_READINESS.md`).
> - `GET /datasets/imports/{import_id}`: **IMPLEMENTED** (Phase 4).
> - `POST /datasets/imports/{import_id}/recover`: **IMPLEMENTED** (Phase 4).

| Method | Path | Frontend use | Access |
|---|---|---|---|
| POST | `/datasets/imports` | Upload CSV | Implemented (Phase 4). Admin, Analyst |
| GET | `/datasets/imports` | List import executions | **Approved Requirement — Not Yet Implemented.** Paginated import history; see `BACKEND_API_READINESS.md` |
| GET | `/datasets/imports/{import_id}` | Import detail and validation errors | Implemented (Phase 4). Admin, Analyst, Investigator |
| POST | `/datasets/imports/{import_id}/recover` | Recover failed/interrupted import | Implemented (Phase 4). Admin, Analyst |

Upload contract documented:

- Multipart form-data.
- `file` is a CSV payload.
- Maximum file size: 50 MB.
- UTF-8 and UTF-8 BOM supported.
- `source_namespace` default: `SYNTHETIC`.
- `source_type` default: `SYNTHETIC`.

Import behavior documented:

| Condition | Response |
|---|---|
| New import | `201 Created`, `is_duplicate=false` |
| Identical completed import in same namespace | `200 OK`, existing summary, `is_duplicate=true` |
| Same file currently pending/processing | `409 Conflict`, `IMPORT_IN_PROGRESS` |
| File exceeds limit | `413`, `PAYLOAD_TOO_LARGE` |
| CSV parse/field validation failure | `422` with documented error code |

The import response includes ID, namespace, filename, file hash, source type, status, row counters, timestamps, and duplicate flag. The detail response includes up to 100 recorded validation/quarantine errors in the documented example.

Recovery accepts the original file as multipart data and verifies its SHA-256 against the existing import. Implement the recovery action only after confirming its current runtime contract and allowed state transitions.

### 7.4 Analytics

| Method | Path | Frontend use |
|---|---|---|
| GET | `/analytics/overview` | Dashboard overview |
| GET | `/analytics/trends` | Time-series analytics |
| GET | `/analytics/categories` | Category distribution |
| GET | `/analytics/merchants` | Merchant analytics |
| GET | `/analytics/accounts/{account_id}` | Account activity |
| GET | `/analytics/accounts/{account_id}/unusual-spending` | Account unusual-spending outliers |

The API guidelines contain endpoint-specific parameters and response examples for these analytics routes. The frontend must use those endpoint-specific contracts, including supported date range, namespace, currency, bucket, and filtering parameters.

Analytics responses are backend-computed. The frontend may map response fields to chart series, labels, and tables; it must not recompute the financial aggregates from transaction rows.

### 7.5 Investigations

| Method | Path | Frontend use | Access documented |
|---|---|---|---|
| GET | `/investigations` | Shared queue | Admin, Investigator, Analyst |
| POST | `/investigations` | Manual case creation | Admin, Investigator, Analyst |
| GET | `/investigations/{id}` | Workspace | Admin, Investigator, Analyst |
| PATCH | `/investigations/{id}` | Assignment/priority/status update | Endpoint-specific rules |
| POST | `/investigations/{id}/resolve` | Human resolution | Admin or assigned Investigator |
| GET | `/investigations/{id}/transactions` | Primary/related transaction list | Admin, Investigator, Analyst |
| POST | `/investigations/{id}/transactions` | Link related transaction | Admin or assigned Investigator |
| GET | `/investigations/{id}/evidence` | Evidence list | Admin, Investigator, Analyst |
| POST | `/investigations/{id}/evidence` | Attach evidence | Admin or assigned Investigator |

Investigation list filters documented:

- `page`
- `page_size`
- `status`: `OPEN`, `UNDER_REVIEW`, `RESOLVED`
- `priority`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `assigned_to`
- `unassigned`

Supplying both `assigned_to` and `unassigned=true` returns `400 FILTER_CONFLICT`.

Create request example:

```json
{
  "transaction_id": "transaction-uuid",
  "priority": "HIGH"
}
```

Creation is manual-first. Note: the backend schema (`InvestigationCreateRequest`) strictly forbids additional properties (`extra="forbid"`); do not send fields such as `notes` or `title` during creation. If investigator notes are needed, attach them post-creation via `POST /api/v1/investigations/{id}/evidence` with `evidence_type: "USER_NOTE"`. The backend creates an `OPEN`, unassigned investigation and binds the primary transaction.

Workspace response is documented as an `InvestigationDetailResponse` containing investigation metadata, primary transaction context, related transaction count, and latest risk-analysis context. Verify exact nested fields from OpenAPI before coding.

Resolution request example:

```json
{
  "resolution": "CONFIRMED_FRAUD",
  "resolution_notes": "Non-empty explanation of the human decision."
}
```

Allowed outcomes:

- `LEGITIMATE`
- `SUSPICIOUS`
- `CONFIRMED_FRAUD`
- `INCONCLUSIVE`

Resolution requires non-empty, non-whitespace notes and a case currently in `UNDER_REVIEW`. An `OPEN` case cannot be resolved directly. Resolved cases are immutable.

Related transaction linking:

- Must use the same `source_namespace` as the primary transaction.
- Must satisfy the documented direct 1-hop shared-account predicate.
- Cannot link a transaction already linked to the case.
- Cannot link to a resolved investigation.
- The frontend must not implement recursive graph traversal.

Evidence list:

- Uses page pagination.
- Documented default `page_size=50`, maximum `100`.
- Deterministic ordering: `created_at ASC, id ASC`.

Evidence attachment:

- Append-only; no edit or delete API is supported.
- Maximum serialized JSON payload size: 64 KB.
- `evidence_type` and `source_type` must be compatible.
- `source_id` must be null if and only if `source_type` is `USER_NOTE`.
- Backend verifies source existence and investigation scope.
- Resolved investigations reject new evidence.

### 7.6 AI investigation summaries

| Method | Path | Frontend use | Access documented |
|---|---|---|---|
| POST | `/investigations/{id}/ai-summary` | Generate/refresh summary | Admin, assigned Investigator |
| GET | `/investigations/{id}/ai-summary` | Latest summary | Admin, Analyst, assigned Investigator |
| GET | `/investigations/{id}/ai-summary/history` | Summary history | Admin, Analyst, assigned Investigator |

Generation request body is optional:

```json
{
  "force_refresh": false
}
```

The documented behavior:

- If `force_refresh=false`, a matching latest completed summary may be returned from cache when `evidence_hash` and `prompt_version` match current case state.
- `force_refresh=true` requests a fresh generation.
- The documented response is `200 OK` with `AISummaryResponse`.
- The response includes status, summary, `is_stale`, error message, provider/model metadata, hashes, and timestamps.
- `GET` latest summary returns `404 AI_SUMMARY_NOT_FOUND` if no summary attempt exists.
- History uses `page` and `page_size`; documented default is 20 and maximum is 100.
- Analysts have read-only access; they cannot generate.
- Investigators are restricted to assigned investigations.

Structured summary fields:

- `executive_summary`
- `observed_facts`
- `derived_signals`
- `potential_interpretations`
- `uncertainties_and_limitations`

The frontend must display these as distinct sections. Evidence IDs included in fact/signal items should be linked to the corresponding evidence only when the referenced evidence can be resolved through a supported API.

**Lifecycle caution:** the API guidelines describe a “two-transaction generation cycle” and also show a `200 OK` response with a status field. They do not fully define a universal polling contract or every possible status transition in the excerpts. Do not invent polling intervals or status values. Verify the actual response model and runtime behavior before implementing generation progress.

### 7.7 Accounts, merchants, and devices

Documented endpoint summary:

| Method | Path |
|---|---|
| GET | `/accounts` |
| GET | `/accounts/{account_id}` |
| GET | `/accounts/{account_id}/behavior` |
| GET | `/merchants` |
| GET | `/merchants/{merchant_id}` |
| GET | `/merchants/{merchant_id}/transactions` |
| GET | `/devices` |
| GET | `/devices/{device_id}` |
| GET | `/devices/{device_id}/accounts` |
| GET | `/devices/{device_id}/transactions` |

These routes appear in the API endpoint summary. Their exact query parameters, response schemas, pagination, and authorization must be verified against OpenAPI before building detail workflows. The presence of a route in a summary is not enough to define its frontend contract.

### 7.8 Health and readiness

Documented system endpoints:

```text
GET /health
GET /ready
GET /api/v1/health
GET /api/v1/ready
```

The API guidelines describe health and readiness as distinct concepts. These are primarily operational endpoints; do not expose internal readiness diagnostics to ordinary users unless the backend response and product requirements explicitly support a user-facing status view.

## 8. Central API Client Contract

All feature API functions must use one centralized client.

Conceptual responsibilities:

```ts
type ApiError = {
  status: number;
  code?: string;
  message: string;
  details?: unknown;
  requestId?: string;
  retryAfterSeconds?: number;
};

type RequestOptions = {
  signal?: AbortSignal;
};
```

The actual implementation should:

- Resolve the configured base URL.
- Apply the approved session/authentication mechanism.
- Set `Accept: application/json` for JSON requests.
- Set `Content-Type: application/json` only for JSON bodies.
- Allow the browser to set multipart boundaries for `FormData`.
- Parse JSON responses safely.
- Handle `204 No Content` without attempting JSON parsing.
- Preserve backend error codes and safe messages.
- Capture request IDs when returned.
- Pass through `AbortSignal`.
- Avoid logging sensitive headers or payloads.

Do not assume every backend response is JSON in every failure case. The client should handle malformed or empty error bodies safely.

## 9. Feature API Module Boundaries

Suggested modules:

```text
features/
  auth/api/auth-api.ts
  transactions/api/transactions-api.ts
  analytics/api/analytics-api.ts
  datasets/api/datasets-api.ts
  risk/api/risk-api.ts
  investigations/api/investigations-api.ts
  accounts/api/accounts-api.ts
```

Each module owns endpoint-specific functions and request/response types. Generated API types should be imported from the generated contract file.

Illustrative function names (not guaranteed route names):

```ts
login(request)
getCurrentUser(signal)
getTransactions(filters, signal)
getTransaction(transactionId, signal)
getTransactionRisk(transactionId, signal)
analyzeTransactionRisk(transactionId, request)
createDatasetImport(formData)
getDatasetImport(importId, signal)
recoverDatasetImport(importId, formData)
getAnalyticsOverview(params, signal)
getInvestigationQueue(filters, signal)
createInvestigation(request)
getInvestigationWorkspace(investigationId, signal)
updateInvestigation(investigationId, request)
resolveInvestigation(investigationId, request)
getInvestigationTransactions(investigationId, signal)
linkRelatedTransaction(investigationId, request)
getInvestigationEvidence(investigationId, pagination, signal)
attachInvestigationEvidence(investigationId, request)
generateAiSummary(investigationId, request)
getLatestAiSummary(investigationId, signal)
getAiSummaryHistory(investigationId, pagination, signal)
```

Before implementing each function, verify the exact method, path, parameter names, and generated request/response type.

## 10. Query Keys and Cache Invalidation

If TanStack Query is approved, query keys must encode all parameters that affect the server response.

Examples:

```ts
const transactionKeys = {
  all: ["transactions"] as const,
  list: (filters: TransactionFilters) =>
    [...transactionKeys.all, "list", filters] as const,
  detail: (id: string) =>
    [...transactionKeys.all, "detail", id] as const,
  risk: (id: string) =>
    [...transactionKeys.all, "risk", id] as const,
};

const investigationKeys = {
  all: ["investigations"] as const,
  list: (filters: InvestigationFilters) =>
    [...investigationKeys.all, "list", filters] as const,
  detail: (id: string) =>
    [...investigationKeys.all, "detail", id] as const,
  transactions: (id: string) =>
    [...investigationKeys.all, id, "transactions"] as const,
  evidence: (id: string, page: number, pageSize: number) =>
    [...investigationKeys.all, id, "evidence", page, pageSize] as const,
  aiSummary: (id: string) =>
    [...investigationKeys.all, id, "ai-summary"] as const,
  aiSummaryHistory: (id: string, page: number, pageSize: number) =>
    [...investigationKeys.all, id, "ai-summary-history", page, pageSize] as const,
};
```

Include namespace, currency, date range, timezone, filters, sort, and pagination when they affect the response. Never include credentials or tokens in query keys.

Mutation invalidation expectations:

| Mutation | Queries to refresh/invalidate |
|---|---|
| Create dataset import | Import detail/status if available; analytics/transaction queries only when ingestion completion is confirmed and relevant |
| Recover import | Import detail |
| Request risk analysis | Transaction risk; transaction detail if it embeds risk; relevant investigation workspace |
| Create investigation | Investigation queue; new investigation detail |
| Update assignment/status | Investigation queue; investigation detail |
| Resolve investigation | Investigation queue; investigation detail |
| Link related transaction | Investigation detail; associated transaction list |
| Attach evidence | Evidence list; investigation workspace; latest AI summary state if it is displayed there |
| Generate AI summary | Latest summary; summary history; investigation workspace |

Avoid invalidating all queries after every mutation. Do not optimistically mark a case resolved before the backend confirms it.

## 11. Error Contract and Frontend Mapping

### 11.1 Documented error envelope

The API guidelines provide this example:

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

Validation errors may place field-specific messages in `error.details`.

The frontend should normalize this into one internal error type while preserving the backend's stable code.

### 11.2 Status mapping

| HTTP status | Frontend handling |
|---|---|
| 400 | Display request/filter/model eligibility error; show safe details |
| 401 | Run approved session-expiration flow; do not repeatedly retry |
| 403 | Display access-denied state; do not leak protected resource details |
| 404 | Display resource-not-found or endpoint-specific absence state |
| 409 | Explain conflict; refresh authoritative resource before retry |
| 413 | Explain documented upload/payload limit |
| 422 | Map field-level validation errors where possible |
| 429 | Respect `Retry-After` if supplied; prevent rapid repeated submissions |
| 500 | Generic server failure with request ID if available |
| 502 | Upstream/provider/schema/grounding failure for documented AI cases |
| 503 | Service/dependency unavailable; offer safe retry |
| 504 | Timeout; do not assume the backend operation definitely did not complete |

### 11.3 Endpoint-specific absence semantics

- `GET /transactions/{id}/risk`: `404` may mean transaction missing or no risk analysis exists. The UI should distinguish these only if the backend error code distinguishes them.
- `GET /investigations/{id}/ai-summary`: `404 AI_SUMMARY_NOT_FOUND` means no summary attempt exists.
- A failed query must never be rendered as an empty successful collection.

### 11.4 Request IDs

The API guidelines require request/correlation IDs. Verify the actual header/response field and use the returned identifier in support/error presentation. Do not invent a header name.

## 12. Request Cancellation, Retries, and Concurrency

### 12.1 Cancellation

Pass `AbortSignal` through query functions where supported. Cancel obsolete list requests when filters change or the user navigates away, where practical.

Cancellation in the browser does not guarantee that a server-side mutation was rolled back.

### 12.2 Retry policy

- Do not automatically retry non-idempotent `POST` operations without a documented idempotency guarantee.
- Do not retry `401`, `403`, `409`, or validation errors blindly.
- Safe read retries may be bounded and should account for `429`, `503`, and network errors.
- Respect `Retry-After` when returned.
- For timeout on a mutation, reconcile by fetching the resource or operation state before resubmitting.

### 12.3 Concurrency

Investigation assignment, lifecycle transitions, evidence attachment, and resolution can race with another user or process.

- Treat `409` as a state conflict, not a generic server error.
- Refresh the authoritative investigation.
- Re-evaluate whether the action remains available.
- Do not repeatedly submit the stale mutation.
- Do not assume optimistic UI state is correct after a conflict.

The exact optimistic concurrency mechanism (for example, version field or ETag) must be verified; do not invent `If-Match` or version headers.

## 13. Upload and Evidence Payload Handling

### 13.1 Dataset upload

- Use `FormData`.
- Append the file under the exact field name `file`.
- Include `source_namespace` and `source_type` when required or intentionally overriding defaults.
- Do not manually set `Content-Type: multipart/form-data`; the browser must supply the boundary.
- Client-side size validation may reject files over 50 MB for immediate feedback.
- Backend validation remains authoritative.
- Display import ID, status, row counters, duplicate flag, and errors returned by the API.

### 13.2 Evidence attachment

Evidence payloads are JSON, with a documented maximum serialized payload size of 64 KB.

- Enforce a reasonable client-side size warning, but backend remains authoritative.
- Do not permit editing or deletion of persisted evidence.
- Do not allow arbitrary `source_id` references without selecting from supported source entities.
- Do not fabricate evidence payload structure; use generated request schemas.
- Display source type and source ID where useful for traceability.
- User notes use `source_type=USER_NOTE` and require `source_id=null` according to the documented rule.

## 14. AI Summary Integration Details

### 14.1 Generate

```http
POST /api/v1/investigations/{id}/ai-summary
Authorization: Bearer <access_token>
Content-Type: application/json
```

Optional body:

```json
{
  "force_refresh": false
}
```

The documented endpoint returns `200 OK` with an `AISummaryResponse`. The response may represent cached or newly generated content and includes a status field.

### 14.2 Read latest and history

```http
GET /api/v1/investigations/{id}/ai-summary
GET /api/v1/investigations/{id}/ai-summary/history?page=1&page_size=20
```

### 14.3 Rendering contract

Keep the five structured summary fields separate:

- Executive summary
- Observed facts
- Derived signals
- Potential interpretations
- Uncertainties and limitations

For observed facts and derived signals, display the associated evidence IDs. Provide navigation only if the evidence endpoint can resolve the ID within the investigation.

Show `is_stale` explicitly when true. Do not relabel stale content as current.

### 14.4 Lifecycle ambiguity to resolve

The API documentation mentions a two-transaction generation cycle, but the examples show a `200 OK` response with a status field and do not fully define a separate job polling endpoint or every status value.

Before implementation, inspect:

- Actual `AISummaryResponse` schema.
- Runtime behavior for first generation.
- Runtime behavior when generation is already in progress.
- Exact status enum values.
- Whether the client should poll the latest-summary endpoint or wait for the `POST` response.
- Retry behavior after `502` or `504`.
- Whether a failed attempt is included in history.

Do not build a generic asynchronous job framework until the actual contract requires it.

## 15. OpenAPI Type Generation and Contract Verification

### 15.1 Source

FastAPI exposes `/openapi.json` in development according to the API guidelines.

### 15.2 Verification workflow

Before generating types:

1. Start the backend using the project's documented environment.
2. Fetch the actual OpenAPI document.
3. Confirm the `/api/v1` routes are represented.
4. Verify request and response schemas for each MVP workflow.
5. Verify authentication schemes and endpoint security declarations.
6. Verify status codes, query parameter names, and multipart field names.
7. Compare any mismatch with `API_GUIDELINES.md`.
8. Resolve discrepancies or document an agreed exception.
9. Generate frontend types from the verified schema.

### 15.3 Generated artifacts

- Store generated types in a marked generated file or directory.
- Do not manually edit generated output.
- Choose and document whether generated output is committed or generated in CI.
- Add a CI check for stale generated types if practical.
- Use endpoint-specific generated types in API modules.
- Keep runtime validation selective; generated TypeScript types do not validate JSON at runtime.

### 15.4 Contract tests

At minimum, verify:

- Method and path.
- Query parameter serialization.
- Request body shape.
- Multipart field names.
- Authorization header/session integration.
- Response parsing.
- Error envelope parsing.
- Empty and `204` response handling.

## 16. Contract Gaps and Documentation Issues

The following items require verification rather than frontend assumptions.

| Issue | What documentation says | Required action |
|---|---|---|
| Logout | `/auth/logout` appears in endpoint summary, while section 9.4 describes logout strategy options and says JWT is stateless by default. | Verify whether route is implemented, its method/body/response, and whether it revokes anything. |
| Authentication expiration | Login response includes `expires_in`; exact expiration and refresh strategy remain open. | Confirm runtime token policy and document it in `FRONTEND_SECURITY.md`. |
| Role matrix | Section 10 is conceptual and differs from endpoint-specific rules in dataset, investigation, evidence, and AI sections. | Use endpoint-specific rules; reconcile source docs and ADRs. |
| Transaction filters | Guidelines list supported filters as “may include.” | Inspect actual OpenAPI query parameters. |
| Pagination | Page-based convention is general; endpoint defaults differ; cursor pagination is only a future possibility. | Use exact per-endpoint schema and defaults. |
| Analytics filters/responses | Endpoint sections define detailed examples, but exact live schemas must be checked. | Generate types from running OpenAPI and compare examples. |
| Investigation PATCH | Described as assignment/priority/status update; precise field-level role rules and valid transitions must be confirmed from implementation/OpenAPI/security docs. | Verify request model and permission matrix before exposing controls. |
| Workspace composition | Workspace endpoint is documented as a complete envelope, but exact nested schema must be verified. | Inspect generated schema and runtime response. |
| AI generation lifecycle | Two-transaction generation cycle is mentioned; polling/status semantics are not fully specified in the documented contract. | Verify actual status values and whether polling is needed. |
| Account/merchant/device details | Endpoint summary lists routes, but not all schemas and filters are fully specified in the reviewed API sections. | Verify exact routes, schemas, pagination, and RBAC. |
| Audit read API | Auditability is required, but a frontend audit read endpoint is not in the recommended endpoint summary. | Do not build audit history until a read contract exists. |
| Request ID transport | Guidelines require request IDs but the exact header/response transport must be confirmed. | Verify middleware behavior and OpenAPI/header documentation. |
| Error envelope consistency | Error examples vary slightly in whether `request_id` is present and where details are represented. | Confirm one runtime error schema and normalize defensively. |

## 17. Recommended Integration Implementation Order

1. Verify OpenAPI and create generated types.
2. Implement centralized API client and normalized error handling.
3. Implement authentication API functions and session adapter after security decision.
4. Implement current-user query and protected application bootstrap.
5. Implement transaction list/detail and risk read.
6. Implement analytics endpoints.
7. Implement dataset upload/detail/recovery.
8. Implement investigation queue/create/workspace.
9. Implement assignment/status and resolution mutations.
10. Implement associated transactions and evidence.
11. Implement AI summary generation/latest/history.
12. Implement account/merchant/device workflows only after contract verification.

This is an integration sequence, not a replacement for the implementation phases in `FRONTEND_ROADMAP.md`.

## 18. Definition of Done

This document is ready to guide implementation when:

- Every MVP operation is mapped to a verified OpenAPI route and schema.
- Endpoint-specific role and assignment rules are reconciled with backend implementation.
- Logout and token/session semantics are finalized.
- Pagination, filters, date semantics, and error formats are verified.
- AI summary lifecycle behavior is confirmed.
- Generated API types are produced from the verified schema.
- Contract gaps are resolved or explicitly excluded from the first release.
- API client and feature module boundaries align with `FRONTEND_ARCHITECTURE.md`.

## 19. Final Integration Principle

The frontend must consume the API contract that the backend actually implements—not the contract it wishes existed.

**When documentation, generated OpenAPI, and runtime behavior disagree, stop and reconcile the discrepancy. Do not hide it with guessed request fields, fabricated responses, or frontend-side business logic.**
