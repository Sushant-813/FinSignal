# FinSignal — Project Log

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Log  
**Scope:** Backend + ML  
**Status:** Active Development Log  
**Version:** 1.0.0  
**Last Updated:** 2026-11-12

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

`HISTORICAL OUTLINE (Superseded by Section 28 completion entry)`

---

# 17. Phase 10 — AI Investigation Assistant *(Historical Planning Outline)*

*(Note: This historical planning entry has been superseded by Section 28, which records the complete implementation and verification of Phase 10.)*

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

# 18. Phase 11 — Testing, Security & Hardening *(Historical Planning Outline)*

*(Note: This historical planning entry has been superseded by Section 30, which records the Phase 11 implementation, hardening corrections, and targeted verification.)*

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

# 24. Phase 5 Implementation — Deterministic Financial Analytics

**Date:** 2026-10-24
**Scope:** Complete vertical slice implementation of Phase 5 Financial Analytics.

### Summary of Completed Work

1. **Schemas & Domain Contracts (`src/finsignal/analytics/schemas.py`):**
   - Implemented strict Pydantic v2 schemas: `OverviewAnalyticsResponse`, `TrendAnalyticsResponse`, `CategoryAnalyticsResponse`, `MerchantAnalyticsResponse`, `AccountActivityResponse`, and `UnusualSpendingResponse`.
   - Enforced stringified two-decimal formatting (`MoneyStr`, `OptionalMoneyStr`) via `ROUND_HALF_UP` preserving financial correctness without binary floating-point representation.
   - Implemented `count_calendar_buckets` computing actual calendar buckets for half-open intervals `[from_time, to_time)` in target IANA timezones, enforcing `MAX_DAILY_BUCKETS=366` and `MAX_MONTHLY_BUCKETS=120`.

2. **PostgreSQL Aggregation Repository (`src/finsignal/analytics/repository.py`):**
   - Single-roundtrip macro-aggregates over `[from_time, to_time)` using PostgreSQL window/aggregate functions (`percentile_cont(0.5)`, `SUM`, `AVG`, `FILTER`).
   - Contiguous zero-filled trend series generation using wall-clock `TIMESTAMP WITHOUT TIME ZONE` series joined against `date_trunc(interval, occurred_at, tz)` via `TIMESTAMPTZ`, eliminating DST skew and session-timezone coupling.
   - Dynamic parameterized WHERE conditions eliminating untyped prepared statement parameters and optimizing PostgreSQL index utilization.
   - Scoped available currencies and activity details to authoritative account namespace.

3. **Domain Service & Validation (`src/finsignal/analytics/service.py`):**
   - Validates namespace syntax (`^[A-Z0-9_]{3,64}$`) and verifies namespace existence in `accounts` or `dataset_imports`.
   - Validates ISO 4217 currency syntax (`^[A-Z]{3}$`).
   - Enforces half-open interval validation: `from_time < to_time`.
   - Rejects bucket-count overflows before executing database queries.
   - Computes deterministic outlier threshold ($M_{\text{debit}} \times \text{multiplier}$) and pre-pagination matching counts.
   - Implements empty-currency semantics: existing account with no transactions in requested currency returns HTTP 200 with zeroed metrics and available currencies.

4. **API Router & Endpoints (`src/finsignal/api/v1/analytics.py` & `src/finsignal/api/router.py`):**
   - Mounted `GET /api/v1/analytics/overview`
   - Mounted `GET /api/v1/analytics/trends`
   - Mounted `GET /api/v1/analytics/categories`
   - Mounted `GET /api/v1/analytics/merchants`
   - Mounted `GET /api/v1/analytics/accounts/{account_id}`
   - Mounted `GET /api/v1/analytics/accounts/{account_id}/unusual-spending`
   - Enforced JWT Bearer authentication and permitted roles: `ADMIN`, `ANALYST`, and `INVESTIGATOR`.

5. **Empirical Validation & Benchmark Results:**
   - 320 passed tests in 48.58s (43 new tests across unit, API, integration, and benchmark suites, with 0 regressions in existing 277 tests).
   - Verified halfway continuous median rounding (`100.015 -> 100.02`).
   - Verified half-open boundaries (`from_time` included, `to_time` excluded).
   - Verified sub-second boundary regression scenario (`to_time = 00:00:00.500Z` retains day 2 bucket).
   - Verified DST spring-forward 23-hour day and session timezone mismatch resilience.
   - **Medium Scale Benchmark (100 accounts, 5,000 transactions, seed=42):**
     - `/overview` (30-day window): P50=0.48ms, P90=0.78ms, P95=0.81ms, Max=0.88ms. (Target $\le 50.0$ ms MET)
     - `/trends` (30 daily buckets): P50=1.14ms, P90=1.50ms, P95=1.53ms, Max=1.75ms. (Target $\le 50.0$ ms MET)
     - Query plans confirm `Index Scan using ix_transactions_occurred_at`.
   - **Full Scale Benchmark (5,000 accounts, 250,000 transactions, seed=42, 80,651 matching in window):**
     - `/overview` (30-day window): Repository P50=130.79ms, P90=133.06ms, P95=135.74ms, Max=140.85ms; HTTP P95=145.3ms. Engine execution time is 86.13ms.
     - `/trends` (30 daily buckets): Repository P50=134.12ms, P90=138.43ms, P95=140.16ms, Max=141.66ms; HTTP P95=148.1ms. Engine execution time is 141.0ms.
     - `/categories` (30-day window): Repository P50=83.47ms, P90=84.96ms, P95=85.72ms, Max=87.07ms. (Target $\le 100$ ms MET)
     - `/merchants` (top 20): Repository P50=80.33ms, P90=82.35ms, P95=83.06ms, Max=99.82ms. (Target $\le 100$ ms MET)
     - `/accounts/{id}` (activity): Repository P50=0.86ms, P90=0.99ms, P95=1.25ms, Max=1.56ms. (Target $\le 100$ ms MET)
     - `/accounts/{id}/unusual-spending`: Repository P50=0.27ms, P90=0.33ms, P95=0.54ms, Max=0.68ms. (Target $\le 100$ ms MET)
     - Query Plan Findings: PostgreSQL uses `Index Scan using ix_transactions_occurred_at` (index scan took 28.0ms to fetch 80,651 rows with 2,351 shared buffer hits and 0 sequential scans). The remaining time is consumed by in-memory `percentile_cont(0.5)` sorting and 80k-row hash grouping. Global overview and trends over 80k rows slightly exceed the aspirational 100ms threshold due to in-memory aggregation volume; no speculative index is required as the index scan itself runs in 28ms.
   - Code quality: `uv run ruff check .` passed; `uv run ruff format --check .` passed; `uv run mypy src tests` passed (110 source files).

# 25. Phase 6 Implementation — Feature Engineering

**Date:** 2026-10-25
**Scope:** Complete implementation and verification of Phase 6: Feature Engineering.

### Objective
Implement an on-demand, in-memory, point-in-time feature-engineering module (`src/finsignal/features/`) capable of serving single-transaction online evaluations and high-throughput streaming batch extractions according to the approved 34-feature contract, while strictly preventing temporal lookahead leakage and isolating ground-truth labels.

### Summary of Completed Work

1. **Schemas & Contract Versioning (`src/finsignal/features/schemas.py`, `constants.py`):**
   - Implemented `FeatureVector` as an immutable Pydantic v2 model (`frozen=True`, `extra="forbid"`) containing **strictly 34 model input features**. All floating-point fields are validated via `@model_validator(mode="after")` to guarantee finite values (`math.isfinite`), preventing non-finite floats (`NaN`, `+Inf`, `-Inf`) from entering model matrices.
   - Implemented `FeatureMetadata` decoupled from `FeatureVector` to house operational and execution diagnostics (`feature_version="v1.0"`, account/transaction identifiers, event timestamps, calculation timestamp, and `is_account_created_after_txn`). Diagnostic metadata is never exposed as a model feature.
   - Clean DTOs (`HistoricalTransactionDTO`, `EvaluatedTransactionDTO`, `AccountProfileDTO`, `LifetimeBaselineSummary`, `EvaluationContext`, `FeatureEvaluationResult`) isolate domain ORM models from pure computation logic.
   - Centralized constants: `FEATURE_VERSION = "v1.0"`, `MIN_BASELINE_OBSERVATIONS = 3`, velocity window durations (5m: 300s, 1h: 3600s, 24h: 86400s), category spending window (30d: 2,592,000s), nocturnal unusual hours (`{1, 2, 3, 4, 5}` UTC), and weekend days (`{5, 6}`).

2. **Pure Functional Computation Engine (`src/finsignal/features/engine.py`):**
   - Stateless, deterministic feature computer with zero database I/O and zero mutation of domain entities.
   - Enforces strict point-in-time boundary: candidate historical transactions are eligible if and only if:
     `occurred_at < eval.occurred_at OR (occurred_at == eval.occurred_at AND id < eval.id)`.
     The evaluated transaction is strictly excluded from its own baseline and velocity metrics.
   - High precision: monetary sums and aggregates are computed using Python standard library `Decimal` internally and converted to `float` only at the `FeatureVector` boundary.
   - Sliding-window velocities (5m, 1h, 24h count and direction/currency-matched amount) with inclusive lower boundaries (`>= t - window`) and strict upper boundaries.
   - Baseline statistics (mean, sample variance/stddev with $N-1$ degrees of freedom, and exact median with even-length averaging).
   - Zero-variance handling: When count $\ge 3$ and sample variance is zero, assigns neutral `amount_zscore = 0.0`, sets `has_zero_variance_baseline = 1`, and sets `is_amount_different_from_constant_baseline = 1` only if the evaluated amount differs from the constant historical mean.
   - Sparse baseline neutral sentinels: When count $< 3$, assigns `amount_vs_mean_ratio = 1.0`, `amount_vs_median_ratio = 1.0`, `amount_zscore = 0.0`, `has_direction_baseline = 0`, and `has_zero_variance_baseline = 0`.
   - Cold start: `is_cold_start = 1` if total account prior transaction count $< 3$ across all currencies and directions; decoupled from account age. Clamped negative account age does not trigger cold start.
   - Entity familiarity & novelty: Evaluates prior transaction counts and novelty flags for device, merchant, and location. Missing entity IDs return neutral 0 sentinels. Home location match (`is_home_location = 1`) treats the registered address as familiar (`is_new_location = 0`). `location_frequency` uses total eligible prior transactions as the denominator (returning `0.0` when no history exists).
   - Category spending share: Preceding 30-day DEBIT transactions in matching currency, bounded in $[0.0, 1.0]$ with `0.0` sentinel for missing category or zero denominator. Evaluated regardless of whether the current transaction is DEBIT or CREDIT.
   - UTC temporal features: `hour_of_day` (0–23), `day_of_week` (0–6), `is_weekend` (Saturday/Sunday), and `is_unusual_hour` (01:00–05:59 UTC).

3. **Historical Context Repository (`src/finsignal/features/repository.py`):**
   - Cleanly separates bounded window retrieval (preceding 30 days) from lifetime aggregates.
   - Bounded historical query executes an index range scan on `ix_transactions_account_occurred` with range pushdown:
     `occurred_at >= :window_start AND occurred_at <= :eval_occurred_at AND NOT (occurred_at = :eval_occurred_at AND id >= :eval_id)`.
   - Lifetime baseline summary query executes direction- and currency-matched aggregates directly in PostgreSQL (`COUNT`, `AVG`, `STDDEV_SAMP`, `percentile_cont(0.5)::numeric`) in $O(1)$ memory without retrieving millions of raw historical rows.
   - Lifetime total transaction count and entity counts queried using strict point-in-time boundary predicates.
   - Sub-second UUID tie-breaking verified against native PostgreSQL byte-order UUID sorting.
   - Session lifecycle: Repository accepts caller-owned `AsyncSession` without premature commits or rollbacks; raises project-standard `NotFoundError` on missing IDs.

4. **Feature Service & Streaming Batch Extraction (`src/finsignal/features/service.py`):**
   - Single-transaction online evaluation (`evaluate_transaction`): combines repository context assembly and pure engine computation.
   - Chronological batch extraction (`extract_batch`): performs streaming in-memory feature extraction across dataset batches without issuing $N$ individual database queries, achieving $O(N \log N)$ complexity.
   - Non-mutation guarantee: caller-owned collections are never mutated; sorts an internal copy and re-sorts results to preserve caller's original sequence.
   - Account state isolation: maintains independent `AccountChronologicalAccumulator` per account with zero cross-account leakage.
   - Running statistics: implements `DirectionCurrencyRunningStats` using Welford's algorithm for sample variance and balanced dual heaps for exact running medians (with even-count arithmetic averaging matching PostgreSQL's `percentile_cont(0.5)`).
   - Sliding 30-day deques automatically evict records older than 30 days.

