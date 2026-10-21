# FinSignal — Project Log

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Log  
**Scope:** Backend + ML  
**Status:** Active Development Log  
**Version:** 1.0.0  
**Last Updated:** 2026-10-13

---

## 1. Purpose

This document records the chronological development history of FinSignal.

The project log is intended to capture:

- major implementation milestones;
- important decisions;
- completed phases;
- significant changes;
- testing milestones;
- architectural changes;
- release checkpoints;
- unresolved issues;
- lessons learned.

It is not a replacement for the project's technical documentation.

Detailed requirements remain in the relevant project documents.

---

# 2. Project Scope

The current development scope is:

```text
Backend
+
Financial Analytics
+
Machine Learning
+
Risk Analysis
+
Investigation Workflow
+
Evidence
+
AI Investigation Assistance
+
Testing
+
Security
+
Deployment
```

Frontend development is explicitly deferred until the Backend + ML release is complete.

---

# 3. Core Documentation Baseline

The project documentation set currently consists of:

```text
PRD.md
DATASET_SPECIFICATION.md
TRD.md
ARCHITECTURE.md
DATABASE_DESIGN.md
ML_DESIGN.md
API_GUIDELINES.md
SECURITY.md
CODING_STANDARDS.md
TESTING_STRATEGY.md
PROJECT_ROADMAP.md
DECISIONS.md
PROJECT_LOG.md
```

These documents form the current Backend + ML specification baseline.

---

# 4. Development Log Format

Each major entry should follow this structure:

```text
## YYYY-MM-DD — Milestone / Change

### Objective
What was being accomplished.

### Work Completed
What changed.

### Validation
How the work was verified.

### Decisions
Important decisions made during the work.

### Result
Current state after completion.

### Follow-up
What should happen next.
```

Small implementation details do not need individual entries unless they materially affect architecture, behavior, security, or project direction.

---

# 5. 2026-10-04 — Backend + ML Documentation Baseline

## Objective

Establish the complete technical documentation baseline before implementation.

## Work Completed

The project documentation was expanded to cover:

- product requirements;
- synthetic dataset design;
- technical requirements;
- architecture;
- database design;
- ML design;
- API conventions;
- security;
- coding standards;
- testing strategy;
- project roadmap;
- engineering decisions;
- project history.

## Result

The project now has an implementation-oriented documentation baseline for the Backend + ML scope.

## Follow-up

Begin implementation only after the relevant documentation has been reviewed and the repository has been initialized according to the roadmap.

---

# 5.1 2026-10-04 — Documentation Review & Second-Pass Remediation

## Objective

Execute rigorous second-pass remediation of the Backend + ML documentation set following cross-document audit findings.

## Work Completed

- **Risk Levels (ISSUE-01):** Unified risk level vocabulary (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) across `PROJECT_ROADMAP.md` and `TESTING_STRATEGY.md`.
- **Investigation Trigger Policy (ISSUE-02):** Defined server-side application configuration mechanism in `ML_DESIGN.md` and `DECISIONS.md` (ADR-056).
- **Account Age Leakage (ISSUE-03):** Clarified static `account_age_days` CSV field in `DATASET_SPECIFICATION.md` and prohibited its use as a feature in `ML_DESIGN.md`.
- **Temporal Feature Boundary (ISSUE-04):** Established canonical strictly-exclusive boundary (`occurred_at < t OR (occurred_at == t AND id < T.id)`) across `ML_DESIGN.md`, `CODING_STANDARDS.md`, `TESTING_STRATEGY.md`, and `DECISIONS.md` (ADR-057).
- **Sparse Account Baselines (ISSUE-05):** Formally recorded Open Decision in `DECISIONS.md` with candidate strategies and Phase 6 resolution criteria.
- **Model Lifecycle (ISSUE-06):** Synchronized `VALIDATED` state into `DATABASE_DESIGN.md` and defined lifecycle transition tests (TG-05) in `TESTING_STRATEGY.md`.
- **Evidence Immutability (ISSUE-07):** Enforced append-only immutability in `DATABASE_DESIGN.md`, `API_GUIDELINES.md`, and added testing in `TESTING_STRATEGY.md`.
- **Ingestion Idempotency (ISSUE-08):** Specified partial unique index for batch imports and application-level deduplication for standalone transactions in `DATABASE_DESIGN.md` and `DECISIONS.md` (ADR-058).
- **Polymorphic Evidence Source ID (ISSUE-09):** Documented architecture trade-off in `DATABASE_DESIGN.md`, `DECISIONS.md` (ADR-060), and application validation tests in `TESTING_STRATEGY.md`.
- **Hyperparameter Discipline (ISSUE-10):** Added evaluation requirement for Isolation Forest contamination in `TESTING_STRATEGY.md`.
- **Frontend Scope Deferral (ISSUE-11, ISSUE-12):** Added explicit deferral notices to `CODING_STANDARDS.md` and `SECURITY.md`.
- **Security & Testing Gaps (SG-01, SG-02, SG-03, TG-01–TG-04):** Clarified configurable rate limiting, JWT Bearer CSRF model, SHA-256 model artifact verification (`model_versions.artifact_hash`, ADR-059), risk score range enforcement tests, and transfer self-reference check constraints.

## Result

The documentation set is now synchronized, free of internal contradictions, and ready for Backend + ML implementation.

---

# 6. Documentation Completion Tracking

| Document | Purpose | Status |
|---|---|---|
| `PRD.md` | Product requirements | COMPLETED |
| `DATASET_SPECIFICATION.md` | Synthetic data and fraud scenarios | COMPLETED |
| `TRD.md` | Technical requirements | COMPLETED |
| `ARCHITECTURE.md` | System architecture | COMPLETED |
| `DATABASE_DESIGN.md` | PostgreSQL schema/design | COMPLETED |
| `ML_DESIGN.md` | ML/risk architecture | COMPLETED |
| `API_GUIDELINES.md` | REST API contract conventions | COMPLETED |
| `SECURITY.md` | Security requirements | COMPLETED |
| `CODING_STANDARDS.md` | Implementation standards | COMPLETED |
| `TESTING_STRATEGY.md` | Testing strategy | COMPLETED |
| `PROJECT_ROADMAP.md` | Backend + ML roadmap | COMPLETED |
| `DECISIONS.md` | Architecture/engineering decisions | COMPLETED |
| `PROJECT_LOG.md` | Chronological project history | ACTIVE |

---

# 7. Implementation Phase Log

The following sections are reserved for implementation milestones.

---

## Phase 0 — Foundation

### Objective

Establish the Python project, development environment, configuration, PostgreSQL connectivity, migration infrastructure, testing foundation, and CI baseline.

### Completed Work

