# FinSignal
## Technical Requirements Document (TRD)

**Product:** FinSignal  
**Full Name:** Financial Transaction Intelligence & Investigation Platform  
**Document:** Technical Requirements Document  
**Version:** 1.0.0  
**Status:** Approved / Current  
**Last Updated:** 2026-11-04

---

# 1. Purpose

This document defines the technical requirements and implementation direction for FinSignal.

The PRD defines **what FinSignal should accomplish**.

This document defines the technical constraints and engineering requirements for **how those capabilities should be implemented**.

The technical design must support:

- Financial transaction ingestion
- Data validation and cleaning
- Behavioral feature generation
- Financial analytics
- Machine-learning-based anomaly detection
- Risk scoring
- Investigation workflows
- Evidence generation
- AI-assisted investigation summaries
- JWT authentication
- Role-based authorization
- PostgreSQL persistence
- REST APIs
- Reproducible ML experiments
- Containerized development

The architecture should remain modular without introducing infrastructure that is not justified by the current product scope.

---

# 2. Technical Goals

The implementation should satisfy the following goals:

1. Use Python as the primary backend and data/ML language.
2. Provide a clean REST API through FastAPI.
3. Use PostgreSQL as the primary relational database.
4. Keep analytics and ML capabilities within the Python backend initially.
5. Separate raw financial facts from derived intelligence.
6. Prevent data leakage during feature generation and model evaluation.
7. Provide deterministic and reproducible data generation.
8. Keep ML components independently testable.
9. Provide secure JWT-based authentication.
10. Provide role-based authorization.
11. Support Docker-based local development.
12. Keep future expansion possible without premature distributed architecture.

---

# 3. Technology Stack

## 3.1 Backend

**Language:** Python

**Framework:** FastAPI

FastAPI is responsible for:

- HTTP APIs
- Request validation
- Authentication integration
- Authorization
- Service orchestration
- API documentation
- Error handling

---

## 3.2 Database

**Database:** PostgreSQL

PostgreSQL is the primary persistent datastore.

It will store:

- Users
- Accounts
- Merchants
- Devices
- Locations
- Transactions
- Risk analyses
- Risk factors
- Investigations
- Investigation evidence
- AI summaries
- Other application metadata

PostgreSQL is preferred because FinSignal combines relational data with time-oriented transaction analysis and may later benefit from PostgreSQL extensions such as `pgvector`.

---

## 3.3 Data Processing

Initial data-processing technologies:

- Pandas
- NumPy

Pandas should be used for:

- Dataset ingestion
- Cleaning
- Transformation
- Aggregation
- Exploratory analysis
- Feature preparation

NumPy should be used where numerical operations benefit from array-based computation.

---

## 3.4 Machine Learning

**Primary ML framework:** scikit-learn

### Dependency Specifications
- **Declared Constraints (`pyproject.toml`):**
  - `scikit-learn>=1.5.0,<2.0.0`
  - `joblib>=1.4.0,<2.0.0`
  - `numpy>=2.0.0,<3.0.0`
- **Locked Runtime Versions (`uv.lock`):**
  - `scikit-learn`: `1.9.1`
  - `joblib`: `1.6.0`
  - `numpy`: `2.5.4`
  - `scipy`: `1.18.1` (transitive runtime dependency)

### Implemented Phase 7 ML Capabilities
- **Model Wrapper (`IsolationForestModel`):** Encapsulates scikit-learn's `IsolationForest` (`n_estimators=100`, `random_state=42`) with score negation $S(X) = - \text{score\_samples}(X)$.
- **Feature Extraction (`FeatureVectorizer`):** Converts 34-feature vectors to `(N, 34)` float64 arrays under `FEATURE_VERSION = "v1.0"`.
- **Chronological Data Partitioning (`ChronologicalSplitter`):** Target 60% Train, 20% Validation, 20% Test split with equal-timestamp group preservation.
- **Constrained Threshold Tuning (`ModelEvaluator`):** Maximizes validation F1 subject to $\text{alert\_rate} \le 0.05$ (5%), with boundary candidate zero-alert fallback and single-pass holdout evaluation.
- **Artifact Security & Integrity (`ModelArtifactStore`):** Two-phase atomic tempfile writes, SHA-256 digest computation, path containment verification, and pre-deserialization validation.
- **Model Registry (`ModelRepository`):** Managed via SQLAlchemy ORM and Alembic migration `0004_model_versions` (parent: `0003_account_import_namespace`), enforcing row-level locking during promotion and partial unique index `uq_model_versions_active_family`.
- **Inference Service (`MLService`):** Orchestrates dynamic PostgreSQL active-model resolution, in-memory caching validated against `artifact_hash`, and online scoring.

### Implemented Phase 8 Risk Analysis & Explainability Capabilities
- **Risk Scoring Engine (`HybridScoringEngine`):** Combines normalized ML anomaly scores and deterministic rule scores: $\text{raw} = (w_{\text{ml}} \cdot S_{\text{norm}}) + (w_{\text{rule}} \cdot S_{\text{rule}})$ ($w_{\text{ml}}=0.60, w_{\text{rule}}=0.40$), clamped to $[0.00, 100.00]$ and mapped to tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Validation-Anchored Normalization (`normalize_ml_score`):** Piecewise linear interpolation anchored to empirical validation bounds $(s_{\min} \mapsto 0.0, \tau^* \mapsto 50.0, s_{\max} \mapsto 100.0)$ enforcing $s_{\min} < \tau^* < s_{\max}$.
- **Deterministic Heuristic Rules (`RiskRuleEngine`):** Evaluates 9 financial heuristics across velocity, amount deviation, entity novelty, temporal deviations, and cold-start accounts into bounded rule score $S_{\text{rule}} \in [0.0, 100.0]$.
- **Fingerprinting & Idempotency:** Canonical 34-feature SHA-256 fingerprinting and effective config identity hash (`effective_config_version`) backed by composite unique constraint `uq_risk_analyses_identity`.
- **Persistence & Conflict Recovery (`RiskRepository`):** Managed via SQLAlchemy ORM and Alembic migration `0005_intelligence_risk_models` (down-revision `0004_model_versions`). Implements atomic nested transaction savepoint (`session.begin_nested()`) recovering from PostgreSQL unique violation `23505` on `uq_risk_analyses_identity`.
- **Protected API Endpoints (`RiskService` & API Router):** `GET /api/v1/transactions/{id}/risk` and `POST /api/v1/transactions/{id}/risk/analyze` with role-based authorization (`ADMIN`, `ANALYST`, `INVESTIGATOR`), model lifecycle eligibility gates, and `TRANSACTION_RISK_ANALYZED` audit events.

### Implemented Phase 10 AI Investigation Assistant Capabilities
- **Dedicated AI Domain Package (`src/finsignal/ai/`):** Isolates prompt engineering, context serialization, LLM provider integration, persistence, and grounding validation from case management.
- **Two-Transaction Lifecycle under REPEATABLE READ Snapshot Isolation:**
  - *Transaction 1:* Binds connection with `isolation_level="REPEATABLE READ"`, locks case row (`FOR UPDATE`), evaluates assignment and non-terminal state, lazily recovers expired pending attempts, verifies no active pending attempt, loads complete case graph eagerly, computes dual fingerprints, and inserts a `PENDING` summary row with a cryptographically unique `generation_token`. Implements bounded exponential backoff retries for serialization failure `40001`.
  - *Provider Execution:* Runs strictly outside database transactions, eliminating connection pool starvation during upstream model latency.
  - *Transaction 2:* Persists terminal result (`COMPLETED` or `FAILED`) using compare-and-swap (CAS) token fencing (`WHERE id = :id AND status = 'PENDING' AND generation_token = :token`), accompanied by atomic `AuditEvent` logging (`AI_SUMMARY_GENERATED` or `AI_SUMMARY_FAILED`). Late-arriving responses on rotated tokens are safely discarded.
