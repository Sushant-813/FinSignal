# FinSignal — Project Roadmap

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Roadmap  
**Scope:** Backend + ML only  
**Status:** Planning / Implementation-Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-10-25

---

## 1. Purpose

This document defines the implementation roadmap for the first major version of FinSignal.

The roadmap covers the **Python backend, financial analytics, ML/anomaly detection, investigation workflows, AI-assisted investigation backend, testing, security, and deployment**.

The frontend is intentionally excluded from this roadmap. Frontend planning and implementation will begin only after the Backend + ML scope reaches its defined completion point.

The roadmap is designed to keep implementation incremental, testable, and portfolio-ready.

---

# 2. Roadmap Principles

FinSignal will be developed according to the following principles:

1. Build the domain before the intelligence layer.
2. Establish data correctness before ML.
3. Establish temporal correctness before model evaluation.
4. Keep raw facts separate from derived intelligence.
5. Prefer a modular monolith over premature distributed services.
6. Build a strong deterministic baseline before relying on ML.
7. Treat ML as decision support, not an autonomous fraud verdict.
8. Keep AI downstream of structured evidence.
9. Test security and data leakage continuously rather than at the end.
10. Keep infrastructure proportional to project scope.
11. Every phase must leave the repository in a buildable/testable state.
12. Every significant architectural decision must be documented.

---

# 3. Scope Boundary

## 3.1 Included in the Current Roadmap

### Backend

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy / ORM layer
- database migrations
- authentication
- JWT
- RBAC
- account management
- transaction management
- CSV ingestion
- data validation and cleaning
- financial analytics
- investigation workflows
- evidence management
- audit logging
- API documentation
- Docker
- backend deployment preparation

### ML / Data Intelligence

- synthetic dataset generation
- behavioral profiles
- feature engineering
- temporal feature calculation
- deterministic anomaly signals
- Isolation Forest baseline
- hybrid risk scoring
- risk factors
- model evaluation
- scenario-level evaluation
- account-level evaluation
- model versioning
- reproducibility
- model/data lineage
- AI investigation summaries
- LLM provider abstraction

### Quality / Security

- unit tests
- integration tests
- API tests
- security tests
- temporal leakage tests
- ML tests
- performance testing
- CI
- logging
- auditability

---

## 3.2 Explicitly Deferred

The following are **not part of the current implementation roadmap**:

- React implementation
- TypeScript frontend implementation
- Tailwind UI implementation
- dashboard UI
- frontend state management
- frontend testing
- frontend deployment
- UI/UX design implementation
- Kafka
- distributed microservices
- graph database
- graph ML
- RAG
- MLflow
- real-time streaming
- complex distributed worker infrastructure

These may become future phases after the Backend + ML release.

---

# 4. High-Level Roadmap

```text
Phase 0
Foundation
   ↓
Phase 1
Backend Architecture & Project Setup
   ↓
Phase 2
Database & Domain Models
   ↓
Phase 3
Authentication & RBAC
   ↓
Phase 4
Dataset & Transaction Ingestion
   ↓
Phase 5
Financial Analytics
   ↓
Phase 6
Feature Engineering
   ↓
Phase 7
ML / Anomaly Detection
   ↓
Phase 8
Risk Analysis & Explainability
   ↓
Phase 9
Investigation & Evidence
   ↓
Phase 10
AI Investigation Assistant
   ↓
Phase 11
Testing, Security & Hardening
   ↓
Phase 12
Docker, Deployment & Backend/ML Release
   ↓
Backend + ML v1.0
   ↓
Frontend Documentation & Implementation
```

---

# 5. Phase 0 — Project Foundation

## Objective

Establish the repository, development environment, documentation structure, dependency management, and development conventions.

## Deliverables

- repository initialized;
- Python environment configured;
- `uv` configured;
- FastAPI project skeleton;
- PostgreSQL development environment (Windows native);
- environment configuration;
- `.env.example`;
- Git conventions;
- base documentation structure;
- initial CI skeleton;
- Note: Docker containerization is deferred to Phase 12 per approved architectural decision.

## Key Tasks

- define Python version;
- initialize package structure;
- configure dependency management;
- configure formatting/linting;
- configure type checking;
- establish application entry point;
- establish configuration module;
- establish database connection layer;
- create health endpoint;
- configure PostgreSQL locally;
- establish migration tooling.

## Exit Criteria

- application starts successfully;
- PostgreSQL connection works;
- migrations can run;
- health endpoint works;
- tests execute;
- linting/type checking execute;
- native PostgreSQL development environment works (Docker containerization deferred to Phase 12).

## Status

`COMPLETED`

---

# 6. Phase 1 — Backend Architecture & Core Structure

## Objective

Implement the modular-monolith structure defined by the architecture documents.

## Modules

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

## Key Tasks

- establish module boundaries;
- define domain/service/repository responsibilities;
- establish dependency injection;
- configure database session lifecycle;
- establish common exception handling;
- establish API response/error conventions;
- establish request ID handling;
- establish logging;
- establish configuration profiles.

## Exit Criteria

- module boundaries are established;
- application dependencies flow in the intended direction;
- no premature cross-module coupling;
- representative module has unit/integration tests;
- API conventions are operational.

## Status

`COMPLETED`

---

# 7. Phase 2 — Database & Domain Models

## Objective

Build the persistent domain model.

## Primary Entities (Phase 2 — Option C: 12 Operational Tables)

Per accepted ADR-063 and ADR-064, Phase 2 implements the 12 core operational and raw tables. Intelligence, investigation, and AI summary entities are deferred to their corresponding capability phases (Phases 6, 7, and 8).