- Pinned Python 3.12 with `uv` (`.python-version`, `pyproject.toml`, `uv.lock`).
- Established standard `src/finsignal` package layout.
- Implemented environment-based configuration using Pydantic Settings with dual alias mapping (`POSTGRES_*` / `DATABASE_*`), `SecretStr` password masking, and safe URL generators.
- Created `.env.example` with placeholders; ensured `.env` is ignored by Git.
- Implemented SQLAlchemy 2.0 Async (`asyncpg`) database resource factory (`create_db_resources(settings)`) bound to `app.state.db_engine` and `app.state.session_maker`.
- Implemented FastAPI application factory (`create_app(settings)`), lifespan database cleanup, and exposed module-level `app = create_app()`.
- Implemented `GET /health` (200 alive) and `GET /ready` (200 when DB connected, 503 JSONResponse when disconnected).
- Implemented async database session dependency (`get_db_session`) with automatic rollback on error.
- Configured Alembic with synchronous `psycopg` driver, dynamic settings URL retrieval, and created initial baseline migration (`0001_initial_baseline.py`) with zero domain tables.
- Resolved database URL construction defect by transitioning from naive string interpolation to SQLAlchemy's structured `URL.create()` API, ensuring safe percent-encoding for passwords with reserved URI characters (`@`, `:`, `/`, etc.) and adding regression tests.
- Implemented comprehensive test suite (unit, API, integration) using `pytest-asyncio` and `httpx`, verifying health, ready, disconnected handling, settings validation, and test database isolation (`finsignal_test`).
- Configured Ruff (linter and formatter) with `extend-exclude = ["docs"]`, and configured mypy in strict mode.
- Created GitHub Actions CI workflow (`.github/workflows/ci.yml`) targeting `main` with ephemeral PostgreSQL 16 service container.
- Note: Docker local containerization was explicitly deferred to Phase 12 per architectural decision (ADR-061); native Windows PostgreSQL and GitHub Actions CI service were established.

### Validation

- **Automated Tests:** `uv run pytest -v` passed with 12/12 tests passing across unit, API, and integration suites.
- **Static Analysis & Formatting:** `uv run ruff check .` passed with 0 errors; `uv run ruff format --check .` confirmed all 16 files formatted; `uv run mypy src tests` passed in strict mode with 0 issues.
- **Live PostgreSQL Verification:** Native PostgreSQL 18 service (`postgresql-x64-18`) on Windows validated on port 5432; connection verified using project settings.
- **Migration Verification:** `uv run alembic upgrade head` executed live against `finsignal_dev`; downgrade to base (`alembic downgrade base`) and re-upgrade cycles verified; database catalog inspection confirmed `alembic_version` contains `0001_initial_baseline` with zero domain tables.
- **Endpoint Verification:** Live Uvicorn execution verified with HTTP client; `GET /health` returned HTTP 200 `{"status": "healthy"}`; `GET /ready` returned HTTP 200 `{"status": "ready", "database": "connected"}` with live database, and HTTP 503 `{"status": "unhealthy", "database": "disconnected"}` when database is disconnected.
- **CI Workflow:** GitHub Actions workflow reviewed and validated locally; staged for remote execution upon repository push.

### Status

`COMPLETED`

---

# 8. Phase 1 — Backend Architecture

### Objective

Implement the modular-monolith structure establishing a testable, secure foundation for domain and feature modules.

### Completed Work

- Extended `Settings` in `core/config.py` with environment profiles (`development`, `testing`, `production`), normalized log levels, log formats (`text`, `json`), and configurable request ID header name (`request_id_header`, defaulting to `"X-Request-ID"`).
- Created contextual logging subsystem in `core/logging.py` featuring `request_id_ctx` (ContextVar), `RequestIdFilter`, human-readable `TextFormatter`, structured single-line `JsonFormatter`, and idempotent `setup_logging()`.
- Implemented pure ASGI `RequestIdMiddleware` in `core/middleware.py` with strict regex validation (`^[a-zA-Z0-9_-]{1,64}$`), UUID fallback, header de-duplication, latency measurement (`X-Process-Time`), context variable cleanup in `finally`, pre-response-start sanitized 500 fallback, and mid-stream exception propagation.
- Defined minimal `FinSignalError` hierarchy in `common/exceptions.py` (`NotFoundError`, `ConflictError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`, `InfrastructureError`) with validated error code format (`^[A-Z0-9_]{3,64}$`) and strict isolation of public messages/details from private `internal_context`.
- Defined standard error response payload models in `common/responses.py` (`ErrorPayload`, `ErrorResponse`).
- Implemented centralized exception handlers in `common/handlers.py` for `FinSignalError`, `RequestValidationError` (safe descriptions and sanitized key paths), `SQLAlchemyError` (safe 500 responses without query/credential leakage), and `StarletteHTTPException` (allowlisted messages preserving protocol headers).
- Created versioned routing structure in `api/router.py` and `api/v1/system.py`, mounting `/health` and `/ready` probes at both root and `/api/v1` for contract preservation.
- Wired middleware, logging, exception handlers, and database lifecycle resources cleanly through `create_app()` factory in `main.py`.
- Developed comprehensive test coverage across configuration, logging, pure ASGI middleware edge cases, exception handlers, and security sanitization.
- Retained domain modules (`auth`, `users`, `accounts`, etc.) for progressive implementation in their respective scheduled phases (starting with Phase 2 for database models and Phase 3 for authentication), avoiding premature empty directory scaffolding (ADR-063, proposed).

### Validation

- **Automated Tests:** `uv run pytest -v` passed with 49/49 tests passing across unit, API, and integration suites.
- **Static Analysis & Formatting:** `uv run ruff check .` passed with 0 errors; `uv run ruff format --check .` confirmed all 30 files formatted; `uv run mypy src tests` passed in strict mode with 0 issues across 27 source files.
- **Database & Migration Status:** Alembic migration status verified clean at `0001_initial_baseline (head)`.
- **System Endpoints:** Verified `/health` and `/ready` operational at both root and `/api/v1` across connected and disconnected database states.
- **Invariants:** Phase 0 invariants, database session lifecycles, and health/readiness contracts preserved.

### Status

`COMPLETED`

---

# 9. Phase 2 — Database & Domain Models

### Objective

Implement the PostgreSQL domain model for Phase 2 (Option C: 12 Operational Tables per proposed ADR-063 and ADR-064).

### Primary Areas (12 Operational Tables)

- users;
- accounts;
- merchants;
- devices;
- account-device relationships (`account_devices`);
- locations;
- transactions;
- transaction import records (`transaction_import_records`);
- dataset versions (`dataset_versions`);
- dataset imports (`dataset_imports`);
- dataset import errors (`dataset_import_errors`);
- audit events (`audit_events`).

*(Intelligence, investigation, and AI entities deferred to Phases 6, 7, and 8 per proposed ADR-063).*

### Important Constraints