- **Lazy Expired PENDING Recovery:** Automatically transitions orphaned `PENDING` attempts older than `ai_pending_timeout_seconds` to `FAILED` with generation token rotation, writing an `AI_SUMMARY_FAILED` audit event atomically in the same transaction only when the conditional update succeeds (`rowcount == 1`).
- **Dual Fingerprinting & Account Standing Invalidation:** Authoritative `evidence_hash` covers case metadata, primary transaction, risk analysis, risk factors, related transactions, evidence items, and account `status` and `account_type`. Mutating account standing (e.g., `ACTIVE` to `FROZEN`) alters the hash, enabling dynamic staleness detection (`is_stale: true`) on `GET`.
- **Structured Schema & Grounding Validation:** Enforces strict Pydantic v2 schema `AISummaryOutput` (`executive_summary`, `observed_facts`, `derived_signals`, `potential_interpretations`, `uncertainties_and_limitations`) with automated entity citation validation.
- **Provider Abstraction (`BaseAIProvider`):** Implemented via `MockAIProvider` with simulated latency, deterministic scenario generation, and fault injection. Production external LLMs remain deferred.

### Implemented Phase 11 Testing, Security & Hardening Capabilities
- **CORS Defense & Origin Isolation:** Configured FastAPI `CORSMiddleware` with explicit origin allowlist (`cors_origins`), methods, headers, and credential isolation (`allow_credentials=True` only for explicit origins; wildcards with credentials forbidden).
- **Bounded Streaming Ingestion & Recovery:** Streaming chunk-by-chunk processing with 50 MB hard cap (`MAX_UPLOAD_SIZE_BYTES = 52_428_800`), immediate HTTP 413 (`PayloadTooLargeError`) abort, `utf-8-sig` encoding supporting standard UTF-8 and UTF-8 BOM, safe stream handle detachment (`text_stream.detach()`), and explicit `csv.Error` recovery returning HTTP 422.
- **Environment Isolation:** Custom Pydantic settings source `_FinSignalEnvSettingsSource` strips ambient OS environment variables, requiring `FINSIGNAL_` prefix for OS overrides while preserving backward-compatible `.env` parsing.
- **Sliding-Window Login Rate Limiter (`AuthRateLimiter`):** Non-blocking in-memory rate limiter enforcing 5 failed attempts per 60 seconds per IP + email key, atomic in-flight admission control (max 2 concurrent requests per key), guaranteed non-eviction of active reservations, and HTTP 429 (`RATE_LIMIT_EXCEEDED`) with `Retry-After` header.
- **Composite Counterparty Foreign Key:** Alembic migration `0008_security_hardening.py` adds composite foreign key `fk_transactions_counterparty_namespace` enforcing relational dataset isolation on transfers (`(counterparty_account_id, source_namespace)` references `accounts(id, source_namespace)`).
- **Append-Only Audit Immutability:** Migration `0008_security_hardening.py` introduces database trigger `trg_no_update_delete_audit_events` on `audit_events` rejecting all SQL `UPDATE` and `DELETE` queries.
- **Ingestion & Split Optimization:** Batched canonical lookups (`canonical_id = ANY(...)`), bounded reference entity caching (`max_cache_entries = 10_000`), and deterministic tie-breaker in chronological splitting (`str(id) ASC`).

---

## 3.5 Frontend

The frontend will use:

- React
- TypeScript
- Vite
- Tailwind CSS
- Apache ECharts

The frontend is intentionally not covered in detail by this document.

Frontend-specific technical documentation will be created during the frontend phase.

The backend must expose stable API contracts that allow the frontend to be developed independently.

---

## 3.6 Authentication

Authentication will use:

- JWT access tokens
- Secure password hashing
- Role-based authorization

Exact JWT and password-hashing libraries will be finalized during implementation based on current Python ecosystem support.

---

## 3.7 Testing

Backend testing:

- pytest
- pytest-asyncio where asynchronous behavior requires it
- FastAPI testing utilities
- Database integration tests where appropriate

ML/data testing:

- pytest
- deterministic test datasets
- metric-based evaluation
- feature validation tests

Frontend testing will be documented separately.

---

## 3.8 Containerization

Docker will be used for reproducible local development.

The initial environment should support:

```text
Frontend
Backend
PostgreSQL
```

A background worker should only be introduced if asynchronous processing becomes necessary.

---

# 4. Python Environment and Dependency Management

The project should use a modern Python environment and dependency-management workflow.

`uv` is the preferred package and environment management tool unless implementation constraints require another approach.

The project should define:

- Python version
- Runtime dependencies
- Development dependencies
- Test dependencies
- Linting/formatting dependencies
- Dependency lock information

The Python version should be pinned to a supported version selected during implementation.

---

# 5. High-Level Architecture

The initial system should use a modular monolithic backend.

```text
                        +----------------------+
                        |      React UI        |
                        +----------+-----------+
                                   |
                                   | HTTPS / REST
                                   v
                        +----------------------+
                        |      FastAPI         |
                        +----------+-----------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
       Authentication        Application         Data / ML
       & Authorization         Services            Services
              |                    |                    |
              |            +-------+-------+            |
              |            |       |       |            |
              |            v       v       v            |
              |        Analytics Investigation  Feature/ML
              |                    |                    |
              +--------------------+--------------------+
                                   |
                                   v
                           +---------------+
                           |  PostgreSQL   |
                           +---------------+
```

The initial system should avoid splitting the backend into separate microservices.

---

# 6. Modular Monolith Requirement

FinSignal should be implemented as a modular monolith initially.

Logical modules should have clear responsibilities and boundaries.

Potential modules:

```text
auth
user
account
merchant
device
location
transaction
ingestion
analytics
feature
risk
investigation
evidence
ai
dataset
common
```

Modules may evolve as implementation progresses.

The purpose of modular boundaries is to make future extraction possible if genuinely required.

---

# 7. Backend Layering

The backend should use clear application layers.

Recommended conceptual structure:

```text
API / Router
    |
    v
Service
    |
    v
Domain / Business Logic
    |
    v
Repository / Data Access
    |
    v
PostgreSQL
```

Data-processing and ML workflows may have additional layers:

```text
Ingestion
    |
    v
Validation
    |
    v
Cleaning
    |
    v
Enrichment
    |
    v
Feature Engineering
    |
    v
Model / Risk Analysis
```

API routes should not directly contain complex ML or database logic.

---

# 8. API Requirements

FinSignal should expose RESTful APIs.

General API principles:

- Resource-oriented URLs
- JSON request/response bodies
- HTTP status codes used correctly
- Consistent error responses
- Request validation
- Authentication on protected endpoints
- Authorization where required
- Pagination for large collections
- Explicit API versioning strategy

The exact API contract will be documented in `API_GUIDELINES.md`.

---

# 9. API Versioning

The initial API should use a versioned base path.

Recommended:

```text
/api/v1
```

Example:

```text
/api/v1/auth/login
/api/v1/accounts
/api/v1/transactions
/api/v1/investigations
```

Breaking changes should require a new API version.

---

# 10. Authentication Requirements

FinSignal shall provide secure user authentication.

Required capabilities:

- User registration where enabled
- Login
- Password hashing
- JWT access-token generation
- Current-user retrieval
- Protected endpoints
- Role-based access control

Passwords must never be stored in plaintext.

---

# 11. JWT Requirements

JWTs should contain only information required for authentication and authorization.

Potential claims:

```text
sub
role
iat
exp
jti
```

The token should have an explicit expiration time.

Sensitive information must not be embedded in the JWT payload.

---

# 12. Token Lifecycle

The authentication design must define:

- Access-token lifetime
- Token signing algorithm
- Signing-key configuration
- Token validation
- Expiration handling
- Invalid-token handling
- Logout/invalidation strategy

The exact implementation will be finalized in `SECURITY.md`.

---

# 13. Password Security

Passwords must be hashed using a modern password-hashing algorithm supported by the Python ecosystem.

Requirements:

- Never store plaintext passwords.
- Never log passwords.
- Never return password hashes through APIs.
- Use appropriate password-hashing parameters.
- Validate password input securely.

---