```text
users
accounts
merchants
devices
account_devices
locations
transactions
transaction_import_records
dataset_versions
dataset_imports
dataset_import_errors
audit_events
```

*(Deferred to Phase 6: `model_versions`, `risk_analyses`, `risk_factors`)*  
*(Deferred to Phase 7: `investigations`, `investigation_transactions`, `investigation_evidence`)*  
*(Deferred to Phase 8: `ai_summaries`)*

## Key Tasks

- implement SQLAlchemy models for the 12 operational tables;
- implement Alembic migrations;
- define foreign keys and database constraints;
- implement canonical transaction identity scoped by `(source_namespace, account_id, external_transaction_id)`;
- implement `transaction_import_records` for import row provenance and canonical linking;
- support standalone transaction persistence (`first_seen_import_id = NULL`);
- implement material conflict quarantine and error logging (`dataset_import_errors`);
- implement transaction-scoped advisory locking and upload concurrency indexing (`dataset_imports`);
- implement row-level idempotent recovery without naive `MAX + 1` skip;
- define indexes;
- establish timestamp conventions;
- implement transaction representation;
- implement transfer relationships;
- establish immutable transaction semantics;
- establish audit model.

## Exit Criteria

- clean database migrations succeed;
- domain entities persist correctly across all 12 operational tables;
- foreign keys and constraints work;
- canonical transaction identity and row provenance constraints verified;
- repository tests pass;
- transaction semantics are verified;
- no derived risk data is stored directly on raw transactions.

## Status

`COMPLETED`

Implemented 12 operational tables, declarative models, Alembic migration `0002_core_operational_schema`, canonical transaction identity constraints, `transaction_import_records` provenance ledger, deterministic row-hash utilities, and comprehensive tests (82 passing across unit and disposable database integration suites).

---

# 8. Phase 3 — Authentication & RBAC

## Objective

Establish the security boundary before exposing sensitive transaction functionality.

## Key Tasks

- registration;
- password hashing;
- login;
- JWT generation;
- JWT validation;
- current-user endpoint;
- logout/token invalidation strategy;
- role management;
- authorization dependencies;
- object-level authorization;
- security error handling.

## Roles

```text
ADMIN
ANALYST
INVESTIGATOR
```

## Required Security Tests

- invalid credentials;
- expired tokens;
- malformed tokens;
- role violations;
- IDOR;
- unauthorized investigation access;
- disabled accounts;
- password storage;
- sensitive-response filtering.

## Exit Criteria

- protected endpoints require valid authentication;
- role permissions work;
- security tests pass.

## Status

`COMPLETED`

- Implemented Argon2id password hashing, dummy password verification to mitigate timing discrepancies for unknown users, and HS256 JWT access token issuance/validation.
- Implemented `UserRepository` and strict Pydantic v2 auth request/response schemas with normalized email handling.
- Implemented `AuthService` handling registration with server-authoritative `ANALYST` role assignment and race-condition-safe email uniqueness translation.
- Implemented FastAPI `get_current_user` dependency and composable `require_roles("ADMIN", "ANALYST", "INVESTIGATOR")` RBAC with authoritative PostgreSQL state resolution.
- Implemented versioned authentication endpoints under `/api/v1/auth` (`/register`, `/login`, `/me`, `/logout`) with standardized error envelopes and authenticated stateless logout.
- Verified test suite: 205 passed, 14 warnings (Alembic `path_separator` deprecation warnings documented as cleanup work).
- Residual Risk / Next-Step: Rate limiting deferred to future phase (brute-force exposure on `/login` and account creation abuse on `/register` recorded as explicit production risk).

---

# 9. Phase 4 — Dataset Generation & Transaction Ingestion

## Objective

Create realistic synthetic financial data and a safe ingestion pipeline.

## Dataset Targets

```text
5,000 accounts
~500 merchants
~8,000 devices
~100 locations
~250,000 transactions
~3% fraud
```

Development scale:

```text
100 accounts
~5,000 transactions
```

Then:

```text
1,000 accounts
~50,000 transactions
```

Then full-scale generation.

## Key Tasks

- account profile generation;
- merchant generation;
- device generation;
- location generation;
- transaction generation;
- legitimate unusual-event generation;
- fraud scenario generation;
- ground-truth generation;
- CSV export;
- seed configuration;
- dataset versioning;
- import API;
- validation;
- cleaning;
- import error reporting.

## Implementation Constraints & Policies (ADR-065)

- **Contextual Divergence:** Candidate 1 — canonical transactions are immutable; contextual differences record `MATCHED_EXISTING` with `row_hash` provenance; alternate contextual plaintext is lossy and not stored in relational storage; `MATERIAL_CONFLICT` is strictly reserved for the 7 core material fields.
- **Deterministic Synthetic Identity:** Business IDs are deterministic (`ACC_[0-9]{6}`, `TXN_[0-9]{8}`, etc.); PRNG streams are isolated; baseline namespace is `SYNTHETIC`; unrelated experiments require distinct namespaces.
- **Namespace-Scoped File Deduplication:** Completed uploads return existing summaries indefinitely within their target namespace `(source_namespace, file_hash)`; reprocessing is an exceptional, audited administrative workflow.
- **Namespace-Scoped Account Identity (Decision D):** Account identity is `(source_namespace, external_account_id)`. An approved schema migration adding `source_namespace` to `accounts` and `dataset_imports`, accompanied by staged migration preflight, duplicate checks, conditional reconciliation, and layered consistency validation (Option C3), must precede reference-entity account generation (P4.1) and transaction ingestion (P4.4).
- **Reference Entity Prerequisite:** Reference entities (`locations`, `merchants`, `devices`, `accounts`) must be generated and populated before transaction ingestion foreign-key resolution.