- canonical transaction identity: `CONSTRAINT uq_transactions_canonical_id UNIQUE (source_namespace, account_id, external_transaction_id)`;
- source accounts resolved to internal canonical `account_id` before transaction identity matching;
- transaction immutability: never overwrite or update canonical transaction attributes;
- import row-level provenance via `transaction_import_records` (`INSERTED`, `MATCHED_EXISTING`, `DUPLICATE_IN_IMPORT`, `QUARANTINED`, `REJECTED`);
- nullable initial import reference: `first_seen_import_id UUID NULL` to support standalone transactions;
- material conflict quarantine: conflicting payload attributes written to `dataset_import_errors` and marked `QUARANTINED`, never overwriting canonical rows;
- file re-upload handling: byte-identical completed uploads return existing summary (HTTP 200); in-progress identical uploads return HTTP 409 (`IMPORT_IN_PROGRESS`);
- row-level idempotent failure recovery without naive `MAX + 1` skip;
- valid foreign keys;
- valid transfer counterparties;
- deterministic ordering;
- correct timestamp handling;
- appropriate indexes.

### Validation

- migration tests;
- repository tests;
- constraint tests;
- canonical identity and import provenance tests (TG-06);
- transaction persistence tests.

### Status

`NOT STARTED`

---

# 10. Phase 3 — Authentication & RBAC

### Objective

Secure the API.

### Planned Work

- registration;
- password hashing;
- login;
- JWT;
- current-user endpoint;
- logout/token strategy;
- roles;
- authorization dependencies;
- object-level authorization.

### Validation

- authentication tests;
- JWT tests;
- RBAC tests;
- IDOR tests;
- security regression tests.

### Status

`NOT STARTED`

---

# 11. Phase 4 — Dataset & Transaction Ingestion

### Objective

Build realistic synthetic financial data and a safe ingestion pipeline.

### Planned Dataset

```text
5,000 accounts
~500 merchants
~8,000 devices
~100 locations
~250,000 transactions
~3% fraud
```

### Development Scale

```text
100 accounts / ~5,000 transactions
1,000 accounts / ~50,000 transactions
5,000 accounts / ~250,000 transactions
```

### Fraud Scenarios

```text
F001 Large Amount Anomaly
F002 New Device
F003 New Location
F004 Unusual Time
F005 High Transaction Velocity
F006 Account Takeover
F007 Behavioral Spending Shift
```

### Validation

- structural validation;
- behavioral validation;
- deterministic seeds;
- ground-truth isolation;
- import error reporting;
- no silent data loss.

### Status

`COMPLETED (Implementation & Verification Complete; Ready for Final Review)`

---

# 12. Phase 5 — Financial Analytics

### Objective

Build deterministic financial intelligence.

### Planned Analytics

- transaction volume;
- spending trends;
- categories;
- merchants;
- account activity;
- debit/credit trends;
- averages;
- medians;
- temporal trends;
- behavioral summaries.

### Validation

Analytics must be tested against small hand-calculated datasets.

### Status

`NOT STARTED`

---

# 13. Phase 6 — Feature Engineering

### Objective

Build historical, behavior-aware ML features.

### Feature Groups

```text
Amount
Velocity
Device
Location
Merchant
Time
Behavior
```

### Critical Requirement

No feature may use information unavailable at the transaction evaluation timestamp.

### Validation

Mandatory tests:

- historical-window correctness;
- future transaction exclusion;
- future label exclusion;
- deterministic feature values;
- boundary timestamps.

### Status

`NOT STARTED`

---

# 14. Phase 7 — ML / Anomaly Detection

### Objective

Implement the initial anomaly-detection baseline.

### Model

```text
Isolation Forest
```

### Pipeline

```text
Transactions
    ↓
Historical Features
    ↓
Preprocessing
    ↓
Isolation Forest
    ↓
Anomaly Score
```

### Evaluation

- chronological split;
- precision;
- recall;
- F1;
- PR-AUC;
- false-positive rate;
- false-negative rate;
- alert volume;
- scenario-level detection;
- account-level detection.

### Validation

The model must be reproducible for a fixed dataset, feature configuration, and random seed.

### Status

`NOT STARTED`

---

# 15. Phase 8 — Risk Analysis

### Objective

Combine ML anomaly signals with deterministic behavioral signals.

### Architecture

```text
ML Anomaly Score
        +
Deterministic Signals
        ↓
Hybrid Risk Score
        ↓
Risk Level
        ↓
Risk Factors
```

### Risk Levels

```text
LOW
MEDIUM
HIGH
```

### Validation

- score bounds;
- threshold boundaries;
- factor correctness;
- model-version association;
- evidence traceability.

### Status

`NOT STARTED`

---

# 16. Phase 9 — Investigation & Evidence

### Objective

Build the human investigation workflow.

### Investigation Lifecycle

```text
OPEN
  ↓
UNDER_REVIEW
  ↓
RESOLVED
```

### Resolution Types

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

### Planned Work

- investigation creation;
- assignment;
- related transactions;
- evidence assembly;
- evidence persistence;
- status transitions;
- resolution;
- audit events.

### Validation

- authorization;
- state-machine tests;
- evidence lineage;
- immutable transaction verification;
- audit verification.

### Status

`NOT STARTED`

---

# 17. Phase 10 — AI Investigation Assistant

### Objective

Provide evidence-grounded AI summaries for investigators.

### Architecture

```text
Investigation
    ↓
Evidence Assembly
    ↓
Structured Context
    ↓
LLM Provider
    ↓
AI Summary
    ↓
Human Investigator
```

### Requirements

- provider abstraction;
- controlled evidence context;
- prompt versioning;
- evidence hashing;
- output validation;
- provider error handling;
- prompt-injection protection.

### Validation

- mocked provider tests;
- timeout tests;
- malformed response tests;
- grounding tests;
- prompt-injection tests;
- human-resolution protection.

### Status

`NOT STARTED`

---

# 18. Phase 11 — Testing, Security & Hardening

### Objective

Perform full-system verification before release.

### Testing

- unit;
- integration;
- API;
- authentication;
- RBAC;
- IDOR;
- ingestion;
- feature engineering;
- temporal leakage;
- ML;
- investigation;
- AI;
- migration;
- performance;
- failure injection.

### Security

- dependency review;
- secrets review;
- upload security;
- SQL injection;
- authorization;
- JWT;
- logging;
- CORS;
- production configuration.

### Status

`NOT STARTED`

---

# 19. Phase 12 — Docker, Deployment & Release

### Objective

Package the Backend + ML system into a reproducible release.

### Planned Work

- production Docker image;
- Docker Compose;
- environment configuration;
- migration deployment;
- health/readiness;
- structured logging;
- model artifacts;
- deployment documentation;
- backup considerations.

### Status

`NOT STARTED`

---