# 14. Role-Based Authorization

The initial role model is:

```text
ADMIN
ANALYST
INVESTIGATOR
```

Authorization should be enforced at the application layer.

Example:

```text
ADMIN
  |
  +-- User management
  +-- Dataset management
  +-- Analytics
  +-- Investigations

ANALYST
  |
  +-- Dataset import
  +-- Analytics
  +-- Risk analysis
  +-- Alert review

INVESTIGATOR
  |
  +-- Alert review
  +-- Investigation management
  +-- Evidence review
  +-- Investigation resolution
```

Exact permissions will be defined in `SECURITY.md`.

---

# 15. Database Requirements

PostgreSQL must be the authoritative persistent datastore for application state.

The database must preserve the distinction between:

### Source Facts

Examples:

- Transaction
- Account
- Merchant
- Device
- Location

### Derived Intelligence

Examples:

- Behavioral features
- Risk analysis
- Risk factors
- Investigation evidence
- AI summaries

### Human Decisions

Examples:

- Investigation status
- Investigation resolution
- Investigator notes

---

# 16. Database Migration

Database schema changes should be managed through version-controlled migrations.

Migrations must be:

- Ordered
- Reproducible
- Reviewable
- Applied consistently across environments

The specific migration framework will be selected during implementation.

---

# 17. Core Database Entities

The initial logical model includes:

```text
users
accounts
merchants
devices
locations
transactions
risk_analyses
risk_factors
investigations
investigation_evidence
ai_summaries
```

Additional tables may be introduced where justified.

Detailed schema definitions belong in:

`DATABASE_DESIGN.md`

---

# 18. Transaction Data Model

The transaction model should preserve raw financial facts.

Core fields include:

```text
transaction_id
account_id
timestamp
amount
currency
transaction_type
merchant_id
category
location_id
device_id
payment_method
channel
```

Risk scores must not be stored directly as mutable properties of the raw transaction entity.

Risk analysis belongs in a separate representation.

---

# 19. Risk Analysis Model (Phase 8 Implemented)

Risk analyses are persisted separately from transactions in PostgreSQL (`risk_analyses`), implemented in Phase 8 via migration `0005_intelligence_risk_models.py` (down-revision `0004_model_versions`):

```text
id                     UUID PRIMARY KEY
transaction_id         UUID REFERENCES transactions(id) ON DELETE RESTRICT
model_version_id       UUID REFERENCES model_versions(id) ON DELETE RESTRICT
config_version         VARCHAR(32) (base version + 12-char SHA-256 hash)
feature_vector_hash    VARCHAR(64) (SHA-256 of 34 features & context)
score                  NUMERIC(8,3) CHECK (score >= 0.0 AND score <= 100.0)
risk_level             VARCHAR(16) CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL'))
ml_anomaly_score       FLOAT (raw continuous score)
ml_threshold           FLOAT (operating decision threshold tau*)
normalized_ml_score    FLOAT (piecewise linear score in [0.0, 100.0])
rule_score             FLOAT (cumulative bounded rule score in [0.0, 100.0])
normalization_params   JSONB (calibration bounds snapshot)
created_at             TIMESTAMPTZ DEFAULT now()
```

### Constraints & Idempotency
- Unique constraint `uq_risk_analyses_identity` on `(transaction_id, model_version_id, config_version, feature_vector_hash)` enforces identity and idempotency while enabling re-evaluation across different model versions, configuration fingerprints, or updated features.
- In-flight concurrency races are handled via atomic savepoint rollback (`session.begin_nested()`) on PostgreSQL SQLSTATE `23505`.

---

# 20. Risk Factors (Phase 8 Implemented)

Structured explainability factors are stored in PostgreSQL (`risk_factors`), linked to parent risk analyses with cascading delete:

```text
id                  UUID PRIMARY KEY
risk_analysis_id    UUID REFERENCES risk_analyses(id) ON DELETE CASCADE
factor_code         VARCHAR(64) (e.g. HIGH_VELOCITY, LARGE_AMOUNT_DEVIATION)
factor_label        VARCHAR(255) (human-readable title)
severity            VARCHAR(16) CHECK (severity IN ('INFO','LOW','MEDIUM','HIGH','CRITICAL'))
description         TEXT (detailed contextual narrative)
value_numeric       NUMERIC(18,6) (optional quantitative metric)
value_text          TEXT (optional textual identifier)
evidence            JSONB (structured supporting metadata dictionary)
created_at          TIMESTAMPTZ DEFAULT now()
```

Phase 8 implements 9 standardized factor codes: `COLD_START_ACCOUNT`, `HIGH_VELOCITY`, `LARGE_AMOUNT_DEVIATION`, `NEW_DEVICE`, `NEW_LOCATION`, `UNUSUAL_TIME`, `BEHAVIORAL_SHIFT`, `NEW_MERCHANT`, `NEW_CATEGORY`.

---

# 21. Investigation Model (Phase 9 Implemented)

Investigations represent formal operational review cases created around flagged or suspicious transactions.

### 21.1 Investigation Entity (`investigations`)

Operational fields and types:

```text
id                  UUID PRIMARY KEY
assigned_to         UUID REFERENCES users(id) ON DELETE RESTRICT (nullable)
status              VARCHAR(32) NOT NULL DEFAULT 'OPEN'
priority            VARCHAR(16) NOT NULL DEFAULT 'MEDIUM'
resolution          VARCHAR(32) (nullable)
resolution_notes    TEXT (nullable)
created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
```