## Fraud Scenarios

```text
F001 Large Amount Anomaly
F002 New Device
F003 New Location
F004 Unusual Time
F005 High Transaction Velocity
F006 Account Takeover
F007 Behavioral Spending Shift
```

## Implementation Checkpoints (Phase 4 — COMPLETE)

- **Checkpoint P4.0 [COMPLETE]:** Account & Import Namespace Migration (`0003_account_import_namespace.py` applied, preflight duplicate safeguards, conditional reconciliation, and Option C3 layered enforcement).
- **Checkpoint P4.1 [COMPLETE]:** Synthetic Generator Core & Reference Entities (`locations`, `merchants`, `devices`, `accounts`, `ReferenceEntityPersistenceService`).
- **Checkpoint P4.2 [COMPLETE]:** Legitimate Behavioral Synthesis & Fraud Scenarios (F001–F007, behavioral profiles calibrated in INR, attempted drain sequence F006).
- **Checkpoint P4.3 [COMPLETE]:** Scale Verification, Isolated Ground Truth & CSV Exporters (presets `small`, `medium`, `full`, formula sanitization, validator).
- **Checkpoint P4.4 [COMPLETE]:** Ingestion Engine & Canonical Provenance Ledger (`transaction_import_records`, all 5 outcomes verified: `INSERTED`, `MATCHED_EXISTING`, `DUPLICATE_IN_IMPORT`, `QUARANTINED`, `REJECTED`).
- **Checkpoint P4.5 [COMPLETE]:** Advisory Locking, File Deduplication & Dataset Import API (`/api/v1/datasets/imports`, lock key collision tolerance, partial unique index `uq_dataset_imports_active_hash`).
- **Checkpoint P4.6 [COMPLETE]:** Recovery Engine, Security Hardening & Scale Verification (gap-safe recovery, partial batch commit, 276 passing tests).

## Exit Criteria

- [x] deterministic dataset generation works;
- [x] generated data passes structural validation;
- [x] legitimate unusual events exist;
- [x] fraud scenarios exist;
- [x] ground truth is isolated;
- [x] CSV import works;
- [x] invalid records are reported;
- [x] no silent data loss occurs.

---

# 10. Phase 5 — Financial Analytics

## Objective

Build deterministic financial intelligence before introducing ML.

## Analytics

- transaction volume;
- transaction counts;
- debit/credit trends;
- spending trends;
- category distribution;
- merchant distribution;
- account activity;
- average transaction amount;
- median transaction amount;
- daily/monthly activity;
- unusual spending patterns;
- account behavioral summaries.

## Requirements

Analytics must:

- use exact monetary representation;
- respect timestamps;
- handle empty datasets;
- handle missing optional dimensions;
- use deterministic ordering;
- remain independent of fraud ground truth.

## Status

**COMPLETED WITH DOCUMENTED BENCHMARK LIMITATION** (Verified via 320 tests, zero regressions. Medium scale P95 < 2ms against 50ms budget; full-scale categories, merchants, and account endpoints meet <= 100ms budget, with global overview and trends at 135-140ms due to in-memory aggregation of 80k+ decimal rows).

## Exit Criteria

- [x] analytics endpoints work (`/overview`, `/trends`, `/categories`, `/merchants`, `/accounts/{id}`, `/accounts/{id}/unusual-spending`);
- [x] calculations are verified against hand-calculated datasets;
- [x] aggregation tests pass;
- [x] temporal boundaries are tested (half-open `[from_time, to_time)`, sub-second boundaries, zero-filled series);
- [x] API performance is acceptable at development scale (Medium scale P95 < 2 ms on 5,000 transactions; full scale evaluated on 250,000 transactions).

---

# 11. Phase 6 — Feature Engineering

## Objective

Transform transaction history into behavior-aware ML features without temporal leakage.

## Architecture & Implementation