# 20. Backend + ML v1.0 Release Milestone

The release milestone is reached when:

```text
Backend
    +
Database
    +
Authentication
    +
Ingestion
    +
Analytics
    +
Feature Engineering
    +
ML
    +
Risk Analysis
    +
Investigation
    +
Evidence
    +
AI Assistance
    +
Testing
    +
Security
    +
Deployment
```

are implemented, tested, documented, and reproducible.

### Release Status

`NOT STARTED`

---

# 21. Current Non-Goals

The following should not be pulled into active implementation unless the roadmap is explicitly revised:

- Kafka;
- Redis;
- Celery;
- MLflow;
- graph database;
- graph ML;
- RAG;
- real-time streaming;
- microservices;
- advanced distributed processing;
- frontend implementation.

---

# 22. Future Frontend Track

After Backend + ML v1.0:

```text
Backend + ML Release
        ↓
Frontend PRD
        ↓
Frontend TRD
        ↓
Frontend Architecture
        ↓
Frontend Design
        ↓
Frontend Testing Strategy
        ↓
Frontend Implementation
```

Frontend work should begin as a new documented phase rather than being mixed into the current backend roadmap.

---

# 23. Change Log

## 2026-10-18 — Phase 2 Canonical Transaction Identity & Ingestion Contract Review

### Objective
Complete pre-implementation architectural review of transaction identity, import provenance, duplicate handling, and file-level deduplication boundaries prior to Phase 2 schema implementation.

### Work Completed
- Evaluated `PHASE2_IDENTITY_CONTRACT_PROPOSAL.md` against existing architecture and repository contracts.
- Adopted canonical transaction identity scoped by `(source_namespace, account_id, external_transaction_id)`.
- Replaced partial uniqueness index in `DATABASE_DESIGN.md` with explicit natural composite unique constraint `uq_transactions_canonical_id`.
- Decoupled internal synthetic transactions from external systems by introducing `source_namespace VARCHAR(64) NOT NULL DEFAULT 'SYNTHETIC'`.
- Preserved standalone transaction support by keeping `transactions.first_seen_import_id` nullable (`UUID NULL REFERENCES dataset_imports(id) ON DELETE RESTRICT`).
- Added `transaction_import_records` table to capture import-level row provenance, execution outcomes (`INSERTED`, `MATCHED_EXISTING`, `DUPLICATE_IN_IMPORT`, `QUARANTINED`, `REJECTED`), raw payload checksums, and canonical transaction associations.
- Expanded Phase 2 Option C scope from 11 to 12 operational tables (`DATABASE_DESIGN.md`, `PROJECT_ROADMAP.md`, `PROJECT_LOG.md`).
- Established strict material conflict quarantine: rows matching existing canonical identity but diverging in monetary amount, currency, timestamp, account, direction, transaction type, or counterparty are never overwritten; they are logged to `dataset_import_errors` with `error_code = 'MATERIAL_CONFLICT'` and recorded in `transaction_import_records` with `outcome = 'QUARANTINED'` (`transaction_id = NULL`).
- Specified file re-upload and concurrency policy: enforced transaction-scoped PostgreSQL advisory lock (`pg_advisory_xact_lock`) keyed from file hash held across lookup and record creation to eliminate fast-completion races; applicable completed imports take precedence and return HTTP 200 summary; concurrent in-progress uploads return HTTP 409 (`IMPORT_IN_PROGRESS`); failed file re-uploads create a new import attempt only when no applicable completed import exists; retained `uq_dataset_imports_active_hash` partial unique index as secondary safeguard; recorded open decision on completed-file retention window and contextual metadata divergence.
- Defined row-level idempotent recovery: failed imports reconcile committed row ordinals via `transaction_import_records` rather than resuming from naive `MAX(source_row_number) + 1`.
- Specified future generator contracts in `DATASET_SPECIFICATION.md` and `TESTING_STRATEGY.md` (version continuity, ID stability across seeds and accounts, synthetic namespace isolation), with explicit note that generator implementation does not yet exist.
- Prepared ADR-064 (*Canonical Transaction Identity Across Dataset Imports*) as `PROPOSED`. Retained ADR-058 as `ACCEPTED` with cross-reference note pending formal acceptance of ADR-064.

### Validation
- Pure documentation review and update across `DATABASE_DESIGN.md`, `DATASET_SPECIFICATION.md`, `API_GUIDELINES.md`, `TESTING_STRATEGY.md`, `PROJECT_ROADMAP.md`, `PROJECT_LOG.md`, and `DECISIONS.md`.
- No code, migration, or test implementation files were modified.
- Existing automated test suite verified intact: 49 passing tests (`uv run pytest -v`).
- Linter and type checker clean (`ruff check`, `ruff format --check`, strict `mypy`).

### Status
Documentation aligned. Ready for ADR-064 formal review and Phase 2 database model implementation upon authorization.

---

## 2026-10-13 — Phase 1 Backend Architecture & Core Structure

### Objective
Implement Phase 1 Backend Architecture & Core Structure establishing a testable, secure modular-monolith foundation.

### Work Completed
- Extended `Settings` in `core/config.py` with environment profiles (`development`, `testing`, `production`), normalized log levels, log formats (`text`, `json`), and configurable request ID header name (`request_id_header`, defaulting to `"X-Request-ID"`).
- Created contextual logging subsystem in `core/logging.py` featuring `request_id_ctx` (ContextVar), `RequestIdFilter`, human-readable `TextFormatter`, structured single-line `JsonFormatter`, and idempotent `setup_logging()`.
- Implemented pure ASGI `RequestIdMiddleware` in `core/middleware.py` with strict regex validation (`^[a-zA-Z0-9_-]{1,64}$`), UUID fallback, header de-duplication, latency measurement (`X-Process-Time`), context variable cleanup in `finally`, pre-response-start sanitized 500 fallback, and mid-stream exception propagation.
- Defined minimal `FinSignalError` hierarchy in `common/exceptions.py` (`NotFoundError`, `ConflictError`, `ValidationError`, `AuthenticationError`, `AuthorizationError`, `InfrastructureError`) with validated error code format (`^[A-Z0-9_]{3,64}$`) and strict isolation of public messages/details from private `internal_context`.
- Defined standard error response payload models in `common/responses.py` (`ErrorPayload`, `ErrorResponse`).
- Implemented centralized exception handlers in `common/handlers.py` for `FinSignalError`, `RequestValidationError` (safe descriptions and sanitized key paths), `SQLAlchemyError` (safe 500 responses without query/credential leakage), and `StarletteHTTPException` (allowlisted messages preserving protocol headers).
- Created versioned routing structure in `api/router.py` and `api/v1/system.py`, mounting `/health` and `/ready` probes at both root and `/api/v1` for contract preservation.
- Wired middleware, logging, exception handlers, and database lifecycle resources cleanly through `create_app()` factory in `main.py`.
- Developed comprehensive test coverage across configuration, logging, pure ASGI middleware edge cases, exception handlers, and security sanitization.