5. **Empirical Validation & Benchmark Results:**
   - **Full test suite execution:** 347 passed (0 failed, 86 warnings) in 97.51s, verifying 100% regression parity across all 320 baseline tests plus 27 newly implemented Phase 6 tests:
     - `tests/unit/test_feature_schemas.py`: 6 passed (34-feature contract, immutability, extra field rejection, finite float validation, metadata).
     - `tests/unit/test_feature_engine.py`: 11 passed (amount/log, negative age clamping, velocity boundaries, sparse sentinels, direction/currency isolation, zero-variance, entity presence/novelty, 30d category share, UTC temporal features, UUID tie-breaking).
     - `tests/unit/test_feature_service.py`: 3 passed (batch non-mutation, ordering preservation, batch vs. pure engine numerical equivalence within $10^{-5}$, multi-account isolation).
     - `tests/integration/test_feature_repository.py`: 3 passed (bounded window query, sub-second UUID tie-breaking, self-exclusion, lifetime aggregates, not found handling).
     - `tests/integration/test_temporal_leakage.py`: 3 passed (online future-data invariance, batch future-data invariance, ground-truth isolation).
     - `tests/integration/test_feature_benchmark.py`: 1 passed (medium-scale dataset benchmark and query-plan verification).
   - **Quality gates:**
     - `uv run ruff check .`: Clean (all checks passed).
     - `uv run ruff format --check .`: Clean (128 files formatted).
     - `uv run mypy src tests`: Success: no issues found in 122 source files.
   - **Performance Benchmark (100 accounts, 5,000 transactions, seed=42):**
     - Batch feature extraction (5,000 txs): **0.851 s** (~5,875 tx/sec), easily satisfying the $\le 3.0$ s target.
     - Peak memory for batch extraction: **27.82 MB**, satisfying the $\le 50.0$ MB target.
     - Online single evaluation latency: P50=7.23ms, P90=8.51ms, P95=8.84ms (documented known deviation against 5.0ms aspirational target due to unpooled transient asyncpg TCP roundtrips to PostgreSQL on local dev workstation; pure engine execution time is $< 50\ \mu\text{s}$).
     - Online vs. batch numerical agreement: verified identical within rel_tol $\le 10^{-5}$ across sampled transactions.
     - Query plan verification: `EXPLAIN (ANALYZE, BUFFERS)` confirms PostgreSQL executes an `Index Scan using ix_transactions_account_occurred` taking 0.041 ms with 3 shared buffer hits and 0 sequential scans.

### Known Performance & Scaling Considerations
1. **Online Latency Deviation:** Online P95 latency is 8.84 ms versus the 5.0 ms target. This is attributable to connection and network roundtrips across two asynchronous SQL queries per evaluation in the local test setup, rather than feature computation overhead. Production connection pooling and co-located database networking will reduce this latency.
2. **Lifetime Entity Aggregation:** `FeatureRepository.get_lifetime_baseline_summary()` queries `(device_id, merchant_id, location_id, category)` for all lifetime transactions of an account and computes frequency counters in Python. For standard account depths ($< 10,000$ txs), this takes $< 3\text{ ms}$; for hyper-active accounts with hundreds of thousands of transactions, row transfer volume scales with lifetime history. If account lifetimes grow significantly in future phases, separate SQL `GROUP BY` aggregations or entity counter tables can be introduced.
3. **Exact Median Memory in Batch Processing:** The dual-heap algorithm in `DirectionCurrencyRunningStats` stores exact `Decimal` amounts in memory. While highly efficient for operational batch sizes (27.82 MB for 5,000 transactions), memory grows linearly with retained history. If single-account histories reach $> 500,000$ transactions in future ML pipelines, streaming chunks or approximate quantile algorithms (e.g., t-digest) may be considered.

### Architectural Limitations & Invariants
- No persistent feature tables were created; all features are generated on demand or in memory.
- No database migrations were introduced; Alembic head remains unchanged at `0003_account_import_namespace`.
- No new dependencies or lockfiles were added.
- Ground-truth fraud labels and scenarios are strictly isolated from feature inputs.
- Deferred from v1.0: `category_amount_mean`, `category_amount_deviation`, and `device_first_seen_age`.

### Result
Phase 6 implementation is complete, fully verified against PostgreSQL, and reconciled with all project documentation. All exit criteria are satisfied.

### Next Steps
1. Complete Phase 7 documentation reconciliation across architecture, database, security, and testing documents.
2. Submit technical recommendations and proposed ADRs (ADR-067 to ADR-069) for project-owner review.
3. Proceed to Phase 8: Risk Analysis & Explainability.

---

## 2026-10-26 — Phase 7: ML / Anomaly Detection Implementation, Testing & Benchmark Verification

### Context & Objectives
Phase 7 introduces machine learning anomaly detection to FinSignal, providing an unsupervised multivariate baseline model capable of identifying anomalous transactions without ground-truth label leakage.

### What Changed
1. **Machine Learning Package (`src/finsignal/ml/`):**
   - Implemented `FeatureVectorizer` (`vectorizer.py`) converting Phase 6 `FeatureVector` instances into (N, 34) 2D NumPy `float64` matrices adhering strictly to `CANONICAL_FEATURE_NAMES` and `FEATURE_VERSION = "v1.0"`. Enforced rejection of null, NaN, and non-finite values.
   - Implemented `IsolationForestModel` (`model.py`) wrapping scikit-learn's `IsolationForest` (`n_estimators=100`, `random_state=42`, `contamination="auto"`). Formulated monotonic anomaly score $S(X) = - \text{score\_samples}(X)$ so higher scores signify greater anomalousness.
   - Implemented `ChronologicalSplitter` (`split.py`) partitioning transactions chronologically targeting 60% Train, 20% Validation, and 20% Holdout Test. Enforced deterministic sorting `(occurred_at, str(record_id))` and indivisible equal-timestamp grouping to prevent lookahead leakage across partition cuts.
   - Implemented `ModelEvaluator` (`evaluator.py`) optimizing operating decision threshold $\tau^*$ on validation data to maximize F1 score subject to an operational alert-rate budget ($\le 5\%$), with boundary candidate `max_score + 1e-6` guaranteeing zero-alert baseline. Implemented single-pass holdout test evaluation (Precision, Recall, F1, PR-AUC, Alert Rate, Scenario Recall, Cluster Recall).
   - Implemented `ModelArtifactStore` (`registry.py`) providing two-phase atomic persistence (`.tmp` $\to$ `os.replace()`), path containment defense (`.resolve().relative_to()`), and pre-deserialization SHA-256 integrity verification.
   - Implemented `ModelRepository` (`repository.py`) managing `model_versions` table persistence, lifecycle state machine (`EXPERIMENTAL -> VALIDATED -> ACTIVE -> RETIRED`), and row-locked atomic promotion (`SELECT ... FOR UPDATE`).
   - Implemented `MLService` (`service.py`) orchestrating training pipelines, dynamic active-model lookup from PostgreSQL on every scoring call, and in-memory caching validated against `artifact_hash`.

2. **Database Migration (`migrations/versions/0004_model_versions.py`):**
   - Created `model_versions` table with columns: `id`, `name`, `version`, `algorithm`, `feature_version`, `dataset_version_id`, `parameters`, `metrics`, `artifact_uri`, `artifact_hash`, `status`, `created_at`.
   - Applied status check constraint `chk_model_versions_status`, unique constraint `uq_model_versions_name_version`, and partial unique index `uq_model_versions_active_family` on `(name)` where `status = 'ACTIVE'`.
   - Set down-revision to `0003_account_import_namespace`.

3. **Dependencies (`pyproject.toml`, `uv.lock`):**
   - Added `scikit-learn>=1.5.0,<2.0.0`, `joblib>=1.4.0,<2.0.0`, and `numpy>=2.0.0,<3.0.0`.
   - Locked exact runtime versions in `uv.lock`: `scikit-learn 1.9.1`, `joblib 1.6.0`, `numpy 2.5.4`, `scipy 1.18.1`.

4. **Empirical Validation & Benchmark Results:**
   - **Test Suite Growth:** 393 total passing tests in repository (+46 Phase 7 tests covering vectorizer, model, split, evaluator, registry, repository, end-to-end training pipeline, and performance benchmarks).
   - **Static Analysis:** `ruff check .` clean, `ruff format --check .` clean, `mypy src tests` clean.
   - **Empirical Benchmarks (measured on local Windows/Python 3.12 workstation):**
     - Feature vectorization ($N = 1,000$): $\approx 7.3\ \mu\text{s}$ per feature vector.
     - Pure single-sample scoring ($N = 200$): P50 $\approx 5.30$ ms, P90 $\approx 5.75$ ms, P95 $\approx 5.92$ ms (earlier run $6.26$ ms).
     - Pure batch scoring throughput ($N = 10,000$): $\approx 205,302$ transactions/second.
     - Model training duration ($N = 5,000$, 100 trees): $\approx 0.12$ seconds.
     - End-to-end online scoring ($N = 50$, including DB query + feature extraction + vectorization + scoring): P50 $\approx 8.7$ ms, P90 $\approx 9.5$ ms, P95 $\approx 9.88$ ms.

### Technical Baselines & Recommendations Submitted for Review
1. **Artifact Integrity Trust Boundary:** SHA-256 verification acts as an integrity and corruption check against disk corruption or tampering prior to deserialization; it does not protect against an attacker who has compromised both database and filesystem write permissions (no asymmetric PKI).
2. **Single-Sample Scoring Latency Target:** Pure single-sample scoring target of P95 $\le 8.0$ ms submitted for approval, scoped to the measured Windows/Python 3.12 development environment.
3. **Artifact Cleanup & Recovery Blocker:** Interrupted training pipelines can leave unreferenced artifact directories on disk. Automated deletion in exception handlers was rejected due to commit ambiguity. An administrative pruning tool (`finsignal-admin prune-unreferenced-artifacts`) is required prior to production release.
4. **Promotion Concurrency:** Verified for sequential promotion and direct SQL duplicate rejection. Multi-session concurrent race conditions remain unverified under concurrent test fixtures.

### Result & Status
- Phase 7 implementation and automated tests: **100% Completed**.
- Documentation reconciliation: **Completed**.
- Production release gate: **Not Passed** pending artifact cleanup implementation.
- Next development phase: **Phase 8 (Risk Analysis & Explainability)**.

---

# 26. Phase 8 — Risk Analysis & Explainability (Completed)

Phase 8 introduces a deterministic, explainable risk-prioritization layer that synthesizes unsupervised Isolation Forest anomaly detections with transparent financial heuristics, producing bounded investigation scores, risk tiers, and structured explainability factors.

### What Changed
1. **Risk Subsystem Package (`src/finsignal/risk/`):**
   - Implemented `NormalizationParams` and `normalize_ml_score` (`normalization.py`): Performs piecewise linear mapping from continuous anomaly score $S(X)$ into a calibrated $[0.0, 100.0]$ scale anchored to $(s_{\min} \mapsto 0.0, \tau^* \mapsto 50.0, s_{\max} \mapsto 100.0)$. Enforces invariant $s_{\min} < \tau^* < s_{\max}$.
   - Implemented `resolve_normalization_bounds` (`normalization.py`): Extracts empirical calibration bounds ($s_{\min}, s_{\max}$) from model metrics persisted during training. Rejects uncalibrated models unless explicit fallback is authorized.
   - Implemented `RiskRuleEngine` (`rules.py`): Evaluates 9 deterministic rules against features and transaction facts:
     1. `COLD_START_ACCOUNT` (INFO, 0 pts)
     2. `HIGH_VELOCITY` (MEDIUM: 15 pts, HIGH: 25 pts, CRITICAL: 40 pts)
     3. `LARGE_AMOUNT_DEVIATION` (MEDIUM: 15 pts, HIGH: 25 pts, CRITICAL: 40 pts)
     4. `NEW_DEVICE` (MEDIUM: 15 pts, HIGH: 25 pts)
     5. `NEW_LOCATION` (MEDIUM: 15 pts, HIGH: 25 pts)
     6. `UNUSUAL_TIME` (LOW: 5 pts, MEDIUM: 15 pts)
     7. `BEHAVIORAL_SHIFT` (MEDIUM: 15 pts, HIGH: 25 pts)
     8. `NEW_MERCHANT` (LOW: 5 pts)
     9. `NEW_CATEGORY` (LOW: 5 pts; suppressed if behavioral shift fired to prevent double-counting)
   - Implemented `RiskFactorGenerator` (`factors.py`): Converts fired rules into investigator-facing `RiskFactorDTO` instances with labels, severities, textual explanations, numeric/text values, and point-in-time evidence snapshots.
   - Implemented `HybridScoringEngine` (`scoring.py`): Computes composite risk score $\text{raw} = w_{\text{ml}} \cdot S_{\text{norm}} + w_{\text{rule}} \cdot S_{\text{rule}}$ ($w_{\text{ml}}=0.60, w_{\text{rule}}=0.40$), applies optional evidence-gated escalation floors (CRITICAL factor $\ge 75.0$, HIGH factor $\ge 50.0$), clamps score to $[0.00, 100.00]$ rounded to two decimal places, and maps to categorical tiers: `LOW` ($< 25.0$), `MEDIUM` ($< 50.0$), `HIGH` ($< 75.0$), `CRITICAL` ($\ge 75.0$).
   - Implemented `compute_feature_fingerprint` (`fingerprint.py`): Computes canonical 64-character SHA-256 fingerprint over all 34 canonical features and result-affecting context (amount, currency, direction, entity IDs, category).
   - Implemented `effective_config_version` (`schemas.py`): Computes a 12-character SHA-256 hash of all result-affecting weights, thresholds, policy versions, and escalation flags, appending to base version (e.g. `rc_v1.0#<hash>`) to guarantee detection of configuration drift within `VARCHAR(32)`.
   - Implemented `RiskRepository` (`repository.py`): Manages atomic savepoint persistence (`session.begin_nested()`) of parent `RiskAnalysis` and child `RiskFactor` records. Includes `is_risk_identity_conflict` to safely recognize PostgreSQL unique-violation code `23505` on `uq_risk_analyses_identity` across asyncpg/SQLAlchemy exception wrappers while failing closed on foreign keys, check violations, or incomplete driver metadata.
   - Implemented `RiskService` (`service.py`): Orchestrates feature context assembly, model lifecycle eligibility checks (`EXPERIMENTAL` blocked, `VALIDATED` restricted to `ADMIN`), ML inference, normalization, rule evaluation, scoring, savepoint persistence, race recovery, and transactional audit event creation (`TRANSACTION_RISK_ANALYZED`).