- **Pure Functional Computation Engine (`src/finsignal/features/engine.py`):** Stateless calculation engine with zero database dependencies, zero entity mutation, and standard library algorithms (Welford's algorithm, dual heaps for medians, Decimal precision).
- **PostgreSQL Context Repository (`src/finsignal/features/repository.py`):** Asynchronous retrieval separating bounded 30-day index scans (`ix_transactions_account_occurred`) from lifetime statistical aggregations (`COUNT`, `AVG`, `STDDEV_SAMP`, `percentile_cont(0.5)::numeric`).
- **Feature Service & Streaming Extraction (`src/finsignal/features/service.py`):** Supports single-transaction online point-in-time evaluation and $O(N \log N)$ streaming batch feature extraction across dataset batches without per-transaction database queries. Caller-owned collections remain unmutated; state is strictly isolated per account.

## Feature Contract (34 Input Features — Version v1.0)

- **Amount Features (2):** `amount`, `amount_log` (via `math.log1p`).
- **Account Profile (1):** `account_age_days` (UTC difference, clamped $\ge 0.0$; `is_account_created_after_txn` reported in decoupled `FeatureMetadata`).
- **Velocity Counts (3):** `velocity_5m_count`, `velocity_1h_count`, `velocity_24h_count` (all currencies and directions, inclusive lower window boundary, strict point-in-time upper boundary).
- **Velocity Amounts (3):** `velocity_5m_amount`, `velocity_1h_amount`, `velocity_24h_amount` (direction- and currency-matched monetary sums).
- **Amount Deviation & Quality (7):**
  - Direction- and currency-matched: `amount_vs_mean_ratio`, `amount_vs_median_ratio`, `amount_zscore`, `is_amount_different_from_constant_baseline`.
  - Availability indicators: `has_direction_baseline`, `has_zero_variance_baseline`.
  - Cold-start indicator: `is_cold_start` (1 if total account historical tx count $< 3$; decoupled from account age).
  - Provisional threshold: `MIN_BASELINE_OBSERVATIONS = 3`. Below threshold, neutral sentinels returned (ratio=1.0, zscore=0.0, deviation=0).
  - Zero-variance handling: `amount_zscore = 0.0`, `has_zero_variance_baseline = 1`, `is_amount_different_from_constant_baseline = 1` iff amount != mean.
- **Device Familiarity (3):** `has_device`, `is_new_device`, `device_tx_count`.
- **Merchant Familiarity (3):** `has_merchant`, `is_new_merchant`, `merchant_tx_count`.
- **Location Familiarity (5):** `has_location`, `is_home_location` (native UUID match), `is_new_location` (home location treated as familiar), `location_tx_count`, `location_frequency` (denominator is total prior eligible transactions).
- **Category Behavior (3):** `has_category`, `is_new_category`, `category_spend_share_30d` (DEBIT-only, currency-matched spend share over preceding 30-day window $[t - 30\text{d}, t)$).
- **Temporal Features (4):** `hour_of_day` (0–23 UTC), `day_of_week` (0–6 UTC), `is_weekend` (Saturday/Sunday), `is_unusual_hour` (01:00–05:59 UTC).

## Critical Rules & Boundaries

- **Strict Point-in-Time Boundary:** `occurred_at < evaluation.occurred_at OR (occurred_at == evaluation.occurred_at AND id < evaluation.id)`. The evaluated transaction is strictly excluded from its own baseline and velocity metrics. Sub-second tie-breaking is consistent between Python (`uuid.int`) and PostgreSQL (`uuid_cmp`).
- **Ground-Truth Isolation:** Ground-truth labels (`is_fraud`, `fraud_scenario`) are never queried, loaded, or exposed as feature inputs.
- **In-Memory Generation:** Features are generated on demand or in memory; no persistent feature tables or database migrations were introduced.
- **Deferred Features:** `category_amount_mean`, `category_amount_deviation`, and `device_first_seen_age` are explicitly deferred from v1.0.

## Status

**COMPLETED WITH DOCUMENTED BENCHMARK DEVIATION** (Verified via 347 tests, zero regressions. Strict 34-feature immutable contract, pure functional engine, streaming batch extraction in 0.851s on 5,000 txs [target $\le 3.0$ s] with 27.82 MB memory [target $\le 50.0$ MB]. Single online evaluation P95 is 8.84 ms against 5.0 ms target due to unpooled local asyncpg DB roundtrips).

## Exit Criteria

- [x] feature calculations are deterministic and schema-enforced (exactly 34 model input features in immutable `FeatureVector`);
- [x] hand-calculated tests pass across all feature categories, boundaries, and sentinels;
- [x] temporal leakage tests pass with strict future-data invariance;
- [x] future labels cannot enter features (ground truth strictly isolated);
- [x] feature schema is versioned/documented (`FEATURE_VERSION = "v1.0"`, `FeatureMetadata` decoupled from `FeatureVector`);
- [x] batch extraction achieves $O(N \log N)$ scaling (5,000 transactions extracted in 0.851s without database queries during extraction);
- [x] performance evaluated against empirical goals (batch time 0.851s $\le 3$ s, memory 27.82MB $\le 50$ MB; online P95 latency deviation 8.84ms against 5ms target documented as unpooled DB roundtrip overhead).

---

# 12. Phase 7 — ML / Anomaly Detection

**Status:**
- **Implementation & Automated Tests:** **100% Completed** (46 Phase 7 unit/integration/benchmark tests passing; 393 total repository tests passing; 0 Ruff errors, 0 Mypy errors).
- **Documentation Reconciliation:** **In Progress** (reconciling architecture, database, security, and testing documents).
- **Production Release Gate:** **NOT PASSED** (blocked by unimplemented administrative artifact pruning and reconciliation tool).

## Objective

Introduce a baseline unsupervised anomaly-detection model delivering calibrated operating thresholds, deterministic feature vectorization, and artifact integrity verification without fraud label leakage.

## Initial Model

**Isolation Forest (`IsolationForestModel`)**
- Encapsulates scikit-learn's `IsolationForest` (`n_estimators=100`, `random_state=42`, `contamination="auto"`).
- Mathematical score negation: $S(X) = - \text{score\_samples}(X)$, ensuring higher scores indicate higher anomalousness.
- Binary anomaly decision: $A(X) = \mathbb{I}(S(X) \ge \tau)$.

## Pipeline

```text
Historical Transactions
        ↓
Feature Extraction (FeatureVectorizer, FEATURE_VERSION="v1.0")
        ↓
Chronological Splitting (Target 60/20/20 with equal-timestamp grouping)
        ↓
Unsupervised Fitting (IsolationForestModel, zero label leakage)
        ↓
Validation Threshold Selection (ModelEvaluator, max F1 subject to alert rate <= 5%)
        ↓
Holdout Test Evaluation (Precision, Recall, F1, PR-AUC, Scenario Recall)
        ↓
Artifact Storage & SHA-256 Hashing (ModelArtifactStore, atomic tempfile rename)
        ↓
Registry Persistence & Promotion (ModelRepository, migration 0004_model_versions)
```

## Implemented Tasks & Deliverables

- [x] Canonical 34-feature vector extraction (`FeatureVectorizer.to_numpy()`) matching `CANONICAL_FEATURE_NAMES` in strict order.
- [x] Strict schema validation enforcing finite float64 matrices and rejecting null/NaN inputs.
- [x] Unsupervised `IsolationForestModel` wrapping scikit-learn with score negation.
- [x] Deterministic chronological data splitter (`ChronologicalSplitter`) preserving indivisible equal-timestamp groups.
- [x] Validation-only threshold optimization subject to configured operational alert-rate budget ($\le 5\%$).
- [x] Sealed holdout test evaluation producing Precision, Recall, F1, PR-AUC, Scenario Recall, and Cluster Recall.
- [x] Artifact storage (`ModelArtifactStore`) enforcing path-containment validation, atomic `.tmp` file renaming, and pre-load SHA-256 integrity verification.
- [x] PostgreSQL database migration `0004_model_versions` creating registry schema with status check constraints and partial unique index `uq_model_versions_active_family`.
- [x] Model repository (`ModelRepository`) supporting lifecycle transitions (`EXPERIMENTAL -> VALIDATED -> ACTIVE -> RETIRED`) and row-locked promotion.
- [x] Service facade (`MLService`) with dynamic active-model lookup from PostgreSQL on every scoring call and local in-memory caching validated by `artifact_hash`.
- [x] Comprehensive test suite (+46 tests) and benchmark harness (`test_ml_benchmark.py`).

## Outstanding Pre-Release Blocker
- [ ] **Administrative Model Artifact Pruning Tool:** Interrupted training pipelines can leave unreferenced directories in `{model_artifacts_dir}/{model_id}`. An administrative pruning tool (`finsignal-admin prune-unreferenced-artifacts`) is required prior to production release to reconcile database records against disk and safely prune orphaned artifacts.

## Next Phase
- **Phase 8 (Risk Analysis & Explainability):** Completed.

---

# 13. Phase 8 — Risk Analysis & Explainability (Completed)

## Objective

Convert unsupervised model outputs and deterministic signals into an interpretable, reproducible risk assessment and evidence-based explainability factors.

## Implemented Architecture

```text
Point-in-Time Features (34 canonical features) + Context (amount, currency, direction, entities)
        │
        ├─────────────────────────────────────────────────┐
        ▼                                                 ▼
Unsupervised ML Inference                        Deterministic Rule Engine
(Isolation Forest, raw score S(X))               (9 Heuristic Rules)
        │                                                 │
        ▼                                                 ▼
Piecewise Linear Normalization                   Fired Rules & Structured Factors
(Anchored to validation bounds:                  (Point mapping: INFO=0, LOW=5,
 s_min -> 0.0, tau* -> 50.0, s_max -> 100.0)      MEDIUM=15, HIGH=25, CRITICAL=40)
        │                                                 │
        ▼                                                 ▼
Normalized ML Score [0, 100]                     Rule Score [0, 100]
        │                                                 │
        └────────────────────────┬────────────────────────┘
                                 ▼
                     Hybrid Scoring Engine
          Linear combination: raw = 0.60 * S_norm + 0.40 * S_rule
          Optional evidence-gated escalation floors:
            CRITICAL factor -> floor >= 75.0
            HIGH factor     -> floor >= 50.0
          Clamping: [0.00, 100.00] (rounded to 2 decimal places)
                                 │
                                 ▼
                     Risk Tier Classification
             [LOW: < 25, MEDIUM: < 50, HIGH: < 75, CRITICAL: >= 75]
                                 │
                                 ▼
                     Atomic Persistence & Lineage
             Parent risk_analyses + Child risk_factors
             Idempotent reuse via 4-tuple identity:
             (transaction_id, model_version_id, config_version, feature_vector_hash)
             PostgreSQL unique conflict classification (SQLSTATE 23505)
             Transactional audit event: TRANSACTION_RISK_ANALYZED
```

## Implemented Tasks & Deliverables

- [x] **Empirical Validation Calibration Bounds:** Captured empirical $s_{\min}$ and $s_{\max}$ alongside operating threshold $\tau^*$ from the validation partition during training (`metrics["score_min"]`, `metrics["score_max"]`); strictly isolated from the sealed holdout test partition.
- [x] **Piecewise Linear Score Normalization (`normalize_ml_score`):** Transforms continuous anomaly score into $[0.0, 100.0]$ anchored to $(s_{\min} \mapsto 0.0, \tau^* \mapsto 50.0, s_{\max} \mapsto 100.0)$ with strict validation of the invariant $s_{\min} < \tau^* < s_{\max}$.
- [x] **Deterministic Rule Engine (`RiskRuleEngine`):** Implemented 9 heuristic rules generating structured `RiskFactorDTO` instances:
  1. `COLD_START_ACCOUNT` (INFO, 0 pts)
  2. `HIGH_VELOCITY` (MEDIUM: 15 pts, HIGH: 25 pts, CRITICAL: 40 pts)
  3. `LARGE_AMOUNT_DEVIATION` (MEDIUM: 15 pts, HIGH: 25 pts, CRITICAL: 40 pts)
  4. `NEW_DEVICE` (MEDIUM: 15 pts, HIGH: 25 pts)
  5. `NEW_LOCATION` (MEDIUM: 15 pts, HIGH: 25 pts)
  6. `UNUSUAL_TIME` (LOW: 5 pts, MEDIUM: 15 pts)
  7. `BEHAVIORAL_SHIFT` (MEDIUM: 15 pts, HIGH: 25 pts)
  8. `NEW_MERCHANT` (LOW: 5 pts)
  9. `NEW_CATEGORY` (LOW: 5 pts; suppressed if behavioral shift fired)
- [x] **Hybrid Scoring Contract (`HybridScoringEngine`):** Configurable weights ($w_{\text{ml}}=0.60, w_{\text{rule}}=0.40$), evidence-gated escalation floors, and 4-tier risk classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- [x] **Canonical Input Fingerprinting (`compute_feature_fingerprint`):** Computes deterministic 64-character SHA-256 hash over all 34 canonical numeric features and result-affecting context (amount, currency, direction, entity IDs, category).
- [x] **Effective Configuration Identity Versioning (`effective_config_version`):** Computes a 12-character SHA-256 digest of all scoring weights, thresholds, escalation flags, rule policy versions, and algorithm versions, formatting as `rc_v1.0#<hash>` (fits within `VARCHAR(32)`).
- [x] **PostgreSQL Schema Migration (`0005_intelligence_risk_models.py`):** Created `risk_analyses` and `risk_factors` tables with check constraints `chk_risk_analyses_score`, `chk_risk_analyses_risk_level`, `chk_risk_factors_severity`, foreign key cascades, and composite unique constraint `uq_risk_analyses_identity` on `(transaction_id, model_version_id, config_version, feature_vector_hash)`.
- [x] **Atomic Persistence & Race-Safe Recovery (`RiskRepository`):** Atomic persistence of parent and child records using savepoints (`session.begin_nested()`), coupled with PostgreSQL driver-specific unique violation recovery (`23505` on `uq_risk_analyses_identity`) to safely resolve concurrent execution races.
- [x] **Protected REST API Endpoints (`src/finsignal/api/v1/risk.py`):**
  - `GET /api/v1/transactions/{transaction_id}/risk`: Pure query returning latest analysis and factors, accessible by `ADMIN`, `ANALYST`, `INVESTIGATOR`.
  - `POST /api/v1/transactions/{transaction_id}/risk/analyze`: Point-in-time analysis, idempotent reuse, savepoint persistence, and transactional audit event (`TRANSACTION_RISK_ANALYZED`). Enforces model lifecycle eligibility (`EXPERIMENTAL` blocked, `VALIDATED` restricted to `ADMIN`).
- [x] **Comprehensive Test Suite (+57 tests):** Test coverage spanning unit (schemas, scoring invariants, normalization, rules, scenarios, fingerprinting), integration (migration 0005, atomic persistence, race recovery, driver exception shapes), and API contracts (total repository test suite: 450 passing tests).

## Next Phase
- **Phase 9 (Investigation & Evidence):** Case management, alert triage, evidence attachment, and investigator resolution workflows.

---

# 14. Phase 9 — Investigation & Evidence

## Status: `COMPLETED`

## Objective

Turn suspicious activity into a structured, role-authorized, concurrent, and auditable investigation workflow.

## Investigation Lifecycle (Implemented)

```text
OPEN ──> UNDER_REVIEW ──> RESOLVED (Terminal & Immutable)
```

## Resolutions (Implemented)

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

## Implemented Deliverables (Milestones P9.0–P9.9)

- [x] **Database Schema Migration (`0006_investigation_models.py`):**
  - Created `investigations`, `investigation_transactions`, and `investigation_evidence` tables.
  - Foreign key constraints with `ON DELETE RESTRICT` on `assigned_to`, `investigation_id`, and `transaction_id`.
  - Check constraints: `chk_investigations_status`, `chk_investigations_priority`, `chk_investigations_resolution`, `chk_investigations_resolution_state`, `chk_inv_tx_rel_type`, `chk_inv_evidence_type`, `chk_inv_source_type`, `chk_inv_evidence_type_source_pair`, `chk_inv_evidence_source_consistency`.
  - Partial unique index: `uq_investigation_single_primary` on `(investigation_id) WHERE relationship_type = 'PRIMARY'`.
  - PostgreSQL trigger: `trg_no_update_delete_evidence` blocking `UPDATE` and `DELETE` queries on `investigation_evidence`.
- [x] **Investigation Domain Module (`src/finsignal/investigations/`):**
  - Domain models (`models.py`), Pydantic v2 request/response schemas (`schemas.py`), bounded queries and row locking in repository (`repository.py`), and business invariants in service (`service.py`).
- [x] **Primary Transaction Semantics:**
  - Partial unique index enforces at-most-one PRIMARY link in database.
  - Atomic application creation workflow (`create_investigation`) guarantees exactly-one PRIMARY link for every committed case.
  - Single transaction can be PRIMARY across multiple separate cases.
- [x] **1-Hop Related Transaction Linking:**
  - Evaluates 4-way shared-party predicate with exact `source_namespace` match. Multi-hop graph search intentionally excluded.
- [x] **Append-Only Immutable Evidence:**
  - 6 supported evidence types paired with permitted source types.
  - 64 KB JSONB payload size limit; database trigger rejection of updates and deletes.
  - Pre-persistence source existence and investigation scope validation.
- [x] **Pessimistic Concurrency & RBAC Protection:**
  - Row-level lock (`SELECT ... FOR UPDATE`) prevents concurrent update collisions.
  - Concurrent self-assignment races yield one winner (200 OK) and one 409 Conflict (`CASE_ALREADY_ASSIGNED`).
  - Explicit peer case takeover attempts return HTTP 403 Forbidden (`FORBIDDEN`).
  - Analyst restricted to case creation and read operations (mutations return 403 `FORBIDDEN`).
  - Terminal case immutability: resolved investigations cannot be altered or amended by any role, including `ADMIN`.
- [x] **Protected REST API (9 Endpoints under `/api/v1/investigations`):**
  - Implemented and registered in `src/finsignal/api/router.py`.
- [x] **Transactional Audit Integration:**
  - Emits `AuditEvent` records for all mutations (`INVESTIGATION_CREATED`, `INVESTIGATION_ASSIGNED`, `INVESTIGATION_PRIORITY_CHANGED`, `INVESTIGATION_STATUS_CHANGED`, `INVESTIGATION_RESOLVED`, `INVESTIGATION_TRANSACTION_LINKED`, `EVIDENCE_ATTACHED`) using authenticated user context as actor.
- [x] **Comprehensive Test Suite (+35 tests):**
  - Unit tests (schemas, service logic), API route tests, PostgreSQL migration/trigger persistence tests, and multi-connection concurrency tests.
  - Full project test suite: **485 passing tests** (0 failures, 0 errors).

## Next Phase
- **Phase 10 (AI Investigation Assistant):** Evidence summarization, LLM provider abstraction, and AI summary storage (Pending/Deferred).

---

# 15. Phase 10 — AI Investigation Assistant

## Objective

Add an AI layer that summarizes structured investigation evidence for human investigators.

## Core Principle

The LLM is an **evidence summarizer**, not the fraud decision-maker.

```text
Investigation
    ↓
Evidence Assembly
    ↓
Structured Investigation Context
    ↓
LLM Provider
    ↓
AI Summary
    ↓
Human Investigator
    ↓
Final Resolution
```

## Key Tasks

- provider abstraction;
- prompt template/versioning;
- structured context builder;
- evidence hash;
- provider/model metadata;
- AI summary persistence;
- output validation;
- provider error handling;
- timeout handling;
- prompt-injection resistance.

## AI Must Not

- independently decide fraud;
- invent transactions;
- invent risk factors;
- use future information;
- override human resolution;
- access arbitrary unrelated data.

## Exit Criteria

- AI summary can be generated from structured evidence;
- provider failures are handled;
- evidence grounding is tested;
- prompt injection tests pass;
- AI output cannot directly change investigation resolution.

---

# 16. Phase 11 — Testing, Security & Hardening

## Objective

Perform system-wide verification before release.

## Testing

- unit tests;
- integration tests;
- API tests;
- authentication tests;
- RBAC tests;
- IDOR tests;
- ingestion tests;
- feature tests;
- temporal leakage tests;
- ML evaluation tests;
- investigation workflow tests;
- AI grounding tests;
- migration tests;
- performance tests;
- failure-injection tests.

## Security

- dependency audit;
- secret review;
- upload security;
- CSV injection;
- SQL injection;
- authorization review;
- JWT validation;
- sensitive logging review;
- CORS review;
- production configuration review.

## ML Validation

Compare:

- precision;
- recall;
- F1;
- PR-AUC;
- false-positive rate;
- false-negative rate;
- alert volume;
- scenario-level detection;
- account-level detection.

## Exit Criteria

- critical tests pass;
- no known critical authorization bypass;
- no known temporal leakage;
- model evaluation is documented;
- performance is acceptable;
- CI gates pass;
- release checklist is complete.

---

# 17. Phase 12 — Docker, Deployment & Backend/ML Release

## Objective

Package the Backend + ML platform into a reproducible deployable release.

## Deployment Components

Initial deployment should remain intentionally simple:

```text
FastAPI Application
        ↓
PostgreSQL
```

Optional supporting services should only be introduced when justified.

## Key Tasks

- production Dockerfile;
- Docker Compose for local development;
- environment configuration;
- database migration execution;
- health endpoint;
- readiness endpoint;
- structured logging;
- production configuration;
- model artifact packaging;
- seed/data-generation tooling;
- backup considerations;
- deployment documentation.

## Exit Criteria

- application builds from clean environment;
- container starts successfully;
- database migrations execute;
- health/readiness checks work;
- model artifacts load correctly;
- configuration is environment-driven;
- no secrets are committed;
- deployment procedure is documented.

---

# 18. Backend + ML v1.0 Release Gate

The Backend + ML release is complete only when the following are true:

### Backend

- [ ] FastAPI application is stable.
- [ ] PostgreSQL schema is finalized for v1.
- [ ] Authentication works.
- [ ] RBAC works.
- [ ] Dataset ingestion works.
- [ ] Transaction APIs work.
- [ ] Analytics work.
- [ ] Investigation workflow works.
- [ ] Evidence management works.
- [ ] Audit logging works.
- [ ] API documentation is complete.

### ML

- [ ] Synthetic dataset generator works.
- [ ] Behavioral features work.
- [ ] Temporal leakage prevention is verified.
- [ ] Isolation Forest baseline works.
- [ ] Hybrid risk scoring works.
- [ ] Risk factors are explainable.
- [ ] Scenario-level evaluation exists.
- [ ] Account-level evaluation exists.
- [ ] Model versioning exists.
- [ ] Reproducibility is verified.

### AI

- [ ] Provider abstraction exists.
- [ ] Evidence context is controlled.
- [ ] AI summaries are grounded.
- [ ] Prompt-injection tests pass.
- [ ] Provider failures are handled.
- [ ] Human resolution remains authoritative.

### Quality

- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] API/security tests pass.
- [ ] Migration tests pass.
- [ ] Performance baseline is documented.
- [ ] CI is green.
- [ ] Documentation is synchronized.