### Audit & Resolved Findings
Following initial implementation, a comprehensive senior security review and code audit was conducted:
- **P2-1 (Versioned Probe Coverage):** Parametrized tests in `tests/api/test_health.py` to cover both root and versioned routes (`/health` & `/api/v1/health`, `/ready` & `/api/v1/ready`) in connected and disconnected database states.
- **P2-2 (Configurable Request ID Wiring):** Added integration test in `tests/api/test_request_id.py` verifying `Settings(request_id_header="X-Correlation-ID") → create_app() → RequestIdMiddleware` wiring, ensuring valid custom headers are preserved, missing/malformed IDs regenerate under the custom header name, and duplicate headers are stripped.
- **P2-3 (Production Logging Setup):** Added unit tests in `tests/unit/test_logging.py` verifying that `setup_logging()` selects `JsonFormatter` in production profile and honors explicit format overrides, with an autouse fixture ensuring root logger state isolation across tests.
- **P3-1 (Location Sanitization):** Added focused test in `tests/api/test_errors.py` with synthetic validation errors carrying non-alphanumeric location tokens (e.g. `<script>`), verifying they are stripped via `FIELD_NAME_REGEX` and safely fall back to `"payload"` or valid prefix identifiers.
- **Diagnostic Note:** Investigated an editor LSP warning (`Pyrefly(bad-argument-type)` on `Field(..., gt=0)`); determined it is an upstream Pyrefly false positive when matching `annotated_types.SupportsGt`. Confirmed the source code is standard Pydantic v2, unmodified, and verified clean by the project's configured strict Mypy type checker.

### Validation
- 49 automated tests passing (`uv run pytest -v`).
- Ruff linter passing with zero warnings or errors (`uv run ruff check .`).
- Ruff formatter check passing (`uv run ruff format --check .`, 30 files formatted).
- Strict mypy passing across all 27 source files (`uv run mypy src tests`).
- Alembic database migration status verified clean at `0001_initial_baseline (head)` (`uv run alembic current`).
- Phase 0 invariants, database session lifecycles, and health/readiness contracts preserved.

### Decisions
- Handled unexpected pre-start exceptions inside `RequestIdMiddleware` with sanitized HTTP 500 fallback, and re-raise mid-stream exceptions cleanly.
- Strict separation between public exception details and internal diagnostic metadata; private sentinel values and raw internal context dictionaries are never leaked to client responses or routine logs.
- Retained ADR-063 as `PROPOSED` without premature filesystem scaffolding or schema migrations.

### Result
Phase 1 Backend Architecture & Core Structure is fully verified, operational, and clean. All acceptance criteria are satisfied.

### Follow-up
Proceed to Phase 2 (Data Foundation & Schema Design) when authorized.

---

## 2026-10-04

### Added

- Backend + ML documentation baseline.
- Testing strategy.
- Backend + ML project roadmap.
- Architecture and engineering decision record.
- Explicit frontend deferral boundary.

### Result

FinSignal now has an implementation-ready documentation foundation covering the initial Backend + ML release.

### Next

## 2026-10-18 — Phase 2: Database & Domain Models

### Objective
Implement Phase 2: Database & Domain Models of FinSignal adopting Candidate Option C (12 Operational Tables per approved ADR-063 and ADR-064).

### Work Completed
- **Declarative Mixin Hierarchy:** Implemented granular mixins in `common/models.py` (`UUIDPrimaryKeyMixin`, `CreatedAtMixin`, `UpdatedAtMixin`), strictly restricting `updated_at` to the 4 mutable entities (`users`, `accounts`, `merchants`, `devices`). Preserved natural composite primary key `(account_id, device_id)` and observation timestamps on `account_devices` without synthetic ID or generic timestamp pollution.
- **12 Operational Domain Models:** Implemented typed SQLAlchemy 2.0 declarative models across modular domain packages:
  - `users.models.User`: UUID PK, unique email, role check constraint (`ADMIN`, `ANALYST`, `INVESTIGATOR`), active state.
  - `locations.models.Location`: city, state, country, optional geographic coordinates, immutable creation timestamp.
  - `merchants.models.Merchant`: external merchant ID, merchant name, merchant category, location reference.
  - `devices.models.Device`: external device ID, device type, operating system, first seen timestamp.
  - `accounts.models.Account` & `AccountDevice`: account classification, customer age, home location reference, status, and account-device association with `is_primary` indicator.
  - `dataset.models.DatasetVersion`: version tag, source type (`SYNTHETIC`, `IMPORTED`), generator version, seed, configuration JSONB, fraud rate.
  - `dataset.models.DatasetImport`: ingestion tracking, file hash, status vocabulary, row counters, started/completed timestamps, and partial unique index `uq_dataset_imports_active_hash` on active uploads.
  - `dataset.models.DatasetImportError`: row-level and job-level error diagnostics with nullable `row_number`.
  - `transactions.models.Transaction`: financial event fact with `source_namespace VARCHAR(64) NOT NULL DEFAULT 'SYNTHETIC'`, `external_transaction_id`, nullable `first_seen_import_id` for standalone support, account references, monetary amount `NUMERIC(18,2)`, currency `CHAR(3)`, direction, and transfer counterparty constraints.
  - `transactions.models.TransactionImportRecord`: row-level provenance ledger with composite uniqueness `uq_import_records_row (dataset_import_id, source_row_number)` and five controlled outcomes (`INSERTED`, `MATCHED_EXISTING`, `DUPLICATE_IN_IMPORT`, `QUARANTINED`, `REJECTED`).
  - `audit.models.AuditEvent`: append-only audit trail with actor user reference, action, entity type/ID, metadata JSONB, and created_at timestamp.
- **Database Schema Migration:** Authored and verified Alembic revision `0002_core_operational_schema.py` creating the 12 operational tables, foreign keys with `ON DELETE RESTRICT`, primary keys, composite unique constraints, check constraints, and performance indexes.
- **Canonical Transaction Identity & Integrity Constraints:** Enforced natural key uniqueness via `CONSTRAINT uq_transactions_canonical_id UNIQUE (source_namespace, account_id, external_transaction_id)` with all three participating columns strictly `NOT NULL`. Enforced positive amounts, uppercase 3-letter currency regex, direction enums, distinct transfer counterparties (`account_id != counterparty_account_id`), and required transfer counterparties (`transaction_type != 'TRANSFER' OR counterparty_account_id IS NOT NULL`).
- **Deterministic Row-Hash Utilities:** Implemented isolated canonical serialization in `transactions/hashing.py`:
  - Strict monetary scale representation (accepts `Decimal` and fixed-point `str` with exact scale of 2; rejects floats and excess scale; no silent rounding).
  - Explicit Unicode NFC normalization across all text fields.
  - Timezone-aware timestamp UTC normalization with microsecond precision and `Z` suffix (naive datetimes rejected).
  - Exact 15-key sorted JSON serialization producing verified test vector digest: `1a5a4a225797715e7a1c98c6901285120cb4857df19d4ca7eb3f53f5646f686b`.
  - Advisory-lock key derivation helper and upload concurrency deferred to Phase 5.