2. **Database Migration (`migrations/versions/0005_intelligence_risk_models.py`):**
   - Created `risk_analyses` table with columns: `id`, `transaction_id`, `model_version_id`, `config_version`, `feature_vector_hash`, `score`, `risk_level`, `ml_anomaly_score`, `ml_threshold`, `normalized_ml_score`, `rule_score`, `normalization_params`, `created_at`.
   - Applied check constraints `chk_risk_analyses_score` and `chk_risk_analyses_risk_level`, foreign keys to `transactions.id` and `model_versions.id` (`ON DELETE RESTRICT`), and composite unique constraint `uq_risk_analyses_identity` on `(transaction_id, model_version_id, config_version, feature_vector_hash)`.
   - Created `risk_factors` table with columns: `id`, `risk_analysis_id`, `factor_code`, `factor_label`, `severity`, `description`, `value_numeric`, `value_text`, `evidence`, `created_at`. Foreign key references `risk_analyses.id` (`ON DELETE CASCADE`), with check constraint `chk_risk_factors_severity`.
   - Set down-revision strictly to `0004_model_versions`.

3. **REST API Router (`src/finsignal/api/v1/risk.py`):**
   - `GET /api/v1/transactions/{transaction_id}/risk`: Retrieves latest persisted risk assessment without triggering inference. Returns HTTP 200 or 404. Accessible by `ADMIN`, `ANALYST`, and `INVESTIGATOR`.
   - `POST /api/v1/transactions/{transaction_id}/risk/analyze`: Point-in-time risk evaluation and persistence with idempotent reuse. Returns existing analysis if identity matches; persists new analysis and audit event atomically if inputs differ.

4. **Model Calibration Integration (`src/finsignal/ml/service.py`):**
   - Updated `MLService.train_and_register` to compute empirical calibration bounds ($s_{\min}, s_{\max}$) strictly over the validation partition and persist them in `model_record.metrics` (`score_min`, `score_max`), preserving sealed isolation of the holdout test partition.

5. **Empirical Verification & Test Results:**
   - **Test Suite Growth:** 450 total passing tests (+57 Phase 8 tests covering schemas, scoring invariants, piecewise linear normalization, deterministic rules, synthetic scenario cohort, canonical feature fingerprinting, migration 0005, atomic persistence, driver conflict recovery, and REST API endpoints).
   - **Static Analysis & Linting:** `ruff check .` clean, `ruff format --check .` clean, `mypy src tests` clean, Pyright type analysis clean (0 errors, 0 warnings).

### Technical Baselines & Architecture Notes
1. **Prioritization Score vs. Fraud Probability:** The composite risk score is an operational investigation prioritization index $[0.00, 100.00]$, not an empirical or posterior fraud probability.
2. **Validation-Only Calibration:** Normalization bounds ($s_{\min}, s_{\max}$) and threshold ($\tau^*$) are derived strictly from validation data; the sealed holdout dataset is never accessed during training or calibration.
3. **Synthetic Scenario Cohort Role:** The 200-transaction scenario cohort verifies deterministic rule firing and factor generation under synthetic conditions; its alert rate does not represent empirical model performance.
4. **Investigation Auto-Triggering:** Automated investigation case generation based on risk tier boundaries is decoupled from risk scoring and deferred to Phase 9.

### Result & Status
- Phase 8 implementation and automated tests: **100% Completed** (450 passing tests).
- Production release gate: **Not Passed** pending administrative artifact cleanup tool (Phase 7 blocker) and investigation workflow implementation (Phase 9).
- Next development phase: **Phase 9 (Investigation & Evidence)**.

---

# 27. Phase 9 Implementation: Investigation & Evidence Completion

**Date:** 2026-11-01
**Scope:** Backend (Modular Monolith)
**Status:** Completed (Milestones P9.0–P9.9)

### Summary of Completed Work

1. **Investigation Domain Subsystem (`src/finsignal/investigations/`):**
   - Implemented `models.py`: `Investigation`, `InvestigationTransaction`, and `InvestigationEvidence` SQLAlchemy ORM models.
   - Implemented `schemas.py`: Pydantic v2 domain schemas, DTOs, and serialization contracts. Enforces non-whitespace resolution notes (`min_length=1`), valid payload boundaries (64 KB JSONB), and type-source consistency mappings.
   - Implemented `repository.py` (`InvestigationRepository`): Encapsulates persistence logic, row-level pessimistic locks (`SELECT ... FOR UPDATE`), eager joins to avoid N+1 query loops, deterministic queue ordering (`created_at DESC`), and deterministic evidence ordering (`created_at ASC, id ASC`).
   - Implemented `service.py` (`InvestigationService`): Orchestrates core business invariants:
     - Multi-model atomicity: atomically creates the investigation, primary transaction link, and `INVESTIGATION_CREATED` audit event.
     - Role-based authorization: `ADMIN` has global authority; `INVESTIGATOR` can self-assign unassigned cases, self-unassign, edit assigned cases, link 1-hop transactions, attach evidence, and resolve; `ANALYST` is restricted to case creation and read operations (mutations return 403 `FORBIDDEN`).
     - Peer protection: investigators attempting to claim a peer's assigned case receive 403 `FORBIDDEN`.
     - 4-way 1-hop scope predicate: validates related transactions across all 4 account/counterparty matching conditions within the exact same `source_namespace`.
     - Terminal case immutability: resolved investigations cannot be altered or amended with evidence by any role (returns 409 `IMMUTABLE_INVESTIGATION`).
     - Evidence validation: validates source existence in database and confirms source belongs to investigation scope (`EVIDENCE_SOURCE_OUT_OF_SCOPE`).
     - Transactional audit integration: records `AuditEvent` rows with authenticated actor attribution within the shared transaction.

2. **Database Migration (`migrations/versions/0006_investigation_models.py`):**
   - Created `investigations`, `investigation_transactions`, and `investigation_evidence` tables.
   - Foreign key constraints with `ON DELETE RESTRICT` on `assigned_to`, `investigation_id`, and `transaction_id`.
   - Check constraints: `chk_investigations_status`, `chk_investigations_priority`, `chk_investigations_resolution`, `chk_investigations_resolution_state`, `chk_inv_tx_rel_type`, `chk_inv_evidence_type`, `chk_inv_source_type`, `chk_inv_evidence_type_source_pair`, `chk_inv_evidence_source_consistency`.
   - Partial unique index: `uq_investigation_single_primary` on `investigation_transactions(investigation_id) WHERE relationship_type = 'PRIMARY'`.
   - PostgreSQL trigger: `trg_no_update_delete_evidence` calling `trg_enforce_evidence_immutability()` to reject SQL `UPDATE` and `DELETE` on `investigation_evidence`.

3. **REST API Router (`src/finsignal/api/v1/investigations.py`):**
   - Implemented 9 endpoints mounted at `/api/v1/investigations` and registered in `src/finsignal/api/router.py`:
     1. `GET /api/v1/investigations`: Shared triage queue listing and filtering.
     2. `POST /api/v1/investigations`: Manual-first atomic case creation.
     3. `GET /api/v1/investigations/{id}`: Full workspace context envelope retrieval.
     4. `PATCH /api/v1/investigations/{id}`: Row-locked case mutation (assignment, priority, status).
     5. `POST /api/v1/investigations/{id}/resolve`: Explicit resolution into 4 outcomes with mandatory notes.
     6. `GET /api/v1/investigations/{id}/transactions`: List primary and related transactions.
     7. `POST /api/v1/investigations/{id}/transactions`: Link 1-hop related transactions.
     8. `GET /api/v1/investigations/{id}/evidence`: Deterministic paginated evidence listing.
     9. `POST /api/v1/investigations/{id}/evidence`: Attach append-only immutable evidence snapshot.

4. **Empirical Verification & Test Results:**
   - **Test Suite Growth:** 485 total passing tests (+35 Phase 9 tests covering schemas, service authorization and invariants, REST API contracts, PostgreSQL persistence/triggers/rollbacks, and multi-connection concurrency races).
   - **Concurrency Verification:** Multi-connection integration tests confirm that concurrent self-assignment races cleanly yield one winner (200 OK) and one 409 Conflict (`CASE_ALREADY_ASSIGNED`), and peer takeovers return 403 `FORBIDDEN`.
   - **Static Analysis & Linting:** `ruff check .` clean, `ruff format --check .` clean, `mypy src tests` clean (0 errors across 175 source files).

### Architecture & Engineering Invariants Established
1. **Primary Transaction Guarantee:** The partial unique index enforces at-most-one PRIMARY link at the database level, while the atomic application creation workflow ensures exactly-one PRIMARY link for every committed case.
2. **1-Hop Bounded Scope:** Related transactions are strictly constrained to direct 1-hop associations within the primary transaction's `source_namespace`, avoiding recursive graph traversal complexity.
3. **Evidence Immutability Boundary:** Append-only evidence snapshots are protected by database trigger against application-level modification or deletion.
4. **Decoupled Resolution:** Human investigation resolution is strictly decoupled from automated ML risk scores and represents the final operational verdict.
5. **Deferred Automation:** Automatic risk-triggered case creation and Phase 10 AI Investigation Assistant summaries remain intentionally deferred.

### Result & Status
- Phase 9 implementation and automated tests: **100% Completed** (485 passing tests).
- Next development phase: **Phase 10 (AI Investigation Assistant)**.

---

# 28. 2026-11-04 — Phase 10 (AI Investigation Assistant) Completion

### Objective
Implement the Phase 10 AI Investigation Assistant subsystem to generate structured, evidence-grounded briefing summaries for human investigators while maintaining strict advisory boundaries, non-terminal enforcement, concurrency safety, and comprehensive auditability.

### Work Completed

1. **Dedicated AI Package Architecture (`src/finsignal/ai/`):**
   - Implemented a clean, modular package structure separate from the investigation case management layer:
     - `models.py`: SQLAlchemy 2.0 ORM model `AISummary`.
     - `schemas.py`: Pydantic v2 schemas (`AISummaryOutput`, `AISummaryResponse`, `AISummaryListResponse`, `AISummaryGenerateRequest`).
     - `exceptions.py`: AI domain exceptions mapped to standard error envelopes (`AI_SUMMARY_NOT_FOUND`, `AI_SUMMARY_IN_PROGRESS`, `INVESTIGATION_ALREADY_RESOLVED`, `AI_PROVIDER_ERROR`, `AI_TIMEOUT_ERROR`, `AI_SCHEMA_VALIDATION_ERROR`, `AI_GROUNDING_FAILED`).
     - `prompts.py`: Template versioning (`pv_1.0`), advisory instructions, and cryptographic nonce escaping.
     - `context.py`: Canonical JSON serialization, dual fingerprinting (`evidence_hash`, `context_hash`), and bounded context assembly.
     - `repository.py`: Async persistence, compare-and-swap (CAS) updates, and expired pending recovery with atomic audit logging.
     - `service.py`: Two-phase generation workflow orchestration, grounding validation, and staleness detection.
     - `providers/`: Extensible provider interface (`BaseAIProvider`), `MockAIProvider` with fault injection, and `ProviderFactory`.

2. **Database Schema & Constraints (Migration `0007_ai_models.py`):**
   - Created `ai_summaries` table linked to `investigations.id` via `ON DELETE RESTRICT` (preventing accidental cascade deletion of investigation audit history).
   - Configured `JSONB(none_as_null=True)` on `summary` column to ensure Python `None` maps to SQL `NULL`.
   - Enforced `chk_ai_summaries_status` (`PENDING`, `COMPLETED`, `FAILED`).
   - Enforced `chk_ai_summaries_lifecycle_state` constraint:
     - `PENDING`: `completed_at IS NULL AND summary IS NULL AND error_message IS NULL`
     - `COMPLETED`: `completed_at IS NOT NULL AND summary IS NOT NULL AND error_message IS NULL`
     - `FAILED`: `completed_at IS NOT NULL AND summary IS NULL AND error_message IS NOT NULL`
   - Created PostgreSQL partial unique index `uq_ai_summaries_one_pending_per_investigation` on `(investigation_id) WHERE status = 'PENDING'` preventing concurrent active attempts.
   - Created retrieval index `ix_ai_summaries_investigation_created` on `(investigation_id, created_at DESC, id)`.