---

# 19. Suggested Implementation Order Within Phases

Each phase should generally follow this internal sequence:

```text
1. Read relevant documentation
        ↓
2. Inspect current repository state
        ↓
3. Define implementation boundaries
        ↓
4. Implement domain/model changes
        ↓
5. Implement service logic
        ↓
6. Implement API layer
        ↓
7. Add tests
        ↓
8. Run focused tests
        ↓
9. Run full regression suite
        ↓
10. Review documentation
        ↓
11. Commit
```

No phase should proceed simply because the code compiles.

---

# 20. Development Scale Progression

The project should grow through controlled data sizes.

## Stage A — Small

```text
100 accounts
~5,000 transactions
```

Purpose:

- development;
- debugging;
- feature validation;
- fast tests.

## Stage B — Medium

```text
1,000 accounts
~50,000 transactions
```

Purpose:

- integration testing;
- model evaluation;
- query performance;
- behavior validation.

## Stage C — Full

```text
5,000 accounts
~250,000 transactions
```

Purpose:

- realistic evaluation;
- performance baseline;
- portfolio demonstration;
- final release validation.

---

# 21. Git / Commit Strategy

Each phase should result in coherent commits.

Preferred structure:

```text
feat: implement transaction ingestion
test: add transaction ingestion tests
docs: update ingestion documentation
```