- **Alembic Environment Wiring:** Updated `migrations/env.py` to import all domain models for full `Base.metadata` registration, and enhanced `get_url()` to respect dynamically passed database URLs in testing.
- **Governance & ADR Lifecycle:**
  - Formally superseded ADR-058 (`SUPERSEDED by ADR-064`).
  - Formally accepted ADR-063 (Option C / progressive module realization without premature scaffolding).
  - Formally accepted ADR-064 (canonical natural transaction identity and `transaction_import_records` provenance ledger).
  - Reconciled `DATABASE_DESIGN.md` and `PROJECT_ROADMAP.md` (Phase 2 marked `COMPLETED`).

### Validation Results
- **82 automated tests collected and passed** (`uv run pytest -v`):
  - 49 pre-existing tests preserved intact across API, database isolation, configuration, exception, and logging suites.
  - 33 new Phase 2 tests (12 canonical row-hash normalization tests in `test_hashing.py`, 10 declarative model metadata tests in `test_models.py`, and 11 constraint/migration integration tests in `test_constraints.py`).
- **Disposable PostgreSQL Database Validation:** Verified schema creation, foreign key restrictions, unique constraints, check constraints, partial active-import indexes, and persistence rollback atomicity on a freshly provisioned ephemeral PostgreSQL test database.
- **Migration Roundtrip Safety:** Verified clean `alembic upgrade head -> downgrade base -> upgrade head` execution on disposable test database with strict safety preconditions preventing execution against non-test databases.
- **Static Analysis:**
  - Ruff linter: 0 errors across entire repository (`uv run ruff check .`).
  - Ruff formatter: 100% compliant (`uv run ruff format --check .`).
  - Strict mypy: 0 errors across all 48 source files (`uv run mypy src tests`).

### Remaining Open Decisions
- Contextual metadata divergence policy on canonical match (lossy canonical preservation vs quarantine vs observation child table).
- Completed-file deduplication retention window (perpetual vs sliding window).
- Non-transfer counterparty business rule (whether non-transfers should be prohibited from holding counterparties at the DB constraint level).
---

## 2026-10-20 — Phase 3: Authentication & Role-Based Access Control (RBAC)

### Objective
Establish the security boundary for FinSignal, implementing secure user registration, Argon2id password hashing, JWT access token issuance/validation, user persistence, role-based access control, and public authentication endpoints prior to exposing transaction analysis features.

### Work Completed
- **Stage 1 — Dependencies & Configuration:** Configured `argon2-cffi`, `PyJWT`, and `email-validator` in `pyproject.toml`. Extended `core.config.Settings` with `jwt_secret_key` (SecretStr), `jwt_algorithm` (HS256), and `access_token_expire_minutes` (30m).
- **Stage 2 — Security Primitives (`auth.security`):** Implemented Argon2id password hashing (`hash_password`, `verify_password`, `verify_dummy_password`) and JWT access token handling (`create_access_token`, `decode_access_token`). Enforced algorithm whitelisting (strictly HS256), canonical lowercase UUID subject format, and strict expiration/iat verification without leaking internal tokens or secrets in exception contexts.
- **Stage 3 — Persistence & Schemas (`users.repository`, `auth.schemas`):** Implemented `UserRepository` providing async CRUD (`create`, `get_by_id`, `get_by_email`) with NFC Unicode and trimmed email normalization. Authored strict Pydantic v2 schemas: `RegisterRequest` (12-128 chars, extra="forbid"), `LoginRequest` (extra="forbid"), `TokenResponse` (bearer, expires_in), `UserResponse` (sanitized public fields only, stripping sensitive hashes), and `LogoutResponse`.
- **Stage 4 — Authentication Service (`auth.service`):** Implemented `AuthService` handling registration with server-authoritative `ANALYST` role assignment, dummy password hash verification to mitigate timing discrepancies for unknown users, and structured driver diagnostic classification (`_is_email_unique_violation`) translating PostgreSQL unique_violation `23505` to client-safe `ConflictError("STATE_CONFLICT")` while performing safe session rollback.
- **Stage 5 — Authentication Dependencies & RBAC (`auth.dependencies`):** Implemented FastAPI dependencies using `Annotated`: `get_current_user` (Bearer extraction via `HTTPBearer(auto_error=False)` returning HTTP 401 `AuthenticationError` on missing/invalid credentials, authoritative DB lookup, inactive check), and composable RBAC `RoleChecker` / `require_roles("ADMIN", "ANALYST", "INVESTIGATOR")`. Does not rely on token claims for authorization: user status and roles are authoritatively queried from PostgreSQL on every request.
- **Stage 6 — Authentication API Endpoints (`api.v1.auth`):** Mounted versioned routes under `/api/v1/auth`:
  - `POST /register`: creates `ANALYST` user, returns HTTP 201 `UserResponse`.
  - `POST /login`: authenticates credentials, returns HTTP 200 `TokenResponse`.
  - `GET /me`: protected endpoint returning current user's public profile from DB.
  - `POST /logout`: protected endpoint requiring valid authentication and returning stateless confirmation `LogoutResponse`.
- **Stage 7 — Automated Security & Integration Testing:** Added targeted integration tests on disposable PostgreSQL databases covering concurrent duplicate registration races, account deactivation/deletion enforcement on live routes, algorithm substitution/tampering defenses, and request-id correlation.

### Validation Results
- **205 automated tests collected and passed** (`uv run pytest`):
  - 82 pre-existing Phase 0, 1, 2 tests preserved.
  - 123 Phase 3 tests across security primitives, hashing, schemas, repositories, service, dependencies, RBAC, and integration endpoints.
- **Static Analysis & Tooling:**
  - Ruff check: 0 errors (`uv run ruff check .`).
  - Ruff format: 100% compliant across 69 files (`uv run ruff format --check .`).
  - Strict mypy: 0 errors across 65 source files (`uv run mypy src tests`).
- **Disposable PostgreSQL Integration:** Verified end-to-end HTTP request/response flows, database session rollbacks, constraint enforcement, and dynamic role propagation on ephemeral live databases.