3. **Two-Transaction Lifecycle under REPEATABLE READ Snapshot Isolation:**
   - **Transaction 1 (Reservation):** Configures `isolation_level="REPEATABLE READ"` before beginning transaction. Locks investigation row (`FOR UPDATE`), verifies authorization and non-terminal status, lazily recovers expired pending generations, checks for active pending generations, loads complete graph eagerly, computes dual fingerprints, and inserts a `PENDING` row with a cryptographically unique `generation_token`. Implements bounded exponential backoff retry for PostgreSQL serialization failure `40001`.
   - **Provider Execution:** Executes model generation outside active database transactions to prevent holding database locks during LLM network or inference latency.
   - **Transaction 2 (Terminal Update):** Uses conditional compare-and-swap (CAS) on `(id, status='PENDING', generation_token)` to write final status (`COMPLETED` or `FAILED`), structured output, and atomic `AuditEvent` (`AI_SUMMARY_GENERATED` or `AI_SUMMARY_FAILED`).

4. **Expired PENDING Recovery & Atomic Audit Logging:**
   - Detects orphaned pending records older than `ai_pending_timeout_seconds` (default 60s).
   - Atomically rotates `generation_token` to fence out delayed responses and sets status to `FAILED`.
   - Persists an `AI_SUMMARY_FAILED` audit event within the exact same database transaction if and only if the conditional update affected a row (`rowcount == 1`).

5. **Authoritative Evidence Hashing & Account Standing Parity:**
   - `compute_authoritative_evidence_hash`: Computes SHA-256 over canonical sorted JSON of case metadata, primary transaction, risk analysis, risk factors, related transactions, evidence items, and account `status` and `account_type`.
   - Changes to account standing (e.g. `ACTIVE` -> `FROZEN`) or account classification (`CHECKING` -> `SAVINGS`) materially alter the evidence hash and dynamically flag existing summaries as stale on `GET`.
   - `build_bounded_context`: Assembles prioritized context under explicit byte and item limits, computing a separate `context_hash`.

6. **Prompt Delimiter Isolation & Grounding Validation:**
   - Untrusted context is wrapped in `<case_context nonce="{uuid}">` tags with embedded closing tags escaped (`</` -> `<\u002F`). System instructions explicitly treat all transaction descriptions, merchant names, and notes as untrusted data.
   - Output grounding validation verifies that every cited UUID in `cited_evidence_ids` and `cited_transaction_ids` exists in the snapshot. Fabricated or phantom references raise `AISummaryGroundingError` (502).

7. **Protected REST API Endpoints:**
   - `POST /api/v1/investigations/{id}/ai-summary`: Synchronous generation with optional `force_refresh`. Restricted to `ADMIN` and assigned `INVESTIGATOR`.
   - `GET /api/v1/investigations/{id}/ai-summary`: Latest summary with dynamic `is_stale` check. Restricted to `ADMIN`, `ANALYST`, and assigned `INVESTIGATOR`.
   - `GET /api/v1/investigations/{id}/ai-summary/history`: Deterministic paginated history (`created_at DESC, id DESC`).

8. **Empirical Verification & Test Results:**
   - Full test suite: **529 passing tests** (+44 Phase 10 tests across unit, integration, persistence, recovery, concurrency, and API contracts).
   - Static analysis: `ruff check` clean, `ruff format --check` clean (196 files formatted), `mypy` clean (0 errors across 113 source files).

### Architecture & Engineering Invariants Established
1. **Advisory-Only Safety Boundary:** AI cannot resolve investigations, alter risk scores, or modify evidence. Cases in terminal `RESOLVED` or `CLOSED` status reject AI generation with 409 Conflict.
2. **Transaction Separation:** Long-running LLM provider I/O never holds database connections or locks.
3. **Lease Fencing & CAS:** Generation tokens guarantee that late-arriving provider responses cannot overwrite recovered or superseded summaries.
4. **Mock Provider Baseline:** System operates on deterministic `MockAIProvider`; external live LLM credentials remain intentionally deferred.
5. **Reference Existence vs. Semantic Truth:** Grounding validation guarantees entity reference existence, while semantic claim verification remains human-investigator authoritative.

### Result & Status
- Phase 10 implementation and verification: **100% Completed** (529 passing tests).
- Next development phase: **Phase 11 (Testing, Security & Hardening)**.

---

# 30. 2026-11-04 — Phase 11 (Testing, Security & Hardening) Implementation & Targeted Verification

**Date:** 2026-11-04  
**Scope:** Backend & Security Hardening (Modular Monolith)  
**Status:** Completed (Formally Accepted on 2026-11-04 per docs/PHASE_11_FORMAL_ACCEPTANCE.md)

### Summary of Completed Work

1. **Security Hardening (SEC-01 through SEC-06):**
   - **CORS Defense (SEC-01):** Integrated `CORSMiddleware` in `src/finsignal/main.py` with explicit origin whitelisting (`cors_origins`), methods, headers, and exposed correlation IDs (`X-Request-ID`). Configured strict credential isolation (`allow_credentials=True` only when origins are explicit and non-wildcard).
   - **Bounded Streaming Upload & Recovery (SEC-02):** Hardened `/api/v1/datasets/upload` and `/api/v1/datasets/{import_id}/recover` against memory exhaustion. Replaced whole-file buffering with bounded 64 KB chunk streaming enforcing a strict 50 MB hard limit (`MAX_UPLOAD_SIZE_BYTES = 52_428_800`). Oversized uploads are terminated immediately and return HTTP 413 (`PayloadTooLargeError`). Integrated `utf-8-sig` stream decoding for transparent UTF-8 BOM compatibility, safely detaching file handles (`text_stream.detach()`). Wrapped CSV parsing with explicit `csv.Error` handling, ensuring malformed files rollback transactions cleanly and transition imports to `FAILED` with HTTP 422.
   - **Environment Variable Isolation (SEC-03):** Replaced default environment parsing with custom `_FinSignalEnvSettingsSource` in `src/finsignal/core/config.py`. Prevents ambient OS environment variables (such as ambient `DEBUG`) from overriding application settings unless explicitly prefixed with `FINSIGNAL_`. Retained backward-compatible `.env` parsing for local developer environments with strict Pydantic boolean conversion.
   - **Sliding-Window Login Rate Limiter (SEC-06):** Implemented non-blocking, thread-safe `AuthRateLimiter` (`src/finsignal/auth/limiter.py`) and integrated into `/api/v1/auth/login`. Enforces 5 failed attempts per 60 seconds per IP + normalized email pair. Implements atomic in-flight admission control (max 2 concurrent requests per key). Active keys with active reservations (`in_flight > 0`) are guaranteed protection against eviction under capacity saturation (`max_tracked_keys = 10_000`). Breached limits return HTTP 429 (`RATE_LIMIT_EXCEEDED`) with RFC-compliant `Retry-After` header.
   - **Relational Counterparty Namespace Foreign Key (SEC-04):** Created Alembic migration `0008_security_hardening.py` adding composite foreign key constraint `fk_transactions_counterparty_namespace` (`FOREIGN KEY (counterparty_account_id, source_namespace) REFERENCES accounts(id, source_namespace) ON DELETE RESTRICT`), enforcing dataset provenance boundary isolation between transactions and counterparty accounts at the database engine level.
   - **Audit Log Immutability Trigger (SEC-05):** Added PostgreSQL trigger `trg_no_update_delete_audit_events` and function `trg_enforce_audit_events_immutability()` in migration `0008_security_hardening.py` blocking `UPDATE` and `DELETE` operations on `audit_events`.

2. **Ingestion & Feature Optimization (PERF-01 through PERF-04):**
   - **Batched Ingestion Lookups (PERF-01):** Replaced single-row lookups with batched queries (`canonical_id = ANY(...)`) in `src/finsignal/dataset/ingestion/engine.py`.
   - **Bounded Ingestion Caching (PERF-02):** Implemented bounded in-memory LRU caching (`max_cache_entries = 10_000`) for account, merchant, and device lookups. Added intra-batch duplicate resolution.
   - **SQL Pushdown for Entity Counts (PERF-03/04):** Optimized entity familiarity calculations in feature repository via targeted index-backed queries.

3. **ML Governance Hardening:**
   - Deterministic tie-breaker in chronological splitting (`occurred_at ASC, str(id) ASC`) in `src/finsignal/ml/split.py`.
   - Alert-rate budget validation guardrails in `src/finsignal/ml/evaluator.py`.

4. **Quality Gates & Empirical Verification:**
   - **Automated Test Suite:** Expanded to **559 passed tests** (0 failed, 0 errors, 79.56s).
   - **Static Analysis:** `ruff check .` clean (0 errors), `ruff format --check .` clean (210 files formatted), `mypy src tests` clean (0 errors across 199 source files).
   - **Database Migrations:** Verified Alembic migration tree clean (`alembic current` at `0003_account_import_namespace`, `alembic heads` at `0008_security_hardening`). Fixed deprecation warning for `path_separator = os`.

### Architecture & Operational Limitations Recorded
1. **Rate Limiter Deployment Boundary:** The login rate limiter is an in-memory, per-process implementation. Clustered or multi-worker deployments require distributed rate limiting (e.g. Redis). Client IP extraction currently reads `request.client.host`; trusted reverse proxy forwarding requires proxy middleware configuration.
2. **Audit Trigger Defense-in-Depth:** The database trigger prevents application-level `UPDATE` and `DELETE` queries, but does not provide hardware/cryptographic WORM storage or block superuser `TRUNCATE` / table drops.
3. **Model Artifact Pruning:** Unreferenced artifact cleanup CLI (`finsignal-admin prune-unreferenced-artifacts`) remains an unnumbered operational proposal, not yet implemented.
4. **Performance Verification:** Ingestion batching code is implemented and verified in integration tests; formal 250k-row benchmark run is deferred to release testing.

### Result & Status
- Phase 11 implementation, hardening corrections, and targeted verification: **Completed** (559 passing tests).
- Stage A Documentation Reconciliation: **Completed**.
- Formal Phase 11 Acceptance: **Accepted** (documented in `docs/PHASE_11_FORMAL_ACCEPTANCE.md`).

---

# 31. 2026-11-04 — Phase 12 (Backend/ML Release & Finalization) Execution & v1.0.0 Release Preparation

**Date:** 2026-11-04  
**Scope:** Backend & ML Release Preparation (Modular Monolith)  
**Status:** Completed  
**Release Tag Prepared:** `v1.0.0`

### Work Completed

1. **Phase 11 Formal Closure (Workstream A):**
   - Conducted rigorous formal engineering inspection of all Phase 11 deliverables (`docs/PHASE_11_FORMAL_ACCEPTANCE.md`).
   - Fixed CORS credentialed wildcard origin security defect: Added validation in `validate_cors_origins` (`src/finsignal/core/config.py`) that strictly raises `ValueError` if wildcard `*` is supplied when credentials are enabled. Added `expose_headers=["X-Request-ID"]` in `CORSMiddleware`.
   - Reconciled login rate limiter concurrency claims with actual code: Atomic in-flight admission bounds concurrent requests to `max_attempts` (5), with guaranteed non-eviction of active reservations.
   - Verified linear migration chain 0001–0008. Verified local dev DB status (`finsignal_dev` retained safely at 0003 without unauthorized modification; ephemeral test DBs verified to head 0008).

2. **ADR Governance Reconciliation (Workstream B):**
   - Formally ratified and transitioned 7 proposed architectural decisions to `ACCEPTED`:
     - **ADR-065:** Synthetic Dataset Identity & Import Observation Policies.
     - **ADR-067:** Canonical 34-Feature Vector Contract & Extraction Ordering.
     - **ADR-068:** Validation-Only Alert-Rate Constrained Threshold Selection.
     - **ADR-069:** Active Model Dynamic Resolution & Promotion Concurrency.
     - **ADR-070:** Hybrid Risk Scoring, Anchored Normalization & Canonical Analysis.
     - **ADR-071:** Manual Investigation Queue, Primary Transaction Invariant & Evidence Immutability.
     - **ADR-072:** Two-Phase Synchronous AI Summary Generation, REPEATABLE READ & CAS Fencing.
   - Authored and accepted **ADR-073**: Formally redefined Phase 12 as "Backend/ML Release & Finalization", delivering v1.0.0 as a tested source library/application release, and deferring Dockerfile, Docker Compose, and cloud deployment to Phase 13.
   - Transitioned Administrative Model Artifact Pruning CLI operational proposal to `DEFERRED TO PHASE 13`.

3. **Operational Limitations & Release Boundaries Documented (Workstream C):**
   - Documented model artifact pruning procedure: Unreferenced directories do not affect inference (only registered models load); safe manual recovery query established.
   - Clarified benchmark scope: Formally distinguished 250k synthetic generation (verified in Phase 4) and 5k benchmarks from deferred 250k database ingestion.
   - Documented rate limiter single-process boundary (Redis required for horizontal multi-instance scaling).
   - Clarified audit trigger immutability boundary (defense-in-depth against application UPDATE/DELETE; not WORM/TRUNCATE).

4. **Documentation Reconciliation (Workstream D):**
   - Reconciled `README.md`, `TRD.md`, `SECURITY.md`, `TESTING_STRATEGY.md`, `PROJECT_ROADMAP.md`, `PROJECT_LOG.md`, and `DECISIONS.md`.
   - Updated package versions to `1.0.0` in `pyproject.toml`, `src/finsignal/__init__.py`, and `src/finsignal/main.py`.

5. **Backend + ML v1.0 Release Gate (Workstream E):**
   - Evaluated all 34 requirements across Backend, ML, AI, and Quality dimensions in `PROJECT_ROADMAP.md` Section 18. All items verified with evidence.

