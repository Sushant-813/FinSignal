# FinSignal — Project Log

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Log  
**Scope:** Backend + ML  
**Status:** Active Development Log  
**Version:** 1.0.0  
**Last Updated:** 2026-10-04

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

Implement the modular-monolith structure.

### Planned Modules

```text
auth
users
accounts
merchants
devices
locations
transactions
ingestion
analytics
features
risk
investigations
evidence
ai
dataset
common
```

### Validation

- dependency direction;
- service/repository separation;
- API boundaries;
- common exception handling;
- logging;
- configuration.

### Status

`NOT STARTED`

---

# 9. Phase 2 — Database & Domain Models

### Objective

Implement the PostgreSQL domain model.

### Primary Areas

- users;
- accounts;
- merchants;
- devices;
- account-device relationships;
- locations;
- transactions;
- dataset imports;
- model versions;
- risk analyses;
- risk factors;
- investigations;
- investigation transactions;
- evidence;
- AI summaries;
- audit events.

### Important Constraints

- transaction immutability;
- valid foreign keys;
- valid transfer counterparties;
- deterministic ordering;
- correct timestamp handling;
- appropriate indexes.

### Validation

- migration tests;
- repository tests;
- constraint tests;
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

`NOT STARTED`

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

Begin Phase 0 implementation after repository setup and documentation review.

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