Operational Enums and Constraints:
- `status`: `OPEN`, `UNDER_REVIEW`, `RESOLVED` (`chk_investigations_status`).
- `priority`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` (`chk_investigations_priority`).
- `resolution`: `LEGITIMATE`, `SUSPICIOUS`, `CONFIRMED_FRAUD`, `INCONCLUSIVE` (`chk_investigations_resolution`).
- Resolution State Integrity (`chk_investigations_resolution_state`): When `status = 'RESOLVED'`, `resolution` and non-whitespace `resolution_notes` are mandatory. Conversely, when `status != 'RESOLVED'`, `resolution` and `resolution_notes` must remain `NULL`.
- Indexes: `ix_investigations_status_priority` on `(status, priority)`, `ix_investigations_assigned_status` on `(assigned_to, status)`, `ix_investigations_created_at` on `created_at DESC`.

### 21.2 Investigation Transaction Association (`investigation_transactions`)

Enables many-to-many associations between investigations and transactions:

```text
investigation_id    UUID REFERENCES investigations(id) ON DELETE RESTRICT
transaction_id      UUID REFERENCES transactions(id) ON DELETE RESTRICT
relationship_type   VARCHAR(32) NOT NULL ('PRIMARY' or 'RELATED')
created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
PRIMARY KEY (investigation_id, transaction_id)
```

Invariants and Scope Rules:
1. **Primary Transaction Invariant:**
   - PostgreSQL partial unique index `uq_investigation_single_primary` on `(investigation_id) WHERE relationship_type = 'PRIMARY'` guarantees **at most one** `PRIMARY` association per investigation in the database.
   - The application-level atomic creation workflow (`InvestigationService.create_investigation`) guarantees **exactly one** `PRIMARY` association for every successfully committed investigation.
   - A single transaction can serve as the `PRIMARY` subject across multiple separate investigations.
2. **1-Hop Related Transaction Scope:**
   - Related transactions are limited strictly to direct 1-hop associations sharing the exact same `source_namespace` as the primary transaction.
   - Must satisfy at least one of four shared-party matching conditions:
     - `related.account_id = primary.account_id`
     - `related.account_id = primary.counterparty_account_id`
     - `related.counterparty_account_id = primary.account_id`
     - `related.counterparty_account_id = primary.counterparty_account_id`
   - Recursive graph search or multi-hop discovery is intentionally excluded.

---

# 22. Investigation Evidence (Phase 9 Implemented)

Evidence represents structured, immutable snapshots captured to substantiate an investigation.

### 22.1 Schema (`investigation_evidence`)

```text
id                  UUID PRIMARY KEY
investigation_id    UUID REFERENCES investigations(id) ON DELETE RESTRICT NOT NULL
evidence_type       VARCHAR(64) NOT NULL
source_type         VARCHAR(64) NOT NULL
source_id           UUID (nullable)
title               VARCHAR(255) NOT NULL
description         TEXT (nullable)
payload             JSONB (nullable, max 64 KB)
created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
```

### 22.2 Evidence Constraints & Immutability Trigger

1. **Type & Source Pairings (`chk_inv_evidence_type_source_pair`):**
   - `TRANSACTION_FACT` <-> `TRANSACTION`
   - `RISK_SCORE` <-> `RISK_ANALYSIS`
   - `RISK_FACTOR` <-> `RISK_FACTOR`
   - `ACCOUNT_PROFILE` <-> `ACCOUNT`
   - `DEVICE_PROFILE` <-> `DEVICE`
   - `USER_NOTE` <-> `USER_NOTE`
2. **Source ID Consistency (`chk_inv_evidence_source_consistency`):**
   - If `source_type = 'USER_NOTE'`, `source_id` MUST be `NULL`.
   - If `source_type != 'USER_NOTE'`, `source_id` MUST be non-null and point to an existing entity in the current investigation scope.
3. **Database-Enforced Immutability Trigger:**
   - Table deliberately omits `updated_at`.
   - PostgreSQL trigger `trg_no_update_delete_evidence` invokes `trg_enforce_evidence_immutability()` to reject standard SQL `UPDATE` and `DELETE` statements on `investigation_evidence`.
   - *Boundary Note:* Does not protect against privileged superusers executing `TRUNCATE` or disabling triggers.
4. **Ordering & Indexing:**
   - `ix_inv_evidence_investigation_created` on `(investigation_id, created_at ASC, id ASC)` provides deterministic pagination.
   - `ix_inv_evidence_source` on `(source_type, source_id)` optimizes reverse lookup.

---

# 23. AI Summary Storage (Phase 10 Implemented)

AI-generated investigation summaries are stored in the `ai_summaries` table (Alembic migration `0007_ai_models.py`), retaining complete provenance and lifecycle auditability separate from investigation evidence snapshots.

### 23.1 Relational Schema (`ai_summaries`)

| Column | Type | Nullable | Default | Description |
|---|---|:---:|---|---|
| `id` | UUID | No | `uuid4()` | Primary key |
| `investigation_id` | UUID | No | — | Foreign key to `investigations.id` (`ON DELETE RESTRICT`) |
| `provider` | VARCHAR(64) | No | — | Provider identifier (`mock`, etc.) |
| `model` | VARCHAR(128) | No | — | Model version string (`mock-v1`) |
| `prompt_version` | VARCHAR(64) | No | — | Prompt template version identifier (`pv_1.0`) |
| `evidence_hash` | VARCHAR(64) | No | — | Authoritative SHA-256 fingerprint over complete case context & account standing |
| `context_hash` | VARCHAR(64) | No | — | SHA-256 fingerprint over budget-bounded prompt payload |
| `generation_token` | UUID | No | — | Lease token for compare-and-swap (CAS) fencing |
| `status` | VARCHAR(32) | No | `'PENDING'` | Lifecycle state: `PENDING`, `COMPLETED`, or `FAILED` |
| `summary` | JSONB | Yes | `NULL` | Structured `AISummaryOutput` payload (`JSONB(none_as_null=True)`) |
| `error_message` | TEXT | Yes | `NULL` | Upstream provider, timeout, or grounding validation failure details |
| `generated_at` | TIMESTAMPTZ | No | — | Timestamp when generation attempt was initiated |
| `completed_at` | TIMESTAMPTZ | Yes | `NULL` | Timestamp when attempt reached terminal state (`COMPLETED` or `FAILED`) |
| `created_at` | TIMESTAMPTZ | No | `now()` | Record insertion timestamp |

### 23.2 Schema Invariants & Database Constraints
1. **Lifecycle Check Constraint (`chk_ai_summaries_lifecycle_state`):**
   ```sql
   CHECK (
       (status = 'PENDING' AND completed_at IS NULL AND summary IS NULL AND error_message IS NULL) OR
       (status = 'COMPLETED' AND completed_at IS NOT NULL AND summary IS NOT NULL AND error_message IS NULL) OR
       (status = 'FAILED' AND completed_at IS NOT NULL AND summary IS NULL AND error_message IS NOT NULL)
   )
   ```
2. **Status Enum Check Constraint (`chk_ai_summaries_status`):**
   ```sql
   CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED'))
   ```
3. **Partial Unique Index (`uq_ai_summaries_one_pending_per_investigation`):**
   ```sql
   CREATE UNIQUE INDEX uq_ai_summaries_one_pending_per_investigation
   ON ai_summaries (investigation_id)
   WHERE status = 'PENDING';
   ```
   Guarantees at the database engine level that no two concurrent workers can execute active generations simultaneously for the same investigation.
4. **Deterministic Retrieval Index (`ix_ai_summaries_investigation_created`):**
   Composite index on `(investigation_id, created_at DESC, id)` optimizing chronological history retrieval and latest-summary queries.
5. **Referential Integrity & Retention (`ON DELETE RESTRICT`):**
   Deleting an investigation with attached AI summary history is blocked by foreign key constraint `fk_ai_summaries_investigation_id`. In the ORM, `Investigation.ai_summaries` is mapped with `passive_deletes="all"` to avoid emitting speculative nullifying queries.

---

# 24. Data Ingestion Architecture

The ingestion pipeline should follow:

```text
CSV Upload
    |
    v
File Validation
    |
    v
Schema Validation
    |
    v
Record Validation
    |
    v
Data Quality Report
    |
    v
Cleaning / Normalization
    |
    v
Enrichment
    |
    v
Persistence
```

Invalid records should be handled according to documented ingestion policy.

---

# 25. Ingestion Requirements

The ingestion system must:

1. Validate file format.
2. Validate required columns.
3. Validate data types.
4. Validate required values.
5. Validate identifiers.
6. Validate foreign-key references.
7. Detect duplicate transaction IDs.
8. Validate timestamps.
9. Validate monetary values.
10. Produce data-quality results.
11. Prevent invalid data from silently entering the production dataset.
12. Handle contextual metadata divergence per ADR-065 Decision A: preserve immutable canonical records, record `MATCHED_EXISTING` with `row_hash` provenance, and isolate material conflicts strictly to core fields.
13. Enforce namespace-scoped perpetual completed-file deduplication under transaction-scoped composite advisory locks per ADR-065 Decision C (`(source_namespace, file_hash)`), reserving reprocessing as an exceptional, auditable administrative action.
14. Pre-condition on reference entities: Reference entities (`locations`, `merchants`, `devices`, `accounts`) must be generated and populated before transaction ingestion can validate foreign references.
15. Account and dataset-import namespace migration dependency (ADR-065 Decision D): Enforce namespace-scoped account resolution using `(source_namespace, external_account_id)` with verified transaction-account namespace consistency. An approved Alembic migration adding `source_namespace` to `accounts` and `dataset_imports` with a unique constraint `UNIQUE (source_namespace, external_account_id)` when non-null, accompanied by staged migration preflight, duplicate checks, conditional reconciliation, and layered consistency enforcement (Option C3), is an explicit prerequisite (Checkpoint P4.0) before reference-entity account generation (Checkpoint P4.1) and transaction ingestion (Checkpoint P4.4) are operationalized.

---

# 26. Data Quality Reporting

The ingestion process should report:

- Total records received
- Valid records
- Invalid records
- Duplicate records
- Missing fields
- Invalid values
- Invalid references
- Cleaning operations performed
- Records rejected

The system should make the difference between:

```text
Rejected
Cleaned
Accepted
```

clear to the user.

---

# 27. Data Processing Pipeline

The processing pipeline should conceptually be:

```text
Raw
 |
 v
Validate
 |
 v
Clean
 |
 v
Normalize
 |
 v
Enrich
 |
 v
Feature Engineering
 |
 v