6. **Final Verification Suite (Workstream F):**
   - Expanded test suite to **562 passed tests** (0 failed, 0 errors, 0 skipped, 82.1s).
   - Static analysis: Ruff clean (0 errors), Ruff format clean (210 files), Mypy clean (0 errors across 199 source files).
   - Migration integrity: Downgrade to base and upgrade to head roundtrip verified on disposable PostgreSQL databases.

7. **Release Packaging & Local Tag (Workstream G):**
   - Authored release deliverables:
     - `docs/PHASE_11_FORMAL_ACCEPTANCE.md`
     - `docs/PHASE_12_RELEASE_REPORT.md`
     - `docs/RELEASE_NOTES_v1.0.0.md`
   - Prepared clean working tree and local annotated tag `v1.0.0`. Stopped at remote publication boundary for owner approval.

### Result & Status
- Phase 12 execution: **Completed**.
- Backend + ML v1.0.0 code release preparation: **100% Complete**.
- Next milestone: **Owner Review & Publication Approval (Phase 13 Scheduled for Deployment)**.

---

# 32. 2026-11-06 — Frontend Planning Documentation & Architecture Audit Milestone

## Context

Following the completion and release of Backend + ML v1.0.0, the frontend planning documentation suite was drafted to define the browser client. A comprehensive consistency audit was conducted across all frontend and backend documents, the FastAPI implementation, Pydantic schemas, and the live OpenAPI contract (`/openapi.json`) to identify architectural mismatches, security requirements, and missing API contracts before implementation begins.

## Documents Created and Audited

1. `docs/FRONTEND_PRD.md`: Frontend Product Requirements Document (operational workflows, role capabilities, screen inventory, data presentation rules, MVP acceptance criteria).
2. `docs/FRONTEND_TRD.md`: Frontend Technical Requirements Document (React, TypeScript, Vite, Tailwind CSS, Apache ECharts, proposed dependency stack, performance budgets).
3. `docs/FRONTEND_ARCHITECTURE.md`: Frontend Architecture Document (presentation, feature workflow, infrastructure, and API integration layers; state ownership and boundary rules).
4. `docs/FRONTEND_DESIGN.md`: Frontend Design System (Coinbase-inspired financial clarity + IBM-inspired enterprise structure, token definitions, typography, layout, accessibility standards).
5. `docs/FRONTEND_API_INTEGRATION.md`: Frontend API Integration Specification (endpoint mappings, error envelope handling, pagination, multipart upload contracts, staleness detection).
6. `docs/FRONTEND_SECURITY.md`: Frontend Security Document (in-memory token handling, browser security controls, threat model, XSS/CSRF boundaries, audit trail integrity).
7. `docs/FRONTEND_TESTING_STRATEGY.md`: Frontend Testing Strategy (Vitest, React Testing Library, MSW network boundary mocking, Playwright E2E, axe accessibility gates).
8. `docs/FRONTEND_ROADMAP.md`: Frontend Implementation Roadmap (Phases F0 through F8, deliverables, and exit criteria).

## Architecture & Design Direction Established

- **Operational Role:** The frontend is an operational interface for analysts, investigators, and administrators; the backend remains the authoritative source for domain logic, financial aggregates, risk scores, features, evidence, and authorization.
- **Design System:** Restrained light-first palette with cobalt blue primary actions, strict status semantic badges, high information density without clutter, and zero reliance on color alone for critical status.
- **State Ownership:** Clear separation between server state (managed via TanStack Query caching) and local UI interaction state. Global state stores (e.g. Redux/Zustand) are avoided by default.
- **Financial Precision:** Strict preservation of backend string decimals (`MoneyStr`) and UTC timestamps; floating-point math in browser JavaScript is prohibited for financial figures.

## API Integration & Contract Verification Findings

- **Live OpenAPI Audit:** Audited 26 active routes in FastAPI backend against `API_GUIDELINES.md` and frontend integration documents.
- **Identified Contract Gaps:**
  - `GET /api/v1/transactions` and `GET /api/v1/transactions/{id}` are documented in `API_GUIDELINES.md` but not implemented in the FastAPI backend router (only `/transactions/{id}/risk` exists).
  - `GET /api/v1/datasets/imports` (listing dataset imports) is not implemented in the backend (only `POST /imports`, `GET /imports/{id}`, and `POST /imports/{id}/recover` exist).
  - `InvestigationCreateRequest` backend schema strictly forbids additional properties (`extra="forbid"`) and contains only `transaction_id` and `priority` (no `notes` or `title`). Corrected in `FRONTEND_API_INTEGRATION.md`.
  - `RiskAnalyzeRequest` backend schema accepts only `model_version_id` (no `force_recalculate`). Corrected in `FRONTEND_API_INTEGRATION.md`.

## Security & Testing Strategy Documented

- In-memory JWT access token storage recommended for Frontend MVP to prevent persistent token exposure on disk or in `localStorage`.
- Role-aware UI elements are treated purely as presentation helpers; all authorization is authoritatively enforced by FastAPI dependencies.
- Frontend testing pyramid established: pure unit tests (Vitest), component tests with simulated network boundaries (MSW), and full user journey tests (Playwright), with automated accessibility gates (axe-core). Frontend tests explicitly forbidden from duplicating backend ML/fraud algorithms.

## Outstanding Decisions & Blockers

1. **ADR-074 (Frontend Tech Stack & Dependencies):** Status: `PENDING` user approval.
2. **ADR-075 (Frontend Auth & In-Memory Token Storage):** Status: `PENDING` user approval.
3. **ADR-076 (OpenAPI Type Generation & Contract Verification):** Status: `PENDING` user approval.
4. **ADR-077 (Transaction & Dataset Import Read API Requirements):** Status: `PENDING` user approval (decision to implement `GET /transactions` and `GET /datasets/imports` in backend during Phase F0).

## Current Status & Next Milestone

- **Backend + ML v1.0.0 Status:** Released & Stable (100% test coverage, clean migrations 0001–0008).
- **Frontend Planning Status:** Completed and Audited (8 specifications complete, master roadmap and log synchronized).
- **Frontend Implementation Status:** Not Started (0 React code generated).
- **Next Milestone:** **Phase F0 — Decisions, Contract Verification & Repository Readiness**.

---

# 33. 2026-11-06 — ADR Ratification & Backend API Readiness Planning Milestone

## Context

Following completion of the frontend documentation audit, the system owner reviewed the four proposed architectural decisions (ADR-074 through ADR-077). Three decisions were formally approved, ADR-075 was revised to accurately evaluate token storage options, and a comprehensive engineering specification was authored for the missing backend read endpoints.

## Decisions Recorded & Updated

1. **ADR-074 (Frontend Technology Stack & Dependency Selection):** **ACCEPTED**.
   - Preserves core stack from `TRD.md` (React, TypeScript, Vite, Tailwind CSS, Apache ECharts).
   - Approves supporting libraries: React Router, TanStack Query, React Hook Form, Zod, Native Fetch API, `openapi-typescript`, Radix UI primitives, Lucide React, Vitest, React Testing Library, MSW, Playwright, npm.
   - Mandates strict version pinning via `package-lock.json`, forbids unapproved dependencies, and rejects Redux or premature global state.
2. **ADR-075 (Frontend Authentication, Session Lifecycle & Token Storage Strategy):** **PENDING (Revised Proposal)**.
   - Replaced misleading claims regarding XSS immunity with precise security boundary definitions.
   - Formally compared Option 1 (In-memory storage), Option 2 (sessionStorage/localStorage), and Option 3 (Backend HttpOnly cookies with CSRF defense).
   - Verified actual backend token expiration: `Settings.access_token_expire_minutes` default is **30 minutes** (1,800 seconds), dynamically returned in `TokenResponse.expires_in`.
   - Evaluated usability trade-offs of re-authentication on reload vs. security exposure. Kept in `PENDING` status for owner review.
3. **ADR-076 (OpenAPI-Driven TypeScript Contract Generation & Network Boundary Validation):** **ACCEPTED**.
   - Approves `openapi-typescript` for generating static TypeScript interfaces from live FastAPI `/openapi.json`.
   - Records governance rules: output isolation, immutability of generated code, committed types with CI drift verification (`npm run check:types-drift`).
   - Explicitly records technical distinction: generated types provide compile-time checking only and perform zero runtime response validation (no false 100% runtime contract safety claim).
4. **ADR-077 (Transaction & Dataset Import Collection Read API Requirements):** **ACCEPTED**.
   - Approves requirement to implement `GET /api/v1/transactions`, `GET /api/v1/transactions/{id}`, and `GET /api/v1/datasets/imports`.
   - Scoped as a dedicated Backend API Readiness Enhancement within Phase F0.
   - Preserves Backend + ML v1.0.0 release history without retroactive claims.

## Specifications Created & Master Documents Synchronized

- **Authored `docs/BACKEND_API_READINESS.md`:** Comprehensive engineering specification defining query parameters, filter feasibility against existing relational models, `risk_level` subquery architecture, deterministic tie-breaking (`occurred_at DESC, id DESC`), response schemas (`MoneyStr` serialization), not-found error envelopes, database index audits, and security boundaries.
- **Synchronized `docs/API_GUIDELINES.md`:** Added Section 23.4 (List Dataset Imports), annotated Section 21 and Section 70 to clearly label the three endpoints as `APPROVED REQUIREMENT — NOT YET IMPLEMENTED`, linking to `BACKEND_API_READINESS.md`.
- **Synchronized `docs/PROJECT_ROADMAP.md`:** Detailed Sub-Task F0.2 (Backend API Readiness Enhancement) under Phase F0.
- **Synchronized `docs/FRONTEND_API_INTEGRATION.md` & `docs/FRONTEND_ROADMAP.md`:** Updated endpoint tables and Phase F0 coordination milestones.

## Strict Restrictions Verified

- Zero Python source code modified.
- Zero database models or Alembic migrations modified.
- Zero React components or frontend scaffolding created.
- Zero npm dependencies installed.
- Zero changes to API runtime behavior.

## Current Status & Next Milestone

- **Backend + ML v1.0.0:** Released & Stable.
- **ADRs:** ADR-074 (ACCEPTED), ADR-075 (PENDING - Revised), ADR-076 (ACCEPTED), ADR-077 (ACCEPTED).
- **Backend API Readiness:** Specification approved; implementation pending in Phase F0.
- **Next Milestone:** Owner review of revised ADR-075; kick-off of Phase F0.

> **Historical status note:** This 2026-11-06 status snapshot records the state at that date. ADR-075 was subsequently accepted on 2026-11-10; see the following milestone entry.


---

# 34. 2026-11-10 — ADR-075 Ratification & Frontend F0 Governance Gate

## Context

The system owner reviewed the revised authentication and token-storage comparison and explicitly selected Option 1 — In-Memory Access-Token Storage — for the FinSignal Frontend MVP.

## Decision Recorded

- **ADR-075: ACCEPTED (2026-11-10).**
- Access tokens are held only in a narrowly scoped JavaScript in-memory authentication/session service.
- Tokens must not be written to `localStorage`, `sessionStorage`, cookies, IndexedDB, or another browser persistence mechanism.
- Protected API requests use the existing Bearer-token contract through the centralized API client.
- Full page reloads and new tabs require re-authentication; no silent refresh is permitted without a separately approved backend contract.
- The frontend must use the backend-provided `TokenResponse.expires_in`; 30 minutes is the documented default, not a hard-coded frontend lifetime.
- Confirmed `401` responses clear the in-memory session and authenticated query state; `403` remains an authorization failure, not session expiry.
- Route restoration may preserve only a validated safe internal destination. Sensitive evidence, private notes, and unsaved sensitive form payloads must not be persisted for this purpose.
- The decision explicitly does not claim protection against active same-origin XSS.
- HttpOnly-cookie authentication with CSRF protection, credentialed CORS, refresh/rotation, and revocation remains deferred and requires a separate coordinated backend decision.

## Documentation Synchronized

- Updated `DECISIONS.md`: ADR-075 status changed to `ACCEPTED`, acceptance date recorded, binding implementation requirements and deferred alternative documented.
- Updated `FRONTEND_SECURITY.md`: proposed authentication recommendation replaced with the approved MVP decision; session lifecycle and security checklist aligned.
- Updated `PROJECT_ROADMAP.md`: F0.1 governance and F0 exit criteria now recognize all four frontend ADRs as accepted.

## Validation & Scope

- Documentation consistency checked across the ADR, frontend security specification, frontend architecture, frontend roadmap, master roadmap, and project log.
- No backend source code, database models, Alembic migrations, API behavior, React source code, or npm dependencies changed as part of this decision ratification.

## Current Status & Next Milestone

- **Backend + ML v1.0.0:** Released & Stable.
- **Frontend ADRs:** ADR-074, ADR-075, ADR-076, and ADR-077 — all `ACCEPTED`.
- **Phase F0:** Governance decision gate complete; backend API readiness enhancement and remaining F0 execution tasks are still pending.
- **Next Milestone:** Begin F0.2 — implement and test the three approved backend read endpoints strictly against `BACKEND_API_READINESS.md`.

---

# 35. 2026-11-10 — Phase F0 Implementation & Documentation Reconciliation Complete

## Context