Avoid one enormous commit containing an entire phase when the phase naturally contains independent components.

Before committing:

```text
git status
git diff
test suite
lint
type checks
```

---

# 22. Definition of Done for a Phase

A phase is complete only when:

- implementation is complete;
- focused tests pass;
- regression tests pass;
- security implications are reviewed;
- documentation reflects the final behavior;
- no known critical TODO remains;
- code follows `CODING_STANDARDS.md`;
- relevant architectural decisions are recorded;
- Git working tree is understood;
- commit is created.

---

# 23. Documentation Synchronization

Implementation must remain synchronized with:

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

If implementation intentionally diverges from an architectural decision, the decision must be reviewed and updated rather than silently ignored.

---

# 24. Architecture Decision Checkpoints

The following checkpoints require explicit review:

### Before Phase 2

Confirm database model and transaction representation.

### Before Phase 6

Confirm historical feature semantics and temporal boundaries.

### Before Phase 7

Confirm ML feature set and leakage controls.

### Before Phase 8

Confirm risk-score semantics and thresholds.

### Before Phase 9

Confirm investigation lifecycle and evidence model.

### Before Phase 10

Confirm AI provider abstraction and evidence boundary.

### Before Phase 12

Confirm deployment architecture and operational requirements.

---

# 25. Deferred Future Roadmap