Analytics / ML
```

Each stage should have a defined contract.

---

# 28. Feature Engineering Requirements

Feature engineering must respect temporal ordering.

For transaction `T` at time `t`:

```text
Features(T) = f(history <= t)
```

Future information must not be used.

Where a feature is explicitly historical, it should use only information available before the prediction/evaluation point.

---

# 29. Behavioral Feature Categories

The initial feature pipeline should support:

### Amount Features

- Historical mean
- Historical median
- Amount deviation
- Z-score
- Percentile

### Velocity Features

- Transactions in 5 minutes
- Transactions in 1 hour
- Transactions in 24 hours

### Merchant Features

- Merchant frequency
- New merchant indicator
- Merchant spending deviation

### Device Features

- Known device indicator
- New device indicator
- Device frequency

### Location Features

- Known location indicator
- New location indicator
- Location frequency

### Temporal Features

- Hour
- Day of week
- Weekend
- Unusual hour

### Category Features

- Category frequency
- Category spending deviation
- New category

---

# 30. Financial Analytics Requirements

Financial analytics are implemented as an independent, deterministic domain module inside the modular monolith (`src/finsignal/analytics/`), providing database-backed financial intelligence without coupling to ML scoring pipelines.

### 30.1 Module Architecture and Boundaries

```text
HTTP Request
     │
     ▼
FastAPI Router (src/finsignal/api/v1/analytics.py)
     │  ├── JWT Authentication
     │  └── Role Authorization (ADMIN, ANALYST, INVESTIGATOR)
     ▼
Analytics Service (src/finsignal/analytics/service.py)
     │  ├── Input Validation (Regex, IANA Timezones, Bounds)
     │  ├── Namespace Verification (accounts/dataset_imports)
     │  ├── Bucket-Count Boundary Enforcement
     │  ├── Authoritative Account Namespace Derivation
     │  └── Decimal Percentage Calculations (ROUND_HALF_UP)
     ▼
Analytics Repository (src/finsignal/analytics/repository.py)
     │  ├── Dynamic SQL Parameterized Query Assembly
     │  ├── PostgreSQL Single-Roundtrip Window Aggregations
     │  ├── Wall-Clock generate_series & AT TIME ZONE Projections
     │  └── Continuous Median Calculations (percentile_cont)
     ▼
PostgreSQL Database (transactions, accounts, merchants)
```

### 30.2 Request Validation and Domain Schemas
- **Validation Strictness:** All responses use strict Pydantic v2 models with `extra="forbid"`.
- **Monetary Precision:** Monetary values are modeled as `MoneyStr` (`"0.00"`) and `OptionalMoneyStr`, serialized via `ROUND_HALF_UP` from Python `Decimal` or PostgreSQL `NUMERIC(18,2)`. Binary floating-point representation for currency amounts is strictly prohibited.
- **Reporting Windows:** Time intervals are strictly half-open: `[from_time, to_time)`. When both timestamps are provided, `from_time < to_time` is strictly enforced.
- **Trend Interval & Bucket Limits:**
  - `interval` must be `'day'` or `'month'`.
  - Enforces `count_calendar_buckets()` in the target timezone before query execution:
    - Daily trends: maximum 366 buckets (`MAX_DAILY_BUCKETS`).
    - Monthly trends: maximum 120 buckets (`MAX_MONTHLY_BUCKETS`).
- **Namespace Syntax & Isolation:**
  - Validates namespace syntax against `^[A-Z0-9_]{3,64}$`.
  - Verifies namespace existence against `accounts` or `dataset_imports`, raising HTTP 404 (`NAMESPACE_NOT_FOUND`) if nonexistent.
  - For account-specific routes (`/accounts/{id}` and `/accounts/{id}/unusual-spending`), the source namespace is authoritatively derived from the persisted `Account.source_namespace`, preventing cross-namespace tampering or caller spoofing.
- **Deterministic Outlier Detection:**
  - Median debit amount $M_{\text{debit}}$ is calculated across all debits in the requested reporting window using continuous median (`percentile_cont(0.5)`).
  - Outlier threshold: $\text{threshold} = \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$.
  - Outlier condition: `amount >= :threshold` (inclusive).
  - Multiplier bounded between 1.5 and 10.0 (default 3.0).
  - Total pre-pagination outlier count is computed before applying `limit` and `offset`.

### 30.3 Multi-Currency and Inactive Account Semantics
- Existing accounts with no transaction activity in the requested currency return HTTP 200 with zeroed financial summary metrics and the full list of `available_currencies` transacted by that account in its namespace.
- If the account itself does not exist in the database, HTTP 404 (`RESOURCE_NOT_FOUND`) is returned.

---

# 31. ML Architecture

The initial ML architecture should remain inside the Python backend.

Conceptually:

```text
Transaction Data
      |
      v
Feature Engineering
      |
      v
Feature Matrix
      |
      v
Anomaly Model
      |
      v
Anomaly Score
      |
      v
Risk Mapping
      |
      v
Risk Analysis
```

A separate ML microservice is not required for the initial version.

---

# 32. Initial ML Model

Isolation Forest is the preferred initial anomaly-detection baseline.

Reasons:

- Suitable for anomaly detection
- Available in scikit-learn
- Does not require fully labeled training data
- Can work with multidimensional behavioral features
- Provides a strong baseline for experimentation

The model should not be treated as the final fraud classifier.

---

# 33. Hybrid Detection

The initial risk system should combine:

```text
Deterministic Signals
        +
ML Anomaly Detection
        |
        v
Risk Analysis
```

Rules provide interpretable evidence.

ML provides detection of less-obvious behavioral combinations.

The exact score-combination strategy belongs in `ML_DESIGN.md`.

---

# 34. Model Versioning & Lifecycle Registry

Every trained model and subsequent risk assessment is tracked in PostgreSQL via `model_versions` (migration `0004_model_versions.py`):
- **Family & Version Identity:** Indexed by family `name` (e.g. `transaction_anomaly_isolation_forest`) and semantic `version` (e.g. `1.0.0`), enforced by unique constraint `uq_model_versions_name_version`.
- **Feature Contract:** Bound to `feature_version = "v1.0"`.
- **Dataset Link:** Bound to `dataset_version_id REFERENCES dataset_versions(id) ON DELETE RESTRICT`.
- **Artifact Security:** Stores relative path `artifact_uri` and hexadecimal `artifact_hash` (SHA-256) for pre-load integrity verification.
- **Lifecycle State Machine:**
  - `EXPERIMENTAL -> VALIDATED, RETIRED`
  - `VALIDATED -> ACTIVE (via promote_to_active), RETIRED`
  - `ACTIVE -> RETIRED`
  - `RETIRED -> (terminal)`
- **Concurrency & Promotion:** Active model resolution queries PostgreSQL dynamically on each scoring call. Promotion uses `SELECT ... FOR UPDATE` row locks to retire the existing active model and activate the candidate within a single transaction, enforced by partial unique index `uq_model_versions_active_family`.

---

# 35. ML Training Requirements

Training pipelines must:

- Use approved feature sets.
- Exclude ground-truth leakage.
- Respect temporal splits.
- Record configuration.
- Record model version.
- Record feature definitions.
- Produce evaluation metrics.
- Support reproducibility.

---

# 36. ML Evaluation

Primary evaluation metrics should include:

- Precision
- Recall
- F1
- PR-AUC
- False-positive rate
- False-negative rate
- Alert volume
- Scenario-level detection
- Account-level detection

Accuracy must not be treated as the primary success metric because fraud is intentionally imbalanced.

---

# 37. Model Evaluation Dataset

The evaluation process should use time-aware data splits.

Example:

```text
Training:
January - June

Validation:
July - August

Testing:
September
```

The exact period will be determined by the generated dataset.

---

# 38. Investigation Triggering & Creation (Phase 9 Implemented)

FinSignal implements a manual-first investigation creation model in Phase 9.

### 38.1 Manual Case Creation Workflow
- Authenticated users with `ADMIN`, `ANALYST`, or `INVESTIGATOR` roles can explicitly initiate an investigation on any valid transaction.
- Creation requires:
  - Valid `transaction_id`.
  - Triage `priority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
  - Optional initial notes.