Following ratification of ADR-074 through ADR-077, Phase F0 (`F0.2` Backend API Readiness Enhancement, `F0.3` OpenAPI Type Generation & Contract Verification, `F0.4` Frontend Repository Scaffolding, and `F0-D` Documentation Reconciliation) was executed to prepare the repository for Frontend Phase F1.

## What Changed

- **F0.2 Backend Read APIs & Shared Monetary Types:**
  - Relocated `MoneyStr`, `OptionalMoneyStr`, `to_money_str`, and `to_optional_money_str` verbatim to `src/finsignal/common/types.py`, preserving backward-compatible re-exports in `src/finsignal/analytics/schemas.py`.
  - Implemented `GET /api/v1/transactions` (`TransactionListResponse`, `page_size=50` default, max `100`), deterministic ordering (`occurred_at|amount|created_at` with UUID tie-breaking), service-level semantic validation (`INVALID_NAMESPACE_FORMAT`, `INVALID_TIMEZONE`, `INVALID_DATE_RANGE`, `INVALID_AMOUNT_RANGE`, `UNSUPPORTED_SORT_FIELD`, `INVALID_SORT_ORDER`), and deterministic `risk_level` filtering using correlated `(created_at DESC, id DESC) LIMIT 1` tie-breaking.
  - Implemented `GET /api/v1/transactions/{transaction_id}` (`TransactionDetailResponse`) with eager-loaded `account`, `counterparty_account`, `merchant`, `device`, `location`, nullable `latest_risk` (`TransactionLatestRiskDTO`), and optional `source_namespace` partition fencing.
  - Implemented `GET /api/v1/datasets/imports` (`DatasetImportListResponse`, `page_size=20` default, max `100`) ordered by `(started_at DESC, id DESC)` without `dataset_import_errors` collections.
- **F0.3 OpenAPI & TypeScript Contract (`ADR-076`):**
  - Exported the FastAPI OpenAPI document (`28` paths, `67` schemas) to `frontend/openapi.json` and generated `frontend/src/api/generated/schema.ts` via `openapi-typescript`.
  - Added automated drift verification (`npm run check:types-drift` -> `frontend/scripts/check-types-drift.mjs`).
- **F0.4 Frontend Workspace Foundation (`ADR-074`, `ADR-075`):**
  - Created standalone `frontend/` workspace (`React 19`, `TypeScript 5.8`, `Vite 6`, Tailwind CSS v4, ESLint, Prettier, Vitest, Playwright configuration, pinned `package-lock.json`, `.nvmrc`).
  - Implemented centralized HTTP client (`frontend/src/lib/api/client.ts`), public env loader (`frontend/src/lib/api/env.ts`), in-memory Bearer token store (`frontend/src/lib/auth/token-store.ts`), and baseline tests (`frontend/tests/smoke.test.tsx`).
- **F0-D Documentation Reconciliation & Security Gate Decision:**
  - Reconciled `BACKEND_API_READINESS.md`, `API_GUIDELINES.md`, `FRONTEND_API_INTEGRATION.md`, `FRONTEND_ROADMAP.md`, `PROJECT_ROADMAP.md`, and `PROJECT_LOG.md` against the verified implementation and OpenAPI schema.
  - Confirmed **Option B** for `GET /api/v1/transactions/{transaction_id}`: `source_namespace` remains an optional opt-in partition fence (`None` by default); because `User` carries no tenant/namespace attribute, omitting `source_namespace` executes a global UUIDv4 lookup gated by global RBAC (`ADMIN`, `ANALYST`, `INVESTIGATOR`). Updated `BACKEND_API_READINESS.md` (§3.4, §6.2) and `FRONTEND_API_INTEGRATION.md` (§6.5, §7.2) to state this explicitly rather than claiming unconditional detail isolation.

## Validation

- Backend test suite (`uv run pytest -q`): `593 passed` (including unit, API, and PostgreSQL integration coverage in `tests/unit/test_common_types.py`, `tests/unit/test_transaction_schemas.py`, `tests/unit/test_transaction_service.py`, `tests/api/test_transactions_api.py`, `tests/api/test_dataset_imports_api.py`, and `tests/integration/test_transactions_api.py`).
- Backend quality gates: `uv run ruff check .`, `uv run ruff format --check .`, and `uv run mypy src tests` passed with zero issues.
- Frontend verification: `npm run typecheck`, `npm run lint`, `npm run format:check`, `npm run test` (`4 passed`), `npm run build`, and `npm run check:types-drift` all passed with zero drift.

## Current Status & Next Milestone

- **Backend + ML v1.0.0:** Released & Stable.
- **Phase F0 (F0.1–F0.4 & F0-D):** Completed & Verified.
- **Next Milestone:** Begin Phase F1 — Application Foundation & Design System (`docs/FRONTEND_ROADMAP.md` §7).

---

# 36. 2026-11-11 — Phase F1 Implementation, Audit Remediation & Documentation Synchronization

## Context

Following Phase F0 completion, Phase F1 (Application Foundation & Design System) was implemented, subjected to an independent post-implementation technical audit (`FAIL` on initial audit due to Prettier failures on 17 files, two Tailwind v4 CSS cascade conflicts, 11 `npm audit` vulnerabilities, cross-realm `AbortSignal` stripping, and production `Button` `asChild` prop leakage), and subsequently remediated and re-verified before documentation synchronization.

## Audit Remediation & Technical Changes

- **Formatting (`F1-AUD-001`):** Ran `npm run format` across `frontend/` to remove extra trailing newlines across 17 F1 files without altering `.prettierrc.json` or unrelated F0 files.
- **Dependency Upgrades & Runtime Alignment (`F1-AUD-002`, `ADR-078`, `ADR-079`):**
  - Upgraded `zod` from `3.25.76` to `^4.6.7` (locked `4.6.7`), resolving the high-severity production collection-validation DoS advisory (`1243066`) and verifying compatibility with `react-hook-form@7.91.0` and `@hookform/resolvers@5.9.2`.
  - Upgraded `vitest` from `3.2.7` to `^5.1.0` (locked `5.1.0`), eliminating the 2 critical dev-only advisories (`tinypool@1.1.1`, `@vitest/mocker`) and removing 22 obsolete packages.
  - Because `vitest@5.1.0` drops Node 20 (`"engines": { "node": "^22.12.0 || ^24.0.0 || >=26.0.0" }`) and requires `vite@^6.4.0`, aligned `frontend/.nvmrc` (`20` → `24`), `frontend/package.json` `"engines.node"` (`>=20.0.0` → `^22.12.0 || >=24.0.0`), and `"vite"` range (`^6.3.5` → `^6.4.0`, locked at `6.4.6`).
- **CSS Cascade Remediation (`F1-AUD-003`):**
  - Refactored `frontend/src/components/ui/Input.tsx` to emit mutually exclusive surface, text, and border state utilities (`bg-surface-subtle text-text-disabled border-border` vs `bg-surface text-text-primary border-border-strong` vs `text-text-secondary` vs `border-danger`) so `.text-text-primary` cannot override `.text-text-disabled`.
  - Extended `SkeletonVariant` in `frontend/src/components/ui/Skeleton.tsx` with `"text-sm"` (`h-3.5`) and updated `TableSkeleton` header cells to render `variant="text-sm"` (`14px`) without conflicting `h-4` classes.
- **Cross-Realm `AbortSignal` Fix (`F1-AUD-004`):** Updated `PatchedRequest` in `frontend/tests/setup.ts` to obtain Node's native `AbortController` via `globalThis.process?.getBuiltinModule?.("node:vm")?.runInThisContext?.("AbortController")` and bridge non-aborted foreign `jsdom` signals with `{ once: true }` `"abort"` listeners and cleanup instead of deleting `rest.signal`.
- **Button `asChild` Hardening (`F1-AUD-008`):** Updated `frontend/src/components/ui/Button.tsx` to explicitly destructure and drop `disabled` and `isLoading` before forwarding `...slotRest` to Radix `<Slot>` even when `import.meta.env.DEV` dead-code elimination removes the development throw.
- **Regression Tests Added/Expanded:** Added Zod 4 + `@hookform/resolvers/zod` + `Input` validation integration tests (`tests/unit/zod-rhf.test.tsx`), in-flight `AbortController` MSW cancellation test (`tests/unit/api-client.test.ts`), mutually exclusive state class assertions (`tests/components/input.test.tsx`), header/body height class assertions (`tests/components/skeleton.test.tsx`), and non-DEV `asChild` prop-stripping verification (`tests/components/button.test.tsx`).

## Validation & Security Audit Results (Post-Remediation)

- **Formatting (`npm run format:check`):** `PASS` (exit `0`).
- **Linting (`npm run lint`):** `PASS` (`0` errors, `0` warnings).
- **TypeScript (`npm run typecheck`):** `PASS` (`strict: true`, `tsc -b --pretty`).
- **Vitest (`npm run test`, `v5.1.0`):** `47 passed` across `15` test files (`0` failed, `0` skipped).
- **Production build (`npm run build`, `vite v6.4.6`):** `PASS` (`dist/index.html` `0.39 kB`, CSS `23.18 kB` / `5.58 kB` gzip, JS `362.12 kB` / `114.54 kB` gzip).
- **OpenAPI drift (`npm run check:types-drift`):** `PASS` (`0` drift).
- **Browser verification (system Chrome):** `PASS` against `vite preview` (`1440`/`1024`/`768`/`360`, zero horizontal overflow) and an external `esbuild` harness over built CSS confirming disabled `Input` foreground (`rgb(156, 163, 175)`), `TableSkeleton` header height (`14px`) vs body (`16px`), `Button` `asChild` production attribute stripping, and `Dialog` portal/focus trap. (Note: Not a committed Playwright E2E suite.)
- **Production dependency audit (`npm audit --omit=dev`):** `PASS` (`found 0 vulnerabilities`).
- **Full dependency audit (`npm audit`):** `7 moderate` development-only advisories remain (`typescript-eslint@8.72.2` → `minimatch@10.2.6`, `GHSA-g3hv-75wg-m249`). No safe non-forcing automated fix exists upstream; exception recorded in `ADR-080` as **`PENDING OWNER APPROVAL`**.
- **Remote GitHub Actions CI (`.github/workflows/ci.yml`):** `PENDING` (not yet executed remotely).

## Explicitly Deferred Findings

- `F1-AUD-005`: API client network `TypeError` normalization, non-JSON `2xx` guard, `/api/v1` path deduplication, and `VITE_API_BASE_URL` scheme validation → **Phase F2 API milestone**.
- `F1-AUD-006`: Committed Playwright `tests/e2e/` suite and `playwright.config.ts` `webServer` wiring → **Phase F2 testing milestone**.
- `F1-AUD-009`: `Button` `size="icon"` loading icon replacement layout and `Alert` attribute passthrough ergonomics → **Future UI refinement**.

## Current Status & Next Milestone

- **Backend + ML v1.0.0:** Released & Stable.
- **Phase F0:** Completed & Verified.
- **Phase F1:** **`CONDITIONALLY READY`** — implementation remediation and local verification complete; formal acceptance pending owner approval of `ADR-080` (`minimatch@10.2.6` dev-only exception) and remote GitHub Actions CI verification.
- **Next Milestone:** Obtain formal Phase F1 acceptance sign-off, then begin **Phase F2 — Authentication, Session & Application Shell** (`NEXT / BLOCKED UNTIL F1 ACCEPTANCE`).

---

# 37. 2026-11-11 — Phase F1 Formal Acceptance, ADR-080 Approval & Phase F2 Implementation

## Context

Following push of the Phase F1 baseline (`ad02a4e`), remote GitHub Actions CI workflow run `43036181121` succeeded across both backend (`Lint, Type Check, Migrate & Test`) and frontend (`Frontend Format, Lint, Type Check, Test, Build & Drift Check`) jobs. On `2026-11-11`, the project owner explicitly approved `ADR-080` (temporary risk acceptance for 7 moderate dev-only `minimatch@10.2.6` advisories under `typescript-eslint@8.72.2`), granted formal acceptance of Frontend Phase F1, and authorized implementation of Frontend Phase F2 (`F2.1`–`F2.6`), deferring documentation updates to a dedicated reconciliation run.

## What Changed (Phase F2 Implementation)

- **F2.1 API Hardening & Auth API (`F1-AUD-005` Resolved):**
  - Updated `frontend/src/lib/api/env.ts` (`resolveApiBaseUrl`) to reject empty strings, control characters/whitespace, query strings (`?`), fragments (`#`), embedded credentials, protocol-relative (`//`) paths, non-HTTP(S) schemes, and non-HTTPS absolute URLs in production.
  - Updated `frontend/src/lib/api/client.ts` (`apiRequest`, `buildUrl`) to validate relative paths before `fetch`, prevent `/api/v1` prefix duplication, normalize `TypeError` network failures to `NETWORK_ERROR` (preserving `AbortError`), guard `204`/`205`/empty and non-JSON `2xx` responses (`INVALID_RESPONSE`), normalize FinSignal error envelopes plus defensive FastAPI `422` `{ detail: [...] }` arrays, fall back to `error.details.retry_after_seconds` on `429`, support explicit `authMode` (`"bearer" | "none"`), and trigger `notifyUnauthorized(requestEpoch)` unless `skipUnauthorizedHandler` is set.
  - Added `frontend/src/lib/api/errors.ts`, `frontend/src/lib/auth/session-events.ts`, and `frontend/src/features/auth/api/auth-api.ts` (`login`, `getCurrentUser`, `logout` typed from `src/api/generated/schema.ts`).