After Backend + ML v1.0 is complete, future work may include:

```text
Frontend Documentation
        ↓
Frontend Implementation
        ↓
Advanced ML
        ↓
Graph-Based Analysis
        ↓
RAG / Knowledge Retrieval
        ↓
Real-Time Streaming
        ↓
Distributed Processing
        ↓
Advanced Model Operations
```

Possible future technologies:

- React/TypeScript;
- Kafka;
- Redis;
- Celery;
- MLflow;
- graph databases;
- graph ML;
- RAG;
- vector search;
- streaming anomaly detection.

These are deliberately excluded from the initial release.

---

# 26. Frontend Boundary

The frontend is **not part of the current roadmap execution**.

Once the Backend + ML release is complete, a new documentation phase will define:

- frontend PRD;
- frontend technical requirements;
- frontend architecture;
- frontend design;
- frontend testing;
- frontend implementation roadmap.

The current backend roadmap only defines the API and system boundaries required for future frontend consumption.

No frontend implementation work should be pulled into the current phases merely to make the system visually complete.

---

# 27. Portfolio Milestones

The project should produce demonstrable milestones.

## Milestone 1 — Working Backend

```text
Authentication
+
Accounts
+
Transactions
+
PostgreSQL
+
API
```

## Milestone 2 — Data Intelligence