### Residual Risks & Next-Step Items
- **Deferred Rate Limiting:** Brute-force protection on `POST /api/v1/auth/login` and account creation abuse protection on `POST /api/v1/auth/register` were deferred per Phase 3 specifications and must be prioritized before public internet exposure.
- **Alembic Path Separator Cleanup:** 14 test-time Alembic deprecation warnings (`No path_separator found in configuration...`) noted for cleanup in future configuration refactoring.
- **Duplicate Registration Error Contract:** API returns `code="STATE_CONFLICT"` (HTTP 409) under the centralized exception hierarchy; documentation reconciled.

---

## 2026-10-20 — Phase 4 Preflight & Synthetic Dataset Observation Policies (ADR-065 Proposed)

### Objective
Execute Phase 4 preflight review, inspect repository state against ADR-064, evaluate unresolved architectural decisions, and synchronize project specifications with project-owner policy selections prior to generator and ingestion implementation.

### Work Completed
- **Repository Verification:** Verified clean working tree, verified 205 passing tests with 14 Alembic deprecation warnings, identified local dev database at revision `0001_initial_baseline` while migration head is `0002_core_operational_schema`.
- **Policy Selection Review:** Reviewed project owner's selected policies:
  - *Decision A:* Candidate 1 — preserve canonical immutable facts and record `row_hash` provenance in `transaction_import_records` with outcome `MATCHED_EXISTING`; alternate contextual plaintext values are not stored in relational storage and cannot be reconstructed from one-way SHA-256 hashes.
  - *Decision B:* Deterministic synthetic business identifiers (`ACC_[0-9]{6}`, `TXN_[0-9]{8}`, etc.), strict reproducibility tuple `(seed, generator_version, config)`, progressive prefix determinism through isolated per-entity PRNG streams, and explicit namespace isolation (`source_namespace`).
  - *Decision C:* Namespace-scoped perpetual completed-file deduplication `(source_namespace, file_hash)`, preserving namespace isolation so identical files uploaded under different namespaces (e.g. `SYNTHETIC` vs `PUBLIC_DATASET_A`) remain distinct import identities. Composite advisory locking prevents concurrent active imports within the same namespace.
  - *Decision D:* Namespace-scoped account identity `(source_namespace, external_account_id)` with verified transaction-account namespace agreement.
- **Follow-Up Technical Review & Refinements:**
  - *Finding A (Advisory Lock Key Derivation):* Specified Python-level derivation of 64-bit signed integer key (`hashlib.sha256(f"{source_namespace}:{file_hash}".encode("utf-8")).digest()[:8]`) and corrected the pure-PostgreSQL SQL alternative using `encode(sha256(...), 'hex')`. Clarified hash collision behavior.
  - *Finding B (Account Namespace Backfill):* Documented staged migration pattern across 5 distinct legacy account cases. Unambiguous reconciliation query with `HAVING count(DISTINCT source_namespace) = 1`; multi-namespace accounts (`> 1`) halt migration for operator remediation.
  - *Finding C (Dataset Imports Backfill):* Defined 5 distinct legacy import cases (I1–I5) with reconciliation from linked transactions, version metadata, or quarantine.
  - *Finding D (Namespace Consistency Enforcement):* Evaluated Option C1 (application-level), Option C2 (DB composite foreign key), and Option C3 (layered enforcement). Recommended Option C3 for financial relational integrity, qualified the scope of database protection (relational referential integrity vs application/audit rules), and explained coordination with the existing single-column FK.
  - *Finding E (Phase 4 Sequencing):* Corrected dependency sequence so that Checkpoint P4.0 (Account & Import Namespace Migration) precedes Checkpoint P4.1 (Reference Entity & Synthetic Generator Core), ensuring the database schema is namespace-ready before account entities are generated or persisted.
  - *Finding F (Constraint Verification):* Confirmed actual canonical transaction constraint name is `uq_transactions_canonical_id` across migrations, models, tests, and documentation.
- **ADR-065 Drafting:** Drafted and refined ADR-065 (`Synthetic Dataset Identity and Import Observation Policies`) in `docs/DECISIONS.md` covering Decisions A, B, C, and D under `PROPOSED — awaiting project-owner approval` status.
- **Documentation Synchronization:** Updated `docs/DECISIONS.md`, `docs/DATABASE_DESIGN.md`, `docs/API_GUIDELINES.md`, `docs/DATASET_SPECIFICATION.md`, `docs/TRD.md`, and `docs/PROJECT_ROADMAP.md` ensuring full consistency across contextual conflict handling, namespace-scoped file deduplication, synthetic identity, and staged account identity migration contracts.
- **Migration Dependency Documented:** Identified that `accounts.external_account_id` currently has a non-unique index and lacks `source_namespace`; recorded the required future Alembic migration (adding `source_namespace` to `accounts` and `dataset_imports` with partial unique index), duplicate preflight, and conditional backfill as prerequisite Checkpoint P4.0 before reference-entity account generation and transaction ingestion.
- **Safety Confirmation:** Confirmed that no application source code, tests, configuration files, or database migrations were modified, and no git commits were created.

### Result
Documentation baseline is technically defensible, mathematically unambiguous, and synchronized across all specifications with the project owner's four selected architectural choices and refined technical safeguards.

### Next Steps
1. Project owner reviews and formally approves ADR-065 final wording.
2. Synchronize local dev database via `uv run alembic upgrade head`.
3. Design, review, test, and apply Checkpoint P4.0 (Account & Import Namespace Staged Migration) before generating reference entities.
4. Proceed to Checkpoint P4.1 (Synthetic Generator Core & Reference Entities: `locations`, `merchants`, `devices`, `accounts`).
5. Proceed to Checkpoints P4.2 through P4.6.

---

## 2026-10-22 — Phase 4 Completion: Synthetic Generator Core, Behavioral Synthesis, Advisory Locking, and Gap-Safe Ingestion Verification

Complete the full implementation and verification of Phase 4 (Checkpoints P4.0 through P4.6) covering deterministic synthetic dataset generation, namespace migration, canonical transaction identity matching, advisory-lock deduplication, REST import endpoints, and gap-safe recovery.

### Work Completed
- **Checkpoint P4.0 (Account & Import Namespace Staged Migration):**
  - Authored, applied, and verified Alembic migration `0003_account_import_namespace.py`.
  - Added `source_namespace VARCHAR(64) NOT NULL DEFAULT 'SYNTHETIC'` to `accounts` and `dataset_imports`.
  - Implemented 5 preflight checks and conditional reconciliation queries (unambiguous ledger, multi-namespace contamination halts, internal account defaults, unprovable account quarantine flagging, collision assertion).
  - Enforced partial unique indexes `uq_accounts_namespace_external_id` and `uq_dataset_imports_active_hash`.
  - Implemented Layered Enforcement (Option C3) backed by database composite foreign key `fk_transactions_account_namespace` on `transactions(account_id, source_namespace) REFERENCES accounts(id, source_namespace)`.