- Upon creation, the case enters the unassigned queue (`assigned_to = NULL`, `status = 'OPEN'`).

### 38.2 Deferred Automated Triggering
Conceptual automated threshold triggering remains defined as a future capability:

```text
Risk Score / Tier
    |
    +---- Low --------> Normal Processing (No Investigation)
    +---- Medium -----> Flagged for Optional Manual Review
    +---- High -------> Investigation Candidate (Future Auto-Trigger Target)
    +---- Critical ---> Immediate Escalation (Future Auto-Trigger Target)
```

Automated case creation based on configured risk score thresholds or alert triggers is intentionally deferred to future operational phases to prevent alert fatigue prior to operational baseline establishment. Risk scores alone do not constitute proof of fraud.

---

# 39. Evidence Assembly

When an investigation is created, the system should assemble relevant evidence.

Potential sources:

- Transaction details
- Account history
- Behavioral statistics
- Similar transactions
- Merchant history
- Device history
- Location history
- Velocity
- Risk factors
- Model output

Evidence generation should be deterministic where possible.

---

# 40. AI Integration

The AI layer should be provider-agnostic.

The application should use an abstraction similar to:

```text
Investigation Evidence
        |
        v
AI Provider Interface
        |
        +---- Provider A
        |
        +---- Provider B
        |
        +---- Future Provider
```

The core investigation system should not be tightly coupled to one LLM vendor.

---

# 41. AI Input Contract

The LLM should receive structured investigation context rather than unrestricted database access.

Conceptually:

```json
{
  "transaction": {},
  "account_context": {},
  "risk_analysis": {},
  "risk_factors": [],
  "related_transactions": [],
  "behavioral_summary": {}
}
```

The exact schema will be defined later.

---

# 42. AI Output Requirements

AI output should:

- Summarize evidence
- Explain important signals
- Mention relevant historical comparisons
- Identify uncertainty
- Avoid unsupported claims
- Preserve numerical facts

The output should not modify source evidence.

---

# 43. AI Guardrails

The AI integration must prevent:

- Unsupported factual claims
- Fabricated transactions
- Fabricated evidence
- Risk-score modification
- Autonomous fraud decisions
- Hidden access to unrelated user data

The final investigation decision remains human-controlled.

---

# 44. Background Processing

The initial system should prefer synchronous processing for operations that can reasonably complete within normal API request limits.

Background processing should be introduced only for tasks that are:

- Long-running
- Resource-intensive
- Failure-prone
- Not appropriate for request/response execution

Potential future infrastructure:

```text
Celery + Redis
```

This is not required for the initial MVP.

---

# 45. Real-Time Processing

Real-time streaming is explicitly deferred.

The initial architecture will not require Kafka.

Future real-time architecture may become:

```text
Transaction Stream
       |
       v
Kafka
       |
       v
Feature Processing
       |
       v
Risk Detection
       |
       v
Alerting
```

This should only be introduced if the product scope later requires real-time transaction monitoring.

---

# 46. Caching

Caching should not be introduced prematurely.

PostgreSQL should remain the authoritative source.

A cache such as Redis may be introduced later for:

- Frequently accessed analytics
- Session-related workloads if required
- Background job infrastructure
- Expensive repeated computations

---

# 47. API Documentation

FastAPI's generated OpenAPI documentation should be enabled for development.

The project should provide:

```text
/docs
/redoc
```

in development environments.

Production exposure should be controlled according to security requirements.

---

# 48. Error Handling

The API should provide consistent error responses.

Conceptual format:

```json
{
  "error": {
    "code": "INVALID_TRANSACTION_DATA",
    "message": "Transaction amount must be positive.",
    "details": {}
  }
}
```

Errors should:

- Use appropriate HTTP status codes.
- Avoid leaking internal implementation details.
- Provide actionable messages where appropriate.
- Use stable application error codes.

---

# 49. Logging

The application should use structured logging where practical.

Logs should capture:

- Request context
- Important processing events
- Authentication failures
- Dataset processing failures
- ML processing failures
- Investigation operations
- Unexpected exceptions

Sensitive information must not be logged.

---

# 50. Configuration Management

Configuration must be environment-based.

Potential configuration categories:

```text
DATABASE_URL
JWT_SECRET
JWT_EXPIRATION
APPLICATION_ENV
LOG_LEVEL
AI_PROVIDER
AI_MODEL
MODEL_STORAGE_PATH
```

Secrets must not be committed to Git.

A `.env.example` file should document required configuration without exposing real secrets.

---

# 51. Environment Separation

At minimum, the system should distinguish:

```text
development
testing
production
```

Environment-specific configuration should not be hard-coded into application logic.

---

# 52. Docker Requirements

The project will provide Docker configuration suitable for local development and production deployment, scheduled for Phase 13 per accepted ADR-061 and ADR-073.

Initial services:

```text
postgres
backend
frontend
```

The exact Compose configuration will be defined during implementation.

---

# 53. Database Persistence

Database data should survive container restarts through Docker volumes during local development.

The application should not depend on container-local database state.

---

# 54. Data Import Storage

Uploaded datasets should not be treated as permanent raw files by default.

The ingestion design should define:

- Temporary upload storage
- Validation
- Processing
- Persistence
- Cleanup

The exact storage mechanism will be finalized during architecture design.

---

# 55. File Size and Upload Limits

Dataset uploads should have configurable limits.

The system should reject files that exceed configured limits.

Limits should be selected based on the MVP dataset scale rather than assuming unrestricted uploads.

---

# 56. Pagination

Large API collections must use pagination.

Potential resources requiring pagination:

- Transactions
- Accounts
- Merchants
- Risk analyses
- Investigations
- Evidence
- Audit records

The exact pagination strategy will be documented in `API_GUIDELINES.md`.

---

# 57. Sorting and Filtering

Collection endpoints should support controlled filtering and sorting where appropriate.

Examples:

```text
transaction date range
account
merchant
category
risk level
investigation status
investigation resolution
```

Filtering should use indexed database fields where appropriate.

---

# 58. Database Indexing

Indexes should be created based on access patterns.

Likely indexed fields include:

- Transaction account ID
- Transaction timestamp
- Transaction ID
- Merchant ID
- Device ID
- Location ID
- Risk analysis transaction ID
- Investigation transaction ID
- Investigation status

Composite indexes may be used where query patterns justify them.

Indexes should not be added indiscriminately.

---

# 59. Transaction Ordering

Financial transaction queries that are used for historical behavior should have deterministic ordering.

Where timestamps can be equal, a stable secondary key such as transaction ID should be used.

Conceptually:

```text
ORDER BY timestamp ASC, transaction_id ASC
```

This is important for reproducibility and temporal feature generation.

---

# 60. Concurrency Requirements

The system should protect against inconsistent concurrent updates to investigations and other mutable application state.

Potential concurrency-sensitive operations include:

- Investigation resolution
- Investigation status updates
- Dataset processing state
- Model analysis jobs

The exact transaction/isolation strategy will be defined in `DATABASE_DESIGN.md`.

---

# 61. Auditability

Important user actions should be auditable.

Potential events:

- Login
- Dataset import
- Risk analysis execution
- Investigation creation
- Investigation update
- Investigation resolution (`INVESTIGATION_RESOLVED`)
- AI summary generation (`AI_SUMMARY_GENERATED`)
- AI summary recovery / failure (`AI_SUMMARY_FAILED`)

The audit implementation will be finalized in the architecture and security documentation.

---

# 62. Security Requirements

The implementation must:

- Hash passwords securely.
- Protect JWT signing secrets.
- Validate authorization on protected endpoints.
- Validate all user input.
- Prevent SQL injection through parameterized data access.
- Prevent unsafe file processing.
- Restrict access to investigations based on authorization.
- Avoid exposing ground truth.
- Avoid leaking secrets through logs.
- Protect AI provider credentials.