```text
Dataset
+
Analytics
+
Behavioral Features
```

## Milestone 3 — ML Intelligence

```text
Features
+
Isolation Forest
+
Risk Scoring
+
Evaluation
```

## Milestone 4 — Investigation Platform

```text
Risk
+
Investigation
+
Evidence
+
Audit
```

## Milestone 5 — AI-Assisted Investigation

```text
Evidence
+
LLM Summary
+
Human Resolution
```

## Milestone 6 — Backend + ML Release

```text
Tested
+
Secured
+
Dockerized
+
Documented
+
Deployable
```

Only after Milestone 6 does frontend development begin.

---

# 28. Final Roadmap Principle

FinSignal should not attempt to look like a complete banking platform from the beginning.

The implementation should progressively establish:

```text
Correct Data
      ↓
Correct Domain
      ↓
Correct Analytics
      ↓
Correct Historical Features
      ↓
Useful ML
      ↓
Explainable Risk
      ↓
Structured Investigation
      ↓
Grounded AI Assistance
      ↓
Tested & Secure Backend
      ↓
Backend + ML v1.0
```

The frontend is intentionally the **next major development track after this chain is complete**.

The success criterion for the current roadmap is therefore not visual completeness. It is a backend and ML platform that can ingest financial transactions, understand account behavior, identify anomalous activity, provide evidence-backed risk intelligence, support human investigations, and produce trustworthy AI-assisted summaries without compromising financial correctness, temporal integrity, security, or explainability.