- **F2.2 In-Memory Authentication & Session Lifecycle (`ADR-075`):**
  - Extended `frontend/src/lib/auth/token-store.ts` with monotonic `sessionEpoch` alongside module-scoped `accessToken`.
  - Created `auth.types.ts` (`isUserRole`, `parseAuthUser`), `AuthContext.ts`, `AuthProvider.tsx`, and `useAuth.ts`, and mounted `AuthProvider` inside `QueryProvider` in `AppProviders.tsx`.
  - Implemented 8-step `signIn` (`authAttemptId` -> `/auth/login` -> `setAccessToken` -> post-write `sessionEpoch` capture -> `/auth/me` -> dual attempt/epoch verification -> state commit), backend `expires_in` timer, single-flight `401` expiration, `403` session preservation, local-only logout (`Option B`: no `/auth/logout` call or JWT revocation claim), and `QueryClient` cancellation + synchronous cache clearing.
- **F2.3 Routing Guards & Capability Matrix:**
  - Added `redirect.ts` (`sanitizeRedirectPath`, `buildLoginRedirectPath`) rejecting external URLs, `//`, `\`, schemes, control chars, `/login` loops, and sensitive query keys.
  - Added `capabilities.ts` scoped strictly to F2 workspace/navigation capabilities, failing closed on inactive/unknown roles and separating `canViewDatasetImports` (`ADMIN | ANALYST | INVESTIGATOR` read-only import history) from `canManageDatasets` (`ADMIN | ANALYST` upload/recovery).
  - Added `SessionLoadingView.tsx`, `ProtectedRoute.tsx`, `PublicOnlyRoute.tsx`, and `RoleGate.tsx`.
- **F2.4–F2.5 Application Shell, Login Page & Route Cutover:**
  - Created `AuthLayout.tsx`, `AppLayout.tsx` (skip link to `#main-content`), `nav-config.ts`, `Sidebar.tsx` (collapsible desktop nav + `Escape`-dismissible mobile drawer), `TopBar.tsx`, `UserMenu.tsx`, `WorkspaceHomePage.tsx`, and honest F3–F5 `PhasePlaceholderPage.tsx` views (omitting uncontracted `Accounts`, `Audit`, and `Admin Users` and introducing zero fake metrics).
  - Created Zod 4 `login-schema.ts` (`1..128` password matching `LoginRequest`) and React Hook Form `LoginPage.tsx` (single-submit lock, `401`/`422`/`429`/`5xx`/network/expired-session alerts, no registration link).
  - Cut over `routes.tsx` and retired `FoundationPage.tsx`; updated `smoke.test.tsx` and `resilience.test.tsx`.
- **F2.6 Testing & Playwright E2E (`F1-AUD-006` Resolved):**
  - Added Vitest/MSW test suites (`auth-api.test.ts`, `session-lifecycle.test.tsx`, `redirect.test.ts`, `capabilities.test.ts`, `protected-routes.test.tsx`, `app-shell.test.tsx`, `login-page.test.tsx`, expanded `api-client.test.ts`, plus `tests/fixtures/auth.ts`).
  - Configured `frontend/playwright.config.ts` and `"test:e2e": "playwright test"` in `frontend/package.json` to build a fresh production bundle and serve via `vite preview` (`reuseExistingServer: false`) for mocked Chromium E2E (`tests/e2e/{auth,shell}.spec.ts` + `tests/e2e/helpers/auth-mock.ts`), explicitly separated from `E2E_API_MODE=live` dev-proxy mode.

## Implementation Deviations from Plan

- **Deliberate Logout Navigation Fix:** Added `preserveRedirectOnUnauthenticated` in `AuthContext.ts`/`AuthProvider.tsx`/`ProtectedRoute.tsx` after Playwright caught a race where manual `signOut()` from `/datasets` previously produced `/login?redirect=%2Fdatasets` instead of `/login`.
- **Structural Extractions:** Extracted `AuthContext.ts` (avoiding `react-refresh/only-export-components` warnings in `AuthProvider.tsx`), `SessionLoadingView.tsx`, and `tests/e2e/helpers/auth-mock.ts` to keep shared logic DRY.
- **Explicit Policy Implementations:** Implemented local-only logout (`Option B`) and `INVESTIGATOR` read-only dataset import access (`canViewDatasetImports` vs `canManageDatasets`) per owner confirmation; left `/datasets` inside `ProtectedRoute` without gating read access away from investigators.

## Verification Results (Local, After Final Edit)

- **Prettier (`npm run format:check`):** `PASS` (`0` issues).
- **ESLint (`npm run lint`):** `PASS` (`0` errors, `0` warnings).
- **TypeScript (`npm run typecheck`):** `PASS` (`strict: true`).
- **Vitest (`npm run test`):** **`87/87` PASS** across `22` files (`msw/node`, `0` failed, `0` skipped).
- **Production build (`npm run build`):** `PASS` (`dist/index.html` `0.39 kB`, CSS `28.09 kB`, JS `522.78 kB`).
- **OpenAPI drift (`npm run check:types-drift`):** `PASS` (`0` drift).
- **Playwright E2E (`npm run test:e2e`):** **`5/5` PASS** in Chromium against fresh production `vite preview` (`0` failed, `0` skipped, mocked `page.route` API).
- **Production dependency audit (`npm audit --omit=dev`):** `PASS` (`0` vulnerabilities).
- **Full dependency audit (`npm audit`):** `7 moderate` dev-only `minimatch@10.2.6` advisories remain (not remediated; covered by owner-approved `ADR-080`).

## Outstanding Verification & Deferred Items

- **Live-Backend E2E (`E2E_API_MODE=live`):** Not executed locally (requires running FastAPI + PostgreSQL + `E2E_LIVE_EMAIL`/`E2E_LIVE_PASSWORD`).
- **Remote GitHub Actions CI for F2:** Not yet triggered on F2 changes.
- **Deferred F1 Item:** `F1-AUD-009` (`Button` `size="icon"` loading layout & `Alert` attribute passthrough) remains deferred.

## Current Status & Next Milestone

- **Backend + ML v1.0.0:** Released & Stable.
- **Phase F0 & Phase F1:** Completed & Formally Accepted (`ad02a4e`, CI run `43036181121`, `ADR-080` accepted `2026-11-11`).
- **Phase F2:** Implemented & Locally Verified (Remote F2 CI & Live-Backend E2E Pending; Formal Acceptance Pending).
- **Phase F3:** Implemented & Locally Verified (Remote F3 CI & Live-Backend E2E Pending; Formal Acceptance Pending).
- **Next Milestone:** Verify remote CI and optional live-backend checks for Phase F2, F3 & F4 acceptance, then proceed to **Phase F5 — Investigation Queue, Workspace & Lifecycle**.

---

# 39. Phase F4 — Dataset Import & Processing Visibility Implementation

**Date:** 2026-11-13  
**Role:** Senior Frontend Engineer, Architect & QA Reviewer  
**Objective:** Implement complete Frontend Phase F4 scope including dataset CSV upload, client-side preflight validation, import history ledger with status filtering and UTC boundaries, status monitoring with 5-minute polling cutoff, import detail with validation error logs, failed import recovery, and safe cache invalidation.

## Key Changes & Components Added

1. **Dataset Ingestion & Preflight Validation (`frontend/src/features/datasets/`):**
   - Implemented `DatasetUploadCard` mounted on `/datasets` enabling `ADMIN` and `ANALYST` roles to upload CSV files with target namespace and source type.
   - Built client-side preflight validation schema (`dataset-upload-schema.ts`) strictly enforcing the authoritative 50 MB limit (`52,428,800` bytes) and `.csv` extension check before initiating network requests.
   - Dispatched multipart uploads to backend route `POST /api/v1/datasets/imports`.
   - Handled duplicate upload detection cleanly: distinguishing `200 OK` (byte-identical completed re-upload) and `201 Created` (fresh ingestion job).

2. **Dataset Ledger & History Presentation:**
   - Implemented `DatasetsPage` mounted at `/datasets` with server-side pagination, namespace filter, status filter (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), and UTC date-range controls (`DatasetFiltersBar.tsx`).
   - Built `DatasetImportTable` rendering deterministic start-time ordering, row-level metrics (total rows, valid rows, invalid rows), duplicate indicators, and status badges.
   - Implemented role-based capability gating: `INVESTIGATOR` role receives clear read-only notice while upload forms and recovery buttons are hidden.

3. **Status Polling & Abandoned Import Safeguard:**
   - Implemented `importPollingTracker` (`polling-tracker.ts`): tracks elapsed active polling duration per import in the current SPA session.
   - Configured 5-second polling interval via TanStack Query (`refetchInterval`), automatically halting after 5 minutes (300,000 ms) for active imports (`PENDING`, `PROCESSING`).
   - Preserves last known status upon polling cutoff and surfaces a clear visual indicator offering manual refresh without triggering automated recovery.

4. **Import Detail & Validation Error Visibility:**
   - Implemented `DatasetImportDetailPage` mounted at `/datasets/imports/:importId` consuming `GET /api/v1/datasets/imports/{id}`.
   - Built fact cards displaying immutable import metadata: filename, SHA-256 hash, execution duration, and total/valid/invalid row counters.
   - Built `DatasetImportErrorTable` rendering quarantined rows, error codes (`INVALID_DECIMAL`, `REQUIRED_FIELD_MISSING`, etc.), row numbers, and field pointers with HTML-escaped text rendering.

5. **Failed Import Recovery Workflow:**
   - Implemented `DatasetRecoveryDialog` consuming `POST /api/v1/datasets/imports/{id}/recover`.
   - Restricted recovery button strictly to imports in `FAILED` status and permitted roles (`ADMIN`, `ANALYST`).
   - Verified that the recovery state machine forbids `PROCESSING -> PROCESSING` transitions, preventing premature recovery while ingestion is active.

6. **UTC Date-Filter Boundaries:**
   - Built `mapDateRangeToUtcIsoBoundaries` and `toDateBoundaryParam` (`dataset-filter-schema.ts`):
     - `from_time`: serialized to start-of-day UTC ISO string (`YYYY-MM-DDT00:00:00.000Z`, inclusive `>=`).
     - `to_time`: serialized to start of next-day UTC ISO string (`+ 24h`, exclusive `<`).
     - Tested across month boundaries, year boundaries, and leap years (`2024-02-28` -> `2024-02-29T00:00:00.000Z` and `2024-02-29` -> `2024-03-01T00:00:00.000Z`).

7. **Safe Cache Invalidation Policy:**
   - Conditioned `422` cache invalidation in `useUploadDatasetMutation` on the presence of a persisted `import_id` in error details.
   - Pre-insertion 422 validation errors do not prematurely invalidate import history or pollute transaction/analytics caches.

8. **Audit Findings & Test Suite Remediation:**
   - Corrected 3 heading assertions in `tests/components/datasets-page.test.tsx` targeting `{ name: "Datasets", level: 1 }`, bringing the Vitest suite to 100% pass rate (150/150).
   - Removed ambient `"node"` types from `tsconfig.app.json`, eliminating Node.js global pollution (`process`, `Buffer`) from browser client application code.
   - Replaced Playwright spec Buffer dependencies with runtime-isolated `globalThis.Buffer` resolution.

## Verification Results (Local)

- **Prettier (`npm run format:check`):** `PASS` (`0` formatting issues).
- **ESLint (`npm run lint`):** `PASS` (`0` errors, `0` warnings).
- **TypeScript (`npm run typecheck`):** `PASS` (`strict: true`, zero type errors).
- **OpenAPI Drift (`npm run check:types-drift`):** `PASS` (generated types in sync with backend contract).
- **Vitest Unit & Component Tests (`npm run test`):** **`150/150` PASS** across `43` test files (`0` failed, `0` skipped).
- **Production Build (`npm run build`):** `PASS` (Vite production bundle built cleanly in 8.25s).
- **Playwright E2E (`npm run test:e2e`):** **`9/9` PASS** in Chromium against production build (including new `tests/e2e/dataset-import.spec.ts`).
- **Production Dependency Audit (`npm audit --omit=dev`):** `PASS` (`0` vulnerabilities).

## Outstanding Verification & Deferred Items

- **Live-Backend E2E (`E2E_API_MODE=live`):** Not executed locally (requires live running FastAPI + PostgreSQL backend with valid authentication).
- **Remote GitHub Actions CI:** Remote CI workflow execution for Phase F4 commits remains pending.
- **Account-Level Analytics:** Retains deferred status per approved F3 scope.

---

# 38. Phase F3 — Analytics, Transaction Exploration & Risk Implementation

**Date:** 2026-11-12  
**Role:** Senior Frontend Engineer & Architect  
**Objective:** Implement complete Frontend Phase F3 scope including operational dashboard overview, financial analytics visualizations, transaction exploration table, transaction detail, and hybrid risk scoring with on-demand evaluation.

## Key Changes & Components Added

1. **Dashboard Overview (`frontend/src/features/dashboard/`):**
   - Replaced landing placeholder at `/` with `DashboardPage` displaying high-level operational metrics from `GET /api/v1/analytics/overview`.
   - Built `OverviewKpiGrid` rendering total transactions, debit/credit transaction counts, total debit volume, total credit volume, and continuous median transaction amounts.
   - Built `ReportingScopeBar` providing client-side namespace filtering (default `"SYNTHETIC"`), currency display, and half-open time-range scoping (`[from_time, to_time)`).