- **Checkpoint P4.1 (Deterministic Generator Core & Reference Entities):**
  - Implemented `ReferenceEntityGenerator` and `ReferenceEntityPersistenceService` generating deterministic reference entities (`locations`, `merchants`, `devices`, `accounts`).
  - Standardized business identifiers: `ACC_[0-9]{6}`, `MERCH_[0-9]{5}`, `DEV_[0-9]{6}`, `LOC_[0-9]{3}`, and `TXN_[0-9]{8}`.
  - Implemented domain- and entity-isolated PRNG streams (`get_domain_rng`, `get_entity_rng`) ensuring independent stream reproducibility across runs.
- **Checkpoint P4.2 (Behavioral Synthesis & Fraud Scenarios F001–F007):**
  - Implemented `TransactionDatasetGenerator` with five behavioral spending profiles calibrated in Indian Rupees (`LOW_SPENDER`: mean ₹450, `MODERATE_SPENDER`: mean ₹1,800, `HIGH_SPENDER`: mean ₹14,000, `SUBSCRIPTION_HEAVY`: mean ₹650, `BUSINESS_LIKE`: mean ₹32,000).
  - Synthesized fraud scenarios F001 through F007:
    - F001: Large amount anomaly (8x–15x profile ceiling).
    - F002: New device anomaly.
    - F003: New location anomaly.
    - F004: Unusual nocturnal hour (02:30–04:00 AM).
    - F005: High velocity burst (4 rapid transactions).
    - F006: Account takeover pattern (attempted drain sequence: 4 transactions: probe $\rightarrow$ drain transfer $\rightarrow$ drain transfer $\rightarrow$ ATM cash withdrawal).
    - F007: Behavioral spending shift (3 transactions: rapid luxury/electronics pivot).
  - Enforced transfer invariants: `TRANSFER` transactions strictly require distinct `counterparty_account_id` (`counterparty_account_id != account_id`), while non-transfers require `counterparty_account_id IS NULL`.
- **Checkpoint P4.3 (Scale Presets, Isolated Ground Truth & CSV Exporter):**
  - Implemented canonical scale presets in `GeneratorConfig`: `small` (15 accounts, 500 txns, 3% fraud), `medium` (100 accounts, 5,000 txns, 3% fraud), and `full` (5,000 accounts, 250,000 txns, 3% fraud).
  - Built `CSVDatasetExporter` producing 7 distinct artifacts (`accounts.csv`, `merchants.csv`, `devices.csv`, `locations.csv`, `transactions.csv`, `transactions_ground_truth.csv`, `metadata.json`) with formula injection sanitization (`sanitize_csv_value`).
  - Production `transactions.csv` contains zero ground truth labels, completely isolating evaluation labels into `transactions_ground_truth.csv`.
  - Built `DatasetQualityValidator` ensuring structural and domain invariant compliance.
- **Checkpoint P4.4 (Transaction Ingestion Engine & Provenance Ledger):**
  - Implemented `TransactionIngestionEngine` with bounded batch processing and row-level provenance logging to `transaction_import_records`.
  - Implemented canonical transaction natural key matching on `(source_namespace, account_id, external_transaction_id)`.
  - Verified all five documented provenance outcomes:
    - `INSERTED`: Fresh canonical transaction.
    - `MATCHED_EXISTING`: Canonical key and all 7 core material fields match existing record (alternate contextual differences preserved as lossy hash provenance without overwriting canonical facts).
    - `DUPLICATE_IN_IMPORT`: Duplicate canonical key within the same import file.
    - `QUARANTINED`: Canonical key matches but material fields conflict (`MATERIAL_CONFLICT`). Canonical row remains immutable; conflict error logged in `dataset_import_errors`.
    - `REJECTED`: Malformed syntax, invalid types, or unresolvable reference entities.
- **Checkpoint P4.5 (Advisory Locking, Deduplication & REST Import API):**
  - Implemented `DatasetImportService` and FastAPI router mounted on `/api/v1/datasets/imports`.
  - Enforced 64-bit signed integer advisory lock derivation `(source_namespace, file_hash)` via `pg_advisory_xact_lock` with statement timeout. Verified that lock key collisions cause temporary serialization without data corruption or cross-namespace pollution.
  - Implemented namespace-scoped deduplication:
    - Completed upload with identical bytes in same namespace returns `HTTP 200 OK` with existing summary (`is_duplicate = True`).
    - Active in-progress identical upload returns `HTTP 409 Conflict` with code `"IMPORT_IN_PROGRESS"`.
    - Uploading identical bytes in different namespaces operates independently.
  - Endpoints: `POST /api/v1/datasets/imports`, `GET /api/v1/datasets/imports/{id}`, and `POST /api/v1/datasets/imports/{id}/recover`.
- **Checkpoint P4.6 (Gap-Safe Recovery & Integration Verification):**
  - Implemented durable row-level recovery reading committed row ordinals via `SELECT source_row_number FROM transaction_import_records WHERE dataset_import_id = :id`. Proved recovery resumes from non-contiguous gaps without skipping or duplicating rows.
  - Added race-safe entity refresh on advisory lock acquisition during recovery (`session.refresh(import_record)`).
  - Verified 10 lifecycle scenarios under PostgreSQL.

### Empirical Validation & Quality Gates
- `uv run pytest tests/unit`: 165 passed in 3.51s.
- `uv run pytest`: 276 passed (0 failed, 0 skipped) across unit, API, and PostgreSQL integration tests in 49.87s.
- `uv run ruff check .`: Clean (all checks passed).
- `uv run ruff format --check .`: Clean (104 files formatted).
- `uv run mypy src tests`: Success: no issues found in 99 source files.
- Alembic revision: `0003_account_import_namespace (head)`.

### Result
Phase 4 implementation is complete, fully verified against PostgreSQL, and reconciled with all project documentation. All exit criteria are satisfied.

### Next Steps
1. Project owner reviews the complete Phase 4 documentation and code diff.
2. Execute final quality gates.
3. Commit Phase 4 as a unified milestone.
4. Proceed to Phase 5: Deterministic Financial Analytics.

---

# 24. Log Maintenance Rules

The project log should be updated when:

- a phase starts;
- a phase completes;
- an important architectural decision changes;
- a significant test milestone is reached;
- a major bug changes the design;
- a release is created;
- a major scope change occurs.

Do not record every trivial coding action.

The log should answer:

```text
What changed?
Why did it change?
How was it validated?
What is the current state?
What happens next?
```

---

# 25. Final Principle

The project log is a record of **engineering evolution**, not a diary of every command executed.

FinSignal should maintain enough history that a future developer can understand:

- why the architecture looks the way it does;
- why technologies were selected or deferred;
- how the ML system evolved;
- how correctness was validated;
- when major milestones were reached;
- why important trade-offs were made.

The Backend + ML release is the primary milestone for the current development track.

Frontend work begins only after that milestone is complete.