Detailed security requirements belong in `SECURITY.md`.

---

# 63. Testing Requirements

The project must use multiple testing layers.

## Unit Tests

Test:

- Domain logic
- Validators
- Feature calculations
- Risk-factor calculations
- Utility functions

## Integration Tests

Test:

- Database repositories
- Service/database interaction
- Authentication flows
- API endpoints

## ML Tests

Test:

- Feature consistency
- Leakage prevention
- Deterministic preprocessing
- Model training
- Metric calculations

## End-to-End Tests

Validate important product workflows.

Example:

```text
Login
  |
  v
Upload Dataset
  |
  v
Validate
  |
  v
Analyze
  |
  v
Flag Transaction
  |
  v
Create Investigation
  |
  v
Generate Summary
  |
  v
Resolve Investigation
```

---

# 64. Test Data

Tests should use small deterministic datasets.

Production-scale datasets should not be required for every test.

A dedicated test fixture strategy should exist for:

- Accounts
- Transactions
- Fraud scenarios
- Risk analyses
- Investigations

---

# 65. Code Quality

The project should enforce consistent Python code quality.

Recommended tooling may include:

- Ruff
- Formatting checks
- Type checking
- Import checks

The exact tool configuration will be finalized during implementation.

---

# 66. Type Safety

Python type hints should be used throughout application code where practical.

Public functions, service interfaces, data structures, and API schemas should have explicit types.

Type checking may be introduced using a tool such as:

```text
mypy
```

or an equivalent modern Python type checker.

---

# 67. API Schema Validation

Pydantic models should define API request and response schemas.

The application should avoid returning raw database models directly from API endpoints.

API schemas should explicitly define:

- Input fields
- Output fields
- Optional fields
- Validation rules
- Serialization behavior

---

# 68. Repository Requirements

Database access should be isolated from service logic.

Repositories should handle:

- Queries
- Persistence
- Retrieval
- Filtering
- Pagination

Business rules should remain in service/domain layers rather than repository implementations.

---

# 69. Service Requirements

Services should coordinate business workflows and domain invariants.

Examples:

```text
TransactionService
RiskAnalysisService
InvestigationService
DatasetService
AnalyticsService
AuthService
```

Services should not become uncontrolled collections of unrelated logic.

### 69.1 InvestigationService & InvestigationRepository (Phase 9 Implemented)

The `Investigation` domain cleanly separates persistence from business and authorization workflows:

1. **`InvestigationRepository` Responsibilities:**
   - Eager joins and single bounded queries to eliminate N+1 query patterns (e.g., retrieving primary transaction metadata, latest risk analysis score, and audit history in a single structured workspace query).
   - Row-level lock acquisition using PostgreSQL `SELECT ... FOR UPDATE` during assignment, unassignment, priority change, and resolution mutations.
   - Deterministic pagination queries for shared queues (`created_at DESC`) and evidence lists (`created_at ASC, id ASC`).
   - Standard transactional persistence for entities and relation links.

2. **`InvestigationService` Responsibilities:**
   - Enforce multi-model transactional atomicity: atomically persisting the `Investigation`, the primary `InvestigationTransaction`, and the initial `AuditEvent(INVESTIGATION_CREATED)` in a single uncommitted transaction.
   - Enforce RBAC rules across roles:
     - `ADMIN`: Global lifecycle, assignment, linking, attachment, and resolution authority.
     - `INVESTIGATOR`: Permitted to view all cases, self-assign unassigned cases, self-unassign, edit assigned cases, link 1-hop transactions, attach evidence, and resolve. Explicitly prohibited from taking peer cases (403) or reassigning across peers (403).
     - `ANALYST`: Permitted to create unassigned cases and read workspace/transactions/evidence; prohibited from mutations, assignment, transaction linking, evidence attachment, and resolution (403).
   - Guard terminal state immutability: reject any modification or evidence attachment attempt on `RESOLVED` cases with 409 `IMMUTABLE_INVESTIGATION`.
   - Validate 1-hop related transaction eligibility: verify shared `source_namespace` and test the 4-way shared-party predicate before linking.
   - Enforce evidence type and source validation matrix and bound payload sizes to 64 KB.

### 69.2 AISummaryService & AISummaryRepository (Phase 10 Implemented)

The `src/finsignal/ai/` domain separates persistence from LLM orchestration, fingerprinting, and grounding validation:

1. **`AISummaryRepository` Responsibilities:**
   - Manage persistence of `AISummary` records and handle partial unique index conflict translation (`AI_SUMMARY_IN_PROGRESS`).
   - Execute conditional CAS state transitions:
     ```python
     update(AISummary).where(
         AISummary.id == summary_id,
         AISummary.status == "PENDING",
         AISummary.generation_token == token,
     ).values(...)
     ```
   - Execute lazy expired pending recovery (`recover_expired_pending`), atomically transitioning timed-out attempts to `FAILED` with generation token rotation and staging an `AI_SUMMARY_FAILED` audit event when `rowcount == 1`.
   - Provide deterministic pagination for summary history (`created_at DESC, id DESC`).

2. **`AISummaryService` Responsibilities:**
   - Coordinate the two-transaction lifecycle under `REPEATABLE READ` snapshot isolation, with exponential backoff retries for SQLSTATE `40001`.
   - Enforce RBAC access policies:
     - `ADMIN`: Global generation and retrieval permissions across all cases.
     - `INVESTIGATOR`: Permitted to generate and view summaries for cases assigned to themselves; accessing unassigned or peer-assigned cases returns 403 `FORBIDDEN`.
     - `ANALYST`: Permitted to retrieve summaries (`GET /ai-summary` and `/history`); generation attempts return 403 `FORBIDDEN`.
   - Guard terminal state: reject generation on `RESOLVED` or `CLOSED` cases with 409 `INVESTIGATION_ALREADY_RESOLVED`.
   - Coordinate authoritative evidence hashing, bounded prompt context assembly, and dynamic staleness detection.
   - Enforce strict two-stage output validation: Pydantic structural validation (`AISummaryOutput`) followed by citation existence grounding validation.
   - Execute provider generation strictly outside database transactions.

---

# 70. ML Service Boundary

ML-related logic should have a clear boundary from API routing.

Conceptually:

```text
Risk API
   |
   v
Risk Service
   |
   v
Feature Service
   |
   v
ML Model
```

This makes it possible to replace or compare models without rewriting API code.

---

# 71. Model Artifact Management

Initial model artifacts may be stored using a controlled local/object-storage-compatible mechanism.

The system should associate:

- Model version
- Training configuration
- Feature version
- Dataset version
- Training timestamp

Advanced experiment tracking such as MLflow is deferred until justified.

---

# 72. Performance Requirements

The MVP should prioritize correctness over premature optimization.

The system should nevertheless be designed to:

- Process the development dataset reliably.
- Handle approximately 250,000 transactions in the target dataset.
- Avoid loading unnecessarily large datasets into memory for every API request.
- Use database pagination.
- Use batch processing for large ingestion operations.
- Avoid repeated expensive calculations where persistence or caching is justified.

Exact performance targets will be established after profiling.

---

# 73. Batch Processing

Large dataset operations should use batch processing where appropriate.

Potential batch operations:

- Transaction ingestion
- Data cleaning
- Feature generation
- Risk analysis
- Dataset export

The batch size should be configurable.

---

# 74. Analytics Computation

Analytics are executed via database-level SQL aggregations using async SQLAlchemy and raw parameterized PostgreSQL queries (`AnalyticsRepository`). This approach avoids large in-memory dataset transfers to Python and leverages PostgreSQL's query optimizer and index structures.