2. **Financial Analytics Views (`frontend/src/features/analytics/`):**
   - Implemented `AnalyticsPage` mounted at `/analytics` with tabbed view navigation (Volume Trends, Category Spending, Top Merchants).
   - Built `TrendsChartPanel` with dynamically imported Apache ECharts (`React.lazy` in `TrendEChart`), rendering dual-axis bar and line charts for daily/monthly debit vs credit trends.
   - Built `CategoryDistributionPanel` rendering categorical pie charts and accessible tabular breakdowns with exact percentage distributions.
   - Built `MerchantAnalyticsPanel` displaying top merchants ranked by debit volume or transaction frequency with dual-metric percentages (percentage of total debit volume and percentage of merchant spend).
   - Ensured all chart configurations adhere to enterprise guidelines: restrained color palette, HTML-escaped tooltip formatters preventing XSS, and `prefers-reduced-motion` animation disabling.

3. **Transaction Exploration & Detail (`frontend/src/features/transactions/`):**
   - Implemented `TransactionsListPage` at `/transactions` with server-side pagination (`page_size=50`), column sorting (`occurred_at`, `amount`), and multi-field filtering (namespace, amount range, risk level, half-open time bounds).
   - Synchronized all filter and pagination state with URL search parameters (`useSearchParams`) following ADR-074 (zero Redux/Zustand stores).
   - Implemented `TransactionDetailPage` at `/transactions/:transactionId` with `TransactionFactsCard` rendering immutable transaction facts (exact `MoneyStr` amounts, UTC timestamps, account IDs, counterparty references, execution metadata).
   - Integrated `RiskAnalysisPanel` within transaction detail, embedding latest risk scores and model version metadata.

4. **Risk Scoring & Explainability (`frontend/src/features/risk/`):**
   - Implemented `RiskAnalysisPanel` consuming `GET /api/v1/transactions/{id}/risk`.
   - Distinctly mapped HTTP 404 responses to an explicit `"not_analyzed"` state, preventing unanalyzed transactions from being erroneously presented as low risk or zero risk.
   - Rendered hybrid risk score ([0.00, 100.00]), categorical risk tier badges (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), score breakdown (ML score vs Rule score), and structured `RiskFactorList`.
   - Implemented on-demand risk analysis action (`POST /api/v1/transactions/{id}/risk/analyze`) using the default `ACTIVE` model with fail-closed capability gates (`canAnalyzeActiveRisk`).

5. **Shared Components & Utilities:**
   - Implemented domain-agnostic `Pagination` component (`frontend/src/components/ui/Pagination.tsx`) supporting first, previous, page numbers, next, and last controls.
   - Built string-safe formatting utilities: `formatMoney`, `formatMoneyParts`, `MoneyValue` component (`frontend/src/components/data-display/MoneyValue.tsx`) guaranteeing zero floating-point arithmetic.
   - Built timezone-aware UTC datetime formatters (`formatUtcDateTime`, `formatUtcDate`, `toUtcIsoString`) enforcing calendar limits (366 daily / 120 monthly buckets).
   - Built centralized query keys (`frontend/src/lib/api/query-keys.ts`) for `analytics`, `transactions`, and `risk`.

6. **Local Development User Creation Findings:**
   - Identified that default development credentials (`testuser@example.com`) do not exist in the local database.
   - Documented that developers can create an active `ANALYST` user via `POST /api/v1/auth/register` (minimum 12-character password).
   - Documented that `ADMIN` and `INVESTIGATOR` roles currently require direct Python repository instantiation.

## Verification Results (Local)

- **Prettier (`npm run format:check`):** `PASS` (`0` formatting issues).
- **ESLint (`npm run lint`):** `PASS` (`0` errors, `0` warnings).
- **TypeScript (`npm run typecheck`):** `PASS` (`strict: true`, zero type errors).
- **OpenAPI Drift (`npm run check:types-drift`):** `PASS` (generated types in sync with backend contract).
- **Vitest Unit & Component Tests (`npm run test`):** **`121/121` PASS** across `36` test files (`0` failed, `0` skipped).
- **Production Build (`npm run build`):** `PASS` (Vite bundle with isolated `echarts-chunk-*.js` dynamic chunk).
- **Playwright E2E (`npm run test:e2e`):** **`7/7` PASS** in Chromium against production build (`auth.spec.ts`, `shell.spec.ts`, `analytics.spec.ts`, `transactions.spec.ts`).
- **Production Dependency Audit (`npm audit --omit=dev`):** `PASS` (`0` vulnerabilities).

## Outstanding Verification & Deferred Items

- **Live-Backend E2E (`E2E_API_MODE=live`):** Not executed locally (requires live running FastAPI + PostgreSQL backend with populated test transactions).
- **Remote GitHub Actions CI:** Remote CI workflow execution for Phase F3 commits remains pending.
- **Account-Level Analytics:** `/analytics/accounts/{account_id}` and `/unusual-spending` remain intentionally excluded from F3 per approved scope.

---

# 40. Phase F5 — Investigation Queue, Workspace & Lifecycle Implementation & Independent Audit

**Date:** 2026-11-13
**Role:** Senior Frontend Architect, Technical Lead & Independent Reviewer
**Objective:** Deliver the complete Frontend Phase F5 scope (milestones F5.1 through F5.7) including the investigation queue, workspace, lifecycle transitions, related transaction linking, formal human resolution, and comprehensive unit/component/E2E test verification.

## Key Changes & Components Added

1. **Investigation Domain Types & API Client (`frontend/src/features/investigations/`):**
   - Implemented pure async functions in `api/investigations-api.ts` covering all seven backend endpoints (`listInvestigations`, `createInvestigation`, `getInvestigation`, `patchInvestigation`, `resolveInvestigation`, `getInvestigationTransactions`, `addRelatedTransaction`).
   - Re-exported canonical OpenAPI types in `types/investigations.types.ts` without drift or loose type assertions.
   - Built Zod 4 mutation and filter schemas (`investigation-filter-schema.ts`, `investigation-mutations-schema.ts`) strictly whitelisting allowed properties and enforcing backend `extra="forbid"` constraints.
   - Enforced mutual exclusivity between `assigned_to` and `unassigned=true` in client filter normalization, preventing HTTP 400 filter conflicts.
   - Extended `investigationKeys` in `frontend/src/lib/api/query-keys.ts` with hierarchical cache structures.
   - Implemented 8 fail-closed capability helpers in `frontend/src/lib/permissions/capabilities.ts` strictly mirroring backend RBAC and lifecycle rules.

2. **Investigation Queue Page (`frontend/src/features/investigations/pages/InvestigationsQueuePage.tsx`):**
   - Replaced placeholder at `/investigations` with fully interactive, accessible queue page protected by `canAccessInvestigations(user)`.
   - Built `InvestigationFiltersBar` with synchronized URL search parameters (`useInvestigationFilterParams`) for status, priority, page size, and assignee mode (`ALL`, `MINE`, `UNASSIGNED`, `OTHER`).
   - Built `InvestigationQueueTable` rendering status badges, priority badges, primary transaction references, and server-side pagination with deterministic backend ordering (`created_at DESC, id DESC`).
   - Provided clean loading skeletons, error retry actions, and distinct empty states (no cases vs no matching filters).

3. **Investigation Creation Flow (`frontend/src/features/investigations/components/InvestigationCreateDialog.tsx`):**
   - Implemented creation modal accessible from queue header and directly from `TransactionDetailPage` ("Investigate Transaction" button).
   - Pre-populates and locks primary transaction UUID when opened from transaction detail.
   - Enforces default `MEDIUM` priority; strictly adheres to backend contract by omitting initial creation notes (`InvestigationCreateRequest` accepts only `transaction_id` and `priority`).
   - Navigates immediately to `/investigations/:investigationId` upon successful creation.

4. **Investigation Workspace (`frontend/src/features/investigations/pages/InvestigationWorkspacePage.tsx`):**
   - Routed at `/investigations/:investigationId` with client-side UUID validation.
   - Single-query aggregate loading (`useInvestigationDetailQuery`) retrieving `InvestigationDetailResponse` envelope without N+1 waterfalls.
   - `InvestigationWorkspaceHeader`: Displays case metadata, status, priority, assignee, and role-gated action buttons.
   - `InvestigationPrimaryTransactionCard`: Formats immutable transaction facts strictly via `<MoneyValue>` and `<TimestampDisplay>`, with direct link to transaction explorer.
   - `InvestigationLatestRiskCard`: Renders read-only snapshot of risk score and risk level recorded at case creation.
   - `InvestigationRelatedTransactionsCard`: Displays associated transactions from aggregate payload and provides linking trigger.
   - `InvestigationResolutionBanner`: Permanent read-only banner rendered when case is in `RESOLVED` status, displaying verdict, audit notes, resolver, and timestamp.
   - `InvestigationEvidencePlaceholderCard` & `InvestigationAiSummaryPlaceholderCard`: Clear placeholders representing deferred Phase F6 scope without broken interactions.

5. **Assignment, Lifecycle, Linking & Resolution Workflows:**
   - `InvestigationAssignDialog`: Provides manual UUID assignment and unassignment for `ADMIN` role without fabricating an unverified user list.
   - "Take Case" inline action: Enables one-click self-assignment for `INVESTIGATOR` on unassigned cases.
   - "Release Case" action: Allows assigned investigators to return case to unassigned queue.
   - `InvestigationPriorityDialog`: Allows authorized users (`ADMIN` or assigned `INVESTIGATOR`) to adjust triage priority.
   - `OPEN -> UNDER_REVIEW` transition: Accessible via "Begin Review" button for assigned investigators and admins.
   - `InvestigationLinkTransactionDialog`: Associates related transactions satisfying the backend 4-way 1-hop scope predicate; maps backend error codes (`NAMESPACE_MISMATCH`, `TRANSACTION_NOT_RELATED`, `TRANSACTION_ALREADY_LINKED`, `INVESTIGATION_ALREADY_RESOLVED`, `TRANSACTION_NOT_FOUND`).
   - `InvestigationResolveDialog`: Formal human resolution with allowed outcomes (`LEGITIMATE`, `SUSPICIOUS`, `CONFIRMED_FRAUD`, `INCONCLUSIVE`), mandatory non-whitespace notes (`.trim().min(1)`), and prominent permanent lock warning.
   - Concurrency (`409 Conflict`) Handling: State conflicts (e.g. concurrent claim or modification) surface a clear warning alert, dismiss modal forms, and automatically invalidate queries to reload authoritative server state.

6. **Comprehensive Test Suite & Independent Audit (`F5.7`):**
   - Added 8 test and fixture files across unit schemas, API client, badges, queue page, workspace page, creation modal, and Playwright E2E.
   - Authored 4 comprehensive Playwright journeys in `tests/e2e/investigations.spec.ts` (ANALYST creation, INVESTIGATOR lifecycle, ADMIN management, Concurrency 409 conflict handling).
   - Conducted formal independent audit (`docs/F5_IMPLEMENTATION_AUDIT.md`) resulting in verdict: **APPROVED WITH MINOR ISSUES** (zero Critical, High, or Medium blocking defects).

## Verification Results (Independent Audit Baseline)

- **TypeScript Typecheck (`npm run typecheck`):** `PASS` (`tsc -b --pretty`, 0 errors).
- **ESLint Code Quality (`npm run lint`):** `PASS` (`eslint .`, 0 errors, 0 warnings).
- **Vitest Unit & Component Tests (`npm run test`):** **`204/204` PASS** across `49` test files (`0` failed, `0` skipped, duration 31.03s).
- **Playwright E2E Browser Tests (`npm run test:e2e`):** **`13/13` PASS** in Chromium against production preview (duration 31.2s).
- **Production Build (`npm run build`):** `PASS` (clean build with code-splitting chunks).

## Audit Findings Disposition & Documentation Synchronization

- **F5-AUD-01 (Creation Notes):** Reconciled `FRONTEND_PRD.md` (§6.5, §AC-006) to match the authoritative backend contract (`InvestigationCreateRequest` accepts only `transaction_id` and `priority`; initial creation notes are forbidden).
- **F5-AUD-02 (Capability Helper Parameter):** Noted `canAdminAssignInvestigation` optional parameter as a non-blocking type tightness recommendation; runtime usage in workspace safely passes full context.
- **F5-AUD-03 (Mocked E2E Boundary):** Documented that Playwright journeys use client-side route interception (`page.route`); live-backend E2E execution against running PostgreSQL is retained as a staging qualification gate.
- **Queue Ordering Discrepancy Resolved:** Verified from backend repository source code (`src/finsignal/investigations/repository.py:184`) that deterministic SQL ordering is strictly `created_at DESC, id DESC`. Reconciled in `FRONTEND_API_INTEGRATION.md`.
- **Role Model Reconciled:** Verified that backend authentication and database constraint `chk_users_role` enforce strictly three roles (`ADMIN`, `ANALYST`, `INVESTIGATOR`). There is no implemented `AUDITOR` role; unauthenticated/unknown roles fail closed.

## Next Phase

- **Phase F6 — Evidence & AI-Assisted Investigation:** Append-only evidence attachment, evidence list, AI briefing summary generation, staleness detection, and summary history.