### 74.1 Query Techniques
1. **Single-Roundtrip Macro Aggregations:** Aggregates volume, directional counts, sums, min/max, directional averages, and continuous medians (`percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)`) in a single SQL statement.
2. **Wall-Clock Trend Series Generation:** Generates zero-filled continuous series using wall-clock bounds:
   ```sql
   generate_series(
       date_trunc(:interval, :from_time, :tz) AT TIME ZONE :tz,
       date_trunc(:interval, :to_time, :tz) AT TIME ZONE :tz,
       '1 day'::interval
   )
   ```
   joined against transactions projected to the same timezone `date_trunc(:interval, occurred_at, :tz)`. This ensures daylight saving transitions (e.g., 23-hour spring-forward days) and midnight boundaries remain robust regardless of the database connection's session timezone.
3. **Dynamic Where Conditions:** Query predicates are constructed dynamically to pass only populated filters, preventing untyped parameter errors in asyncpg prepared statements and maximizing index scan pruning.

### 74.2 Empirical Performance and Documented Limitations

The Phase 5 implementation was evaluated under the approved benchmarking protocol:
- **Medium Scale (100 accounts, 5,000 transactions, seed=42):**
  - `/overview`: P50 = 0.48 ms, P95 = 0.81 ms (Budget: $\le 50.0\text{ ms}$ — **MET**).
  - `/trends`: P50 = 1.14 ms, P95 = 1.53 ms (Budget: $\le 50.0\text{ ms}$ — **MET**).
- **Full Scale (5,000 accounts, 250,000 transactions, seed=42, 80,651 matching window rows):**
  - `/categories`: Repo P95 = 85.72 ms (Budget: $\le 100\text{ ms}$ — **MET**).
  - `/merchants`: Repo P95 = 83.06 ms (Budget: $\le 100\text{ ms}$ — **MET**).
  - `/accounts/{id}`: Repo P95 = 1.25 ms (Budget: $\le 100\text{ ms}$ — **MET**).
  - `/accounts/{id}/unusual-spending`: Repo P95 = 0.54 ms (Budget: $\le 100\text{ ms}$ — **MET**).
  - `/overview`: Repo P95 = 135.74 ms; HTTP P95 = 145.3 ms (Budget: $\le 100\text{ ms}$ — **EXCEEDED**).
  - `/trends`: Repo P95 = 140.16 ms; HTTP P95 = 148.1 ms (Budget: $\le 100\text{ ms}$ — **EXCEEDED**).
- **Query Plan Findings:**
  - `EXPLAIN (ANALYZE, BUFFERS)` confirms that PostgreSQL uses `Index Scan using ix_transactions_occurred_at`, reading 80,651 rows in 28.02 ms with 2,351 shared buffer hits and 0 sequential scans.
  - The remaining ~100 ms is consumed by in-engine memory sorting and CPU aggregation required for continuous `percentile_cont(0.5)` over 80k decimal rows and hash grouping.
  - Adding composite indexes would not improve performance because row filtering is already index-driven (28 ms). Introducing precomputed rollup tables or background materialization is deferred to future optimization phases.

---

# 75. ML Feature Storage

Feature storage strategy should be selected based on actual requirements.

The initial system may compute features during analysis rather than persisting every feature indefinitely.

If feature persistence is required, the feature schema must be versioned.

---

# 76. Data Lineage

Important derived outputs should be traceable to:

```text
Dataset
   |
   v
Processing Version
   |
   v
Feature Version
   |
   v
Model Version
   |
   v
Risk Analysis
   |
   v
Investigation
```

This allows results to be understood and reproduced.

---

# 77. Model and Dataset Compatibility

A model must not be used with incompatible feature definitions.

A risk-analysis execution should verify compatibility between:

- Dataset version
- Feature version
- Model version

where such metadata is available.

---

# 78. Frontend Integration Requirements

The backend must provide APIs sufficient for the future React frontend to implement:

- Authentication
- Dashboard analytics
- Transaction browsing
- Risk/alert browsing
- Investigation detail
- Evidence viewing
- AI summary viewing
- Investigation resolution

The backend should not depend on frontend-specific implementation details.

---

# 79. API Response Design

Responses should be designed for frontend consumption while preserving domain clarity.

Large nested payloads should be avoided when they cause unnecessary data transfer.

Complex investigation views may use dedicated aggregation endpoints rather than forcing the frontend to make excessive requests.

---

# 80. Health and Readiness

The backend should expose appropriate operational endpoints.

Potential endpoints:

```text
/health
/ready
```

Health checks should distinguish between:

- Application process health
- Dependency readiness

The exact implementation will be finalized later.

---

# 81. Deployment Model

The initial deployment architecture should support:

```text
React Frontend
       |
       v
FastAPI Backend
       |
       v
PostgreSQL
```

Docker should be used for reproducible local development.

Cloud deployment details will be addressed after the core system is implemented and tested.

---

# 82. Deferred Infrastructure

The following infrastructure is intentionally not required for MVP:

- Kafka
- Celery
- Redis
- MLflow
- Kubernetes
- Dedicated ML serving service
- Dedicated vector database
- Dedicated graph database
- Microservice decomposition

These technologies should only be introduced when a concrete requirement justifies them.

---

# 83. Technology Decision Principles

Technology choices should follow these principles:

1. Prefer simplicity.
2. Prefer well-supported open-source tooling.
3. Avoid unnecessary distributed infrastructure.
4. Keep components replaceable.
5. Optimize for correctness before scale.
6. Keep ML experimentation easy.
7. Preserve clear domain boundaries.
8. Avoid vendor lock-in where practical.

---

# 84. Technical Acceptance Criteria

The technical implementation should eventually satisfy:

### TR-001

The backend runs as a FastAPI application.

### TR-002

PostgreSQL is used as the authoritative application database.

### TR-003

Protected APIs require authentication.

### TR-004

Role-based authorization is enforced.

### TR-005

Transaction ingestion validates incoming data.

### TR-006

Data processing prevents temporal leakage.

### TR-007

Behavioral features are generated from valid historical information.

### TR-008

Risk analysis supports model versioning.

### TR-009

Risk factors are available for flagged activity.

### TR-010

Investigations can be created and resolved.

### TR-011

AI summaries use structured investigation evidence.

### TR-012

Ground-truth fraud fields cannot leak into production model features.

### TR-013

The system supports deterministic test datasets.

### TR-014

The application can process the target development and full dataset sizes.

### TR-015

The project can run through Docker-based local development. *(Deferred to Phase 13 per accepted ADR-061 and ADR-073 to allow native verification and code-only v1.0.0 release).* 

---

# 85. Open Technical Decisions

The following decisions will be finalized in subsequent technical documents or during implementation:

1. Exact Python version.
2. Exact JWT library.
3. Exact password hashing library.
4. Exact ORM/data-access approach.
5. Exact migration framework.
6. Exact project package structure.
7. Exact model serialization strategy.
8. Exact AI provider.
9. Exact AI model.
10. Exact background-processing strategy.
11. Exact file-upload storage mechanism.
12. Exact database indexing strategy.
13. Exact feature persistence strategy.
14. Exact deployment platform.

These decisions should be recorded in `DECISIONS.md` when finalized.

---

# 86. Relationship to Other Documents

This document depends on the product requirements defined in:

`PRD.md`

and dataset requirements defined in:

`DATASET_SPECIFICATION.md`

The following documents will provide deeper technical detail:

| Concern | Document |
|---|---|
| Product requirements | `PRD.md` |
| Dataset | `DATASET_SPECIFICATION.md` |
| System architecture | `ARCHITECTURE.md` |
| Database schema | `DATABASE_DESIGN.md` |
| ML design | `ML_DESIGN.md` |
| API contracts | `API_GUIDELINES.md` |
| Security | `SECURITY.md` |
| Coding standards | `CODING_STANDARDS.md` |
| Testing | `TESTING_STRATEGY.md` |
| Roadmap | `PROJECT_ROADMAP.md` |
| Decisions | `DECISIONS.md` |
| Development history | `PROJECT_LOG.md` |

---

# 87. Document Status

**Version:** 1.0.0  
**Status:** Approved / Current  
**Last Updated:** 2026-11-04  
**Previous Document:** `DATASET_SPECIFICATION.md`  
**Next Document:** `ARCHITECTURE.md`

This document defines the technical requirements and implementation constraints that the FinSignal architecture must satisfy.
