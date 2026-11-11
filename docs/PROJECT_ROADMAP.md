# FinSignal — Project Roadmap

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Roadmap  
**Scope:** Backend + ML v1.0.0 (Completed) & Frontend Implementation Track (Phases F0–F8)
**Status:** Backend + ML v1.0.0 Released / Phase F0 Complete / Phase F1 CONDITIONALLY READY (Pending Formal Acceptance)
**Version:** 1.2.1
**Last Updated:** 2026-11-11

---

## 1. Purpose

This document defines the implementation roadmap for the first major version of FinSignal.

The roadmap covers the **Python backend, financial analytics, ML/anomaly detection, investigation workflows, AI-assisted investigation backend, testing, security, and deployment**.

The Backend + ML v1.0.0 scope is fully completed and released. The frontend implementation track (Phases F0–F8) is now integrated into this roadmap as the active next development track following completion of frontend planning documentation.

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
Backend/ML Release & Finalization
   ↓
Backend + ML v1.0
   ↓
Phase 13
Containerization & Production Deployment
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
- **Production Release Gate:** **RECONCILED** (automated artifact pruning CLI deferred to Phase 13 operational tooling per ADR-073; manual safe recovery documented; model registry verified).

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

## Implemented Work & Engineering Components

- [x] **Dedicated Domain Package (`src/finsignal/ai/`):**
  - Fully decoupled architecture isolating AI context building, prompting, provider abstraction, repository persistence, and orchestration from `src/finsignal/investigations/`.
- [x] **Database Schema & Migration (`0007_ai_models.py`):**
  - Table `ai_summaries` with UUID primary key, foreign key to `investigations.id` (`ON DELETE RESTRICT`), provider/model metadata, versioned prompt tracking, dual 64-char SHA-256 digests (`evidence_hash`, `context_hash`), UUID generation tokens, and `JSONB(none_as_null=True)` summary payload.
  - Check constraints: `chk_ai_summaries_status` (`PENDING`, `COMPLETED`, `FAILED`) and `chk_ai_summaries_lifecycle_state` enforcing exact nullability invariants across lifecycle phases.
  - Concurrency & retrieval indexes: partial unique index `uq_ai_summaries_one_pending_per_investigation` on `(investigation_id) WHERE status = 'PENDING'` preventing duplicate concurrent generation leases, and composite index `ix_ai_summaries_investigation_created` on `(investigation_id, created_at DESC, id)` for deterministic retrieval.
- [x] **Two-Transaction Lifecycle under REPEATABLE READ Snapshot Isolation:**
  - **Transaction 1 (Reservation & Snapshot):** Sets `isolation_level="REPEATABLE READ"` before beginning transaction, locks `investigation` row via `SELECT ... FOR UPDATE`, validates state/authorization, lazily recovers expired pending attempts, verifies no active pending attempt exists, loads the full investigation graph eagerly, computes dual fingerprints, and persists a `PENDING` summary row with a cryptographically unique `generation_token`. Implements bounded exponential backoff retries for PostgreSQL serialization failure `40001`.
  - **Provider Execution:** Executes provider generation strictly outside active database transactions, preventing connection pool exhaustion and lock starvation during external network or model latency.
  - **Transaction 2 (Terminal Persistence & Audit):** Atomically commits terminal status (`COMPLETED` or `FAILED`), structured output, and an `AuditEvent` (`AI_SUMMARY_GENERATED` or `AI_SUMMARY_FAILED`) using compare-and-swap (CAS) token fencing (`WHERE id = :id AND status = 'PENDING' AND generation_token = :token`). Outdated or expired leases are safely discarded.
- [x] **Expired PENDING Recovery with Atomic Audit Logging:**
  - `recover_expired_pending` detects orphaned pending records older than `ai_pending_timeout_seconds` (default 60s), rotates `generation_token` to fence out delayed responses, sets status to `FAILED`, and commits an `AI_SUMMARY_FAILED` audit event within the same database transaction only if the conditional update affects a row.
- [x] **Dual Fingerprinting & Grounded Context Assembly:**
  - `compute_authoritative_evidence_hash`: Computes SHA-256 digest over canonical sorted JSON of case metadata, primary transaction, risk analysis, risk factors, related transactions, untruncated evidence records, and account `status` and `account_type`. Mutating account standing (e.g. `ACTIVE` -> `FROZEN`) alters the authoritative fingerprint.
  - `build_bounded_context`: Assembles prioritized prompt context enforcing strict item (`ai_max_evidence_items`) and byte budgets (`ai_max_context_bytes`), computing a separate `context_hash`.
  - Staleness detection: `GET /api/v1/investigations/{id}/ai-summary` recomputes the authoritative hash and flags `is_stale: true` if underlying case or account facts have mutated.
- [x] **Prompt Engineering & Nonce-Based Defense-in-Depth:**
  - Versioned template `pv_1.0` with explicit advisory-only system instruction.
  - Untrusted data containment: wraps structured context within cryptographic nonce tags (`<case_context nonce="...">`) and escapes closing tag delimiters (`</` -> `<\u002F`). Instructions explicitly declare all transaction notes, merchant names, and evidence text to be untrusted data.
- [x] **Two-Stage Output & Grounding Validation:**
  - Validates raw JSON output against strict Pydantic v2 schema `AISummaryOutput` (`executive_summary`, `observed_facts`, `derived_signals`, `potential_interpretations`, `uncertainties_and_limitations`).
  - Validates citation integrity: every cited UUID in `cited_evidence_ids` and `cited_transaction_ids` must exist in the provided snapshot. Phantom citations trigger `AISummaryGroundingError` (HTTP 502).
- [x] **Provider Abstraction & Mock Provider:**
  - `BaseAIProvider` abstract contract.
  - `MockAIProvider` with deterministic scenario outputs, simulated latency, and configurable fault injection (`fail_generation`, `timeout`, `malformed_json`, `grounding_failure`).
  - Production external LLM credentials remain intentionally unconfigured and deferred.
- [x] **Protected REST API Endpoints:**
  - `POST /api/v1/investigations/{id}/ai-summary`: Synchronous generation or cached return with optional `{ "force_refresh": bool }`. Restricted to `ADMIN` and assigned `INVESTIGATOR`.
  - `GET /api/v1/investigations/{id}/ai-summary`: Retrieves latest summary with real-time `is_stale` evaluation. Restricted to `ADMIN`, `ANALYST`, and assigned `INVESTIGATOR`.
  - `GET /api/v1/investigations/{id}/ai-summary/history`: Deterministic paginated history listing (`created_at DESC, id DESC`).
- [x] **Comprehensive Test Suite (+44 tests):**
  - Unit tests for schemas, prompts, context determinism, account attribute invalidation, mock provider, and service orchestration.
  - Integration tests for Alembic migration lifecycle, database check constraints, JSONB null handling, `ON DELETE RESTRICT` cascade blocking, advisory locks, partial unique index concurrency, and atomic expired pending recovery with audit logging.
  - API tests verifying RBAC matrix, investigator assignment enforcement, force refresh, history pagination, and standard 400/403/404/409/502/504 error envelopes.
  - Full project test suite baseline: **529 passing tests** (0 failures, 0 errors, 0 lint/mypy issues).

## AI Operational Limitations

- **Mock Provider Only:** Only `MockAIProvider` is currently implemented; live Anthropic, OpenAI, or other external LLM integrations are intentionally deferred.
- **Citation Existence vs. Semantic Truth:** Grounding validation enforces that cited evidence and transaction UUIDs exist in the case context, but semantic claim verification remains the responsibility of the human investigator.
- **Strictly Advisory:** AI summaries cannot resolve investigations, alter risk scores, or mutate evidence.

## Next Phase

- **Phase 11 (Testing, Security & Hardening):** Full-system security review, end-to-end integration flows, and pre-deployment hardening.

---

# 16. Phase 11 — Testing, Security & Hardening

## Objective

Perform system-wide security hardening, resource bounding, performance optimization, and integration verification before release packaging.

## Implemented Work & Milestones

### Milestone 11.1 — Security & Environment Hardening
- [x] **Configurable CORS Middleware (`src/finsignal/main.py`, `src/finsignal/core/config.py`):**
  - FastAPI `CORSMiddleware` integrated with explicit `cors_origins` list, methods, and exposed correlation headers (`expose_headers=["X-Request-ID"]`).
  - Strict credential isolation: `allow_credentials=True` enabled with explicit domain origins. Wildcard `*` with credentials is systematically rejected at configuration initialization (`validate_cors_origins` in `src/finsignal/core/config.py`). Note that CORS enforces browser-origin policy and does not restrict non-browser HTTP clients.
- [x] **Bounded Streaming Upload & Recovery (`src/finsignal/api/v1/datasets.py`, `src/finsignal/dataset/service.py`):**
  - Replaced unconstrained file loading with chunk-by-chunk streaming enforcement (`MAX_UPLOAD_SIZE_BYTES = 52_428_800`, 50 MB hard limit).
  - Raised dedicated `PayloadTooLargeError` returning HTTP 413 immediately when stream length exceeds 50 MB.
  - Transparent support for standard UTF-8 and UTF-8 BOM via `utf-8-sig` decoding.
  - Safe stream detachment (`text_stream.detach()`) preventing Starlette `UploadFile` premature closing.
  - Explicit `csv.Error` handling: malformed CSV records or oversized CSV fields rollback the transaction and fail the import cleanly with HTTP 422 (`CSV_PARSE_ERROR` / `CSV_FIELD_SIZE_EXCEEDED`).
- [x] **Strict OS Environment Variable Isolation (`src/finsignal/core/config.py`):**
  - Custom settings source `_FinSignalEnvSettingsSource` strips ambient OS environment variables lacking the `FINSIGNAL_` prefix (`DEBUG` in OS environment cannot override application settings).
  - Preserves backward compatibility for un-prefixed values loaded explicitly from `.env` files.
  - Preserves strict boolean casting semantics without unsafe string conversion.
- [x] **Sliding-Window Login Rate Limiter (`src/finsignal/auth/limiter.py`, `src/finsignal/api/v1/auth.py`):**
  - Thread-safe, non-blocking in-memory rate limiter tracking failed attempts in a sliding window (5 attempts per 60 seconds per IP + email pair).
  - Atomic in-flight admission control: in-flight attempt reservations bound concurrent burst volume to `max_attempts` (default 5).
  - Guaranteed eviction safety: active keys (`in_flight > 0`) are never evicted when `max_tracked_keys = 10_000` is reached; admissions under total saturation are safely rejected without evicting active reservations.
  - Returns HTTP 429 (`RATE_LIMIT_EXCEEDED`) with RFC-compliant `Retry-After` header.
  - Documented operational limitation: Rate limiter is currently in-memory and per-process; horizontal multi-instance scaling requires Redis or distributed state. Reverse proxy header trust requires configured trusted proxy middleware.
- [x] **Relational Counterparty Namespace Foreign Key (`migrations/versions/0008_security_hardening.py`):**
  - Adds composite foreign key constraint `fk_transactions_counterparty_namespace`: `FOREIGN KEY (counterparty_account_id, source_namespace) REFERENCES accounts(id, source_namespace) ON DELETE RESTRICT`.
  - Enforces database-level isolation ensuring counterparty accounts belong to the identical dataset provenance namespace.
- [x] **Append-Only Audit Log Immutability Trigger (`migrations/versions/0008_security_hardening.py`):**
  - Implements PostgreSQL trigger `trg_no_update_delete_audit_events` and function `trg_enforce_audit_events_immutability()` blocking `UPDATE` and `DELETE` queries on `audit_events`.
  - Documented scope: Defense-in-depth against SQL application tampering; does not provide hardware/cryptographic WORM immutability and does not protect against superuser `TRUNCATE` or table drop operations.

### Milestone 11.2 — Ingestion & Analytical Performance Hardening
- [x] **Batched Ingestion Lookups (`src/finsignal/dataset/ingestion/engine.py`):**
  - Replaced per-row database roundtrips with batched canonical lookups (`canonical_id = ANY(...)`).
  - Added bounded in-memory reference entity caching (`max_cache_entries = 10_000`) for account, merchant, and device lookups.
  - Intra-batch duplicate resolution: resolves repeated canonical references within the same batch after initial flushing.
- [x] **Feature Engine SQL Pushdown (`src/finsignal/features/repository.py`):**
  - Optimized entity familiarity lookups (`location_tx_count`, `device_tx_count`, `merchant_tx_count`) via targeted database counts.
  - Note: Code changes implemented and passing unit/integration tests; full 250k-row performance benchmark verification is documented as a pre-release task.

### Milestone 11.3 — ML Governance & Test Hardening
- [x] **Deterministic Chronological Splitting (`src/finsignal/ml/split.py`):**
  - Added secondary tie-breaker sorting `str(id) ASC` for identical timestamps (`occurred_at ASC, str(id) ASC`) preventing nondeterministic split boundaries across platforms.
- [x] **Model Evaluation Budget Guardrails (`src/finsignal/ml/evaluator.py`):**
  - Enforced strict alert-rate budget checks during threshold selection, preventing silent over-alerting.
- [x] **Unreferenced Model Artifact Pruning CLI (`finsignal-admin prune-unreferenced-artifacts`):**
  - Formally deferred to Phase 13 operational tooling per ADR-073; manual safe recovery procedure documented.

### Milestone 11.4 — Documentation Reconciliation & Quality Gates
- [x] Comprehensive test suite expansion: **562 passed tests** (0 failed, 0 errors, 79.56s).
- [x] Static analysis: Ruff lint clean, Ruff format clean (210 files), Mypy clean (199 source files).
- [x] Stage A Documentation reconciliation across all canonical project docs (completed).

## Status

`COMPLETED (Formally accepted on 2026-11-04 per docs/PHASE_11_FORMAL_ACCEPTANCE.md)`

---

# 17. Phase 12 — Backend/ML Release & Finalization

## Objective

Deliver the formal release of FinSignal Backend + ML v1.0.0 as an architecturally verified, versioned software application and library.

## Sub-Milestones

### Milestone 12.0 — Formal Phase 11 Acceptance
- Formally accepted all Phase 11 security hardening, bounded streaming upload, and ML governance deliverables (`docs/PHASE_11_FORMAL_ACCEPTANCE.md`).

### Milestone 12.1 — Release Readiness & Security Hardening
- Implemented CORS wildcard-origin rejection at application configuration initialization (`src/finsignal/core/config.py`).
- Added correlation tracing exposure (`expose_headers=["X-Request-ID"]`) in `CORSMiddleware`.
- Reconciled documentation claims regarding login rate limiter burst admission and audit immutability boundaries.
- Ratified ADR-065 and ADR-067 through ADR-072; approved ADR-073 in `docs/DECISIONS.md`.
- Synchronized package version to `1.0.0` across `pyproject.toml`, `src/finsignal/__init__.py`, and `src/finsignal/main.py`.

### Milestone 12.2 — Final Verification
- Executed complete automated test suite (562 tests passing, 0 failures, 0 errors).
- Validated static analysis: Ruff clean (0 errors), Ruff format clean (210 files), Mypy clean across 199 source files.
- Verified database migration integrity (linear chain 0001–0008, roundtrip downgrade/upgrade on disposable test DBs).

### Milestone 12.3 — Versioned Release Packaging
- Prepared release notes (`docs/RELEASE_NOTES_v1.0.0.md`) and formal release report (`docs/PHASE_12_RELEASE_REPORT.md`).
- Prepared local annotated Git release tag `v1.0.0`.

## Exit Criteria

- Phase 11 formally accepted with documentation reconciliation complete.
- ADRs 065, 067–072 ratified; ADR-073 approved.
- Security and configuration validations verified with regression tests.
- Full automated test suite passes (100% clean).
- Package versions consistent at `1.0.0`.
- Working tree clean with annotated tag `v1.0.0` prepared.

## Status

`COMPLETED`

---

# 17.1 Phase 13 — Containerization & Production Deployment (Deferred Scope)

## Objective

Package the verified Backend + ML v1.0.0 platform for containerized execution and production deployment (ADR-073).

## Key Tasks

- Production multi-stage `Dockerfile`.
- `docker-compose.yml` for local multi-container development (FastAPI + PostgreSQL).
- Production reverse-proxy and TLS configuration.
- Redis-backed distributed rate limiting for horizontal multi-instance scaling.
- Automated model artifact pruning CLI (`finsignal-admin prune-unreferenced-artifacts`).
- Formal 250k-row database ingestion scale benchmark.
- Cloud deployment and container registry orchestration.

---

# 18. Backend + ML v1.0 Release Gate

The Backend + ML release is complete only when the following are true:

### Backend

- [x] **FastAPI application is stable:** Verified in `src/finsignal/main.py` via lifespan engine lifecycle, RequestIdMiddleware, and custom error hierarchy.
- [x] **PostgreSQL schema is finalized for v1:** Verified via linear migrations 0001–0008, composite foreign keys, and trigger immutability.
- [x] **Authentication works:** Verified with Argon2id password hashing, constant-time dummy verification, and JWT access tokens.
- [x] **RBAC works:** Verified via `require_roles` dependency across ADMIN, ANALYST, and INVESTIGATOR roles.
- [x] **Dataset ingestion works:** Verified with 50 MB bounded streaming, UTF-8 BOM recovery, advisory locks, and canonical deduplication.
- [x] **Transaction persistence & ingestion work:** Verified with immutable canonical persistence, row-level provenance ledger, and transaction risk query/eval APIs (`/transactions/{id}/risk`). (Note: general collection browsing endpoints `GET /api/v1/transactions` are an identified API contract prerequisite for Frontend Phase F3).
- [x] **Analytics work:** Verified via async SQL aggregate pushdown, timezone-aware calendar bucketing, and statistical median outliers.
- [x] **Investigation workflow works:** Verified via manual triage queue, atomic primary transaction binding, and CAS status lifecycles.
- [x] **Evidence management works:** Verified with polymorphic evidence types, SHA-256 payload hashing, and append-only trigger defense.
- [x] **Audit logging works:** Verified via transactional `AuditEvent` persistence and database trigger immutability.
- [x] **API documentation is complete:** Verified via OpenAPI specification and `docs/API_GUIDELINES.md`.

### ML

- [x] **Synthetic dataset generator works:** Verified via deterministic PRNG master seed, reference entities, and fraud scenarios F001–F007.
- [x] **Behavioral features work:** Verified with canonical 34-feature vector v1.0 and O(N log N) point-in-time calculation.
- [x] **Temporal leakage prevention is verified:** Verified with half-open intervals `[eval_t - window, eval_t)` and index scan pushdown.
- [x] **Isolation Forest baseline works:** Verified with continuous anomaly score negation and contamination calibration.
- [x] **Hybrid risk scoring works:** Verified with composite scoring ($w_{\text{ml}}=0.60, w_{\text{rule}}=0.40$) and anchored normalization.
- [x] **Risk factors are explainable:** Verified with structured factors, rule weights, and human-readable operational rationale.
- [x] **Scenario-level evaluation exists:** Verified with recall tracking across individual fraud scenarios F001–F007.
- [x] **Account-level evaluation exists:** Verified with cluster/account detection recall metrics.
- [x] **Model versioning exists:** Verified via PostgreSQL `model_versions` registry, status lifecycle, and artifact hashing.
- [x] **Reproducibility is verified:** Verified with deterministic chronological splitting tie-breaker and PRNG seed stability.

### AI

- [x] **Provider abstraction exists:** Verified with `BaseAIProvider` and configurable `MockAIProvider` with fault injection.
- [x] **Evidence context is controlled:** Verified with REPEATABLE READ snapshot isolation and dynamic nonce delimiter tags.
- [x] **AI summaries are grounded:** Verified via two-stage Pydantic schema validation and entity citation verification.
- [x] **Prompt-injection tests pass:** Verified via prompt delimiter isolation and closing-tag neutralization.
- [x] **Provider failures are handled:** Verified with timeout recovery, token rotation, and CAS token fencing.
- [x] **Human resolution remains authoritative:** Verified with strict advisory role; AI cannot mutate investigation decisions.

### Quality

- [x] **Unit tests pass:** Verified (415 unit/API tests passing in 6.7s).
- [x] **Integration tests pass:** Verified (147 integration tests against PostgreSQL).
- [x] **API/security tests pass:** Verified (CORS wildcard rejection, login sliding-window rate limiter, upload boundaries).
- [x] **Migration tests pass:** Verified (downgrade-to-base and upgrade-to-head roundtrip on disposable databases).
- [x] **Performance baseline is documented:** Verified (5k feature, analytics, and ML inference benchmarks documented; 250k DB ingestion deferred to Phase 13 per ADR-073).
- [x] **CI is green:** Verified locally against exact workflow specifications (`ruff check .`, `ruff format --check .`, `mypy src tests`, `alembic upgrade head`, `pytest -v`; remote CI recorded per workflow definition).
- [x] **Documentation is synchronized:** Verified across TRD, Testing Strategy, Security, Decisions, and Roadmap.

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

The success criterion for the backend roadmap was not visual completeness. It was a backend and ML platform that can ingest financial transactions, understand account behavior, identify anomalous activity, provide evidence-backed risk intelligence, support human investigations, and produce trustworthy AI-assisted summaries without compromising financial correctness, temporal integrity, security, or explainability. That platform is now released as v1.0.0.

---

# 29. Frontend Implementation Track (Phases F0–F8)

Following the completion of Backend + ML v1.0.0 and the formal finalization of the frontend planning suite (`FRONTEND_PRD.md`, `FRONTEND_TRD.md`, `FRONTEND_ARCHITECTURE.md`, `FRONTEND_API_INTEGRATION.md`, `FRONTEND_SECURITY.md`, `FRONTEND_TESTING_STRATEGY.md`, `FRONTEND_ROADMAP.md`, `FRONTEND_DESIGN.md`), this section integrates the frontend implementation sequence into the master project roadmap.

### High-Level Phase Sequence

```text
F0 — Decisions, Contract Verification & Repository Readiness
  ↓
F1 — Application Foundation & Design System
  ↓
F2 — Authentication, Session & Application Shell
  ↓
F3 — Analytics, Transaction Exploration & Risk
  ↓
F4 — Dataset Import & Processing Visibility
  ↓
F5 — Investigation Queue, Workspace & Lifecycle
  ↓
F6 — Evidence & AI-Assisted Investigation
  ↓
F7 — Integration, Accessibility, Security & Hardening
  ↓
F8 — Deployment, Acceptance & Frontend Release
```

---

## Phase F0 — Decisions, Contract Verification & Repository Readiness

- **Objective:** Eliminate architectural and contract unknowns before frontend feature construction. Execute the backend API readiness enhancement after architectural governance has been ratified (ADR-074 through ADR-077), verify the running FastAPI `/openapi.json` contract, and configure frontend repository tooling.
- **Key Sub-Tasks:**
  - **F0.1 Architectural Governance (COMPLETED):** ADR-074, ADR-075, ADR-076, and ADR-077 are `ACCEPTED`. ADR-075 selects in-memory Bearer-token storage for the MVP; implementation must follow `DECISIONS.md` and `FRONTEND_SECURITY.md`.
  - **F0.2 Backend API Readiness Enhancement (COMPLETED):** Implemented shared monetary types (`src/finsignal/common/types.py`) and the three approved backend read endpoints per `docs/BACKEND_API_READINESS.md` without modifying release history:
    - `GET /api/v1/transactions` (paginated collection querying and multi-field filtering)
    - `GET /api/v1/transactions/{transaction_id}` (single transaction detail retrieval with optional `source_namespace` partition fence)
    - `GET /api/v1/datasets/imports` (paginated dataset import history)
  - **F0.3 OpenAPI Type Generation & Contract Verification (COMPLETED):** Exported OpenAPI from `create_app().openapi()` (`frontend/openapi.json`), generated static TypeScript DTOs (`frontend/src/api/generated/schema.ts`) via `openapi-typescript`, and added automated drift verification (`npm run check:types-drift`, ADR-076).
  - **F0.4 Repository Scaffolding & Tooling (COMPLETED):** Scaffolded React + TypeScript + Vite application in `frontend/` with pinned `package-lock.json` (Node.js `>=20.0.0`, `.nvmrc`), strict compiler flags, Tailwind CSS, ESLint, Prettier, Vitest (`tests/smoke.test.tsx`), Playwright configuration, API client (`src/lib/api/client.ts`), and in-memory token store (`src/lib/auth/token-store.ts`).
- **Exit Criteria:**
  - [x] All four frontend ADRs ratified in `DECISIONS.md` (ADR-074 through ADR-077 are `ACCEPTED`).
  - [x] Backend API readiness endpoints implemented, covered by passing unit/API/PostgreSQL integration tests (`593` backend tests), and verified in OpenAPI.
  - [x] Frontend TypeScript types generated directly from backend OpenAPI with automated zero-drift verification.
  - [x] Frontend repository builds cleanly (`npm run build`), passes lint/format/typecheck, and executes baseline Vitest unit tests (`4` passed).
- **Status:** `COMPLETED (2026-11-10) — F0.1–F0.4 complete and verified; ready for Phase F1`

---

## Phase F1 — Application Foundation & Design System

- **Objective:** Build accessible design system primitives, application foundation providers, routing resilience, and theme tokens conforming to `FRONTEND_DESIGN.md` (Coinbase clarity + IBM enterprise structure). Note: Application Shell construction (Collapsible Sidebar, Header, Breadcrumbs, User Profile indicator) belongs to Phase F2 (`FRONTEND_ROADMAP.md` §8), not Phase F1.
- **Completed Tasks & Audit Remediation (2026-11-11):**
  - Configured centralized Tailwind CSS v4 design tokens (`frontend/src/styles/tokens.css`, non-circular `--fs-*` → `@theme inline`), global `:focus-visible`, `.tabular-nums`, and `prefers-reduced-motion` (`frontend/src/index.css`).
  - Implemented 10 domain-agnostic UI primitives (`Button`, `Badge`, `Card`, `Input`, `Select`, `Table`, `Dialog`, `Alert`, `Skeleton`/`TableSkeleton`, `EmptyState`), `QueryProvider`/`AppProviders`, `RootErrorBoundary`, `FoundationPage`, and `NotFoundPage`.
  - Configured Vitest `5.1.0`, React Testing Library, MSW `2.15.0` (`onUnhandledRequest: "error"`), and `.github/workflows/ci.yml` (`frontend` job).
  - Remediated all blocking F1 audit findings: Prettier formatting across 17 files (`F1-AUD-001`), mutually exclusive `Input` state utilities & `TableSkeleton` `text-sm` height (`F1-AUD-003`), cross-realm `AbortSignal` listener bridge in `tests/setup.ts` (`F1-AUD-004`), `Button` `asChild` prop stripping (`F1-AUD-008`), and approved upgrades to `zod@4.6.7` (`ADR-078`) and `vitest@5.1.0` with Node `24` alignment (`ADR-079`).
- **Verification Snapshot:** Prettier (`PASS`), ESLint (`PASS`), TypeScript (`PASS`), Vitest (`47/47 PASS` across 15 files), Vite production build (`PASS`), OpenAPI drift check (`PASS`), `npm audit --omit=dev` (`0` vulnerabilities), full `npm audit` (`7 moderate` dev-only `minimatch@10.2.6` advisories), system-Chrome computed-style/responsive/Dialog verification (`PASS`), remote GitHub Actions CI (`PENDING`).
- **Explicitly Deferred Findings:** `F1-AUD-005` (API client/env edge-case hardening → F2 API milestone), `F1-AUD-006` (committed Playwright `tests/e2e/` suite & `webServer` → F2 testing milestone), `F1-AUD-009` (`Button` `size="icon"` loading & `Alert` attribute passthrough → future UI refinement).
- **Exit Criteria:**
  - [x] Shared UI component library passes automated rendering, keyboard focus, accessibility, and Chrome computed-style checks (`47/47` Vitest tests).
  - [x] Zero hard-coded color classes in `frontend/src/`; styles derive from centralized tokens.
  - [x] Zero production dependency vulnerabilities (`npm audit --omit=dev` = `0`).
  - [ ] Formal owner acceptance of temporary dev-only `minimatch@10.2.6` security exception (`ADR-080`, `PENDING OWNER APPROVAL`) and first remote GitHub Actions CI run.
- **Status:** `CONDITIONALLY READY (2026-11-11) — implementation remediation and local verification complete; formal acceptance pending security-exception approval (ADR-080) and remote CI verification`

---

## Phase F2 — Authentication, Session & Application Shell

- **Objective:** Deliver secure login, authenticated session state, role-aware routing, and main application layout (including Collapsible Sidebar, Header, Breadcrumbs, and User Profile indicator).
- **Key Tasks:**
  - Build Login page with client-side format validation (Argon2id password requirements, normalized email).
  - Implement in-memory JWT authentication adapter per approved ADR-075.
  - Implement current-user context (`GET /api/v1/auth/me`) and permission-aware navigation helpers.
  - Implement protected route wrappers with unauthorized/forbidden fallback screens.
  - Implement clean logout flow (discard token, clear query cache, redirect).
- **Exit Criteria:**
  - Successful login transitions to dashboard with verified role context (`ADMIN`, `ANALYST`, `INVESTIGATOR`).
  - Access token is strictly held in memory and never written to `localStorage` or `sessionStorage`.
  - Expired tokens or 401 responses trigger clean re-authentication.
- **Status:** `NEXT / BLOCKED UNTIL F1 ACCEPTANCE`

---

## Phase F3 — Analytics, Transaction Exploration & Risk

- **Objective:** Deliver the operational dashboard, transaction exploration table, and risk explainability workflows.
- **Key Tasks:**
  - Implement Analytics Overview page with Apache ECharts visualizations (volume trends, category spending, top merchants).
  - Build Transaction Exploration table with server-side pagination, sorting, and multi-field filtering.
  - Implement Transaction Detail view preserving exact decimal precision (`MoneyStr`) and UTC timestamps.
  - Implement Risk Result panel displaying hybrid score, risk tier badge, ML vs Rule score breakdown, and structured factor list.
  - Implement on-demand risk analysis action (`POST /transactions/{id}/risk/analyze`) with model version awareness.
- **Exit Criteria:**
  - Analytics and transaction queries execute cleanly against backend endpoints.
  - Decimal values render with zero floating-point corruption.
  - Risk factors clearly distinguish between facts, heuristics, and model-derived signals.
- **Status:** `NOT STARTED`

---

## Phase F4 — Dataset Import & Processing Visibility

- **Objective:** Enable authorized analysts and administrators to upload CSV datasets, monitor progress, and review data quality results.
- **Key Tasks:**
  - Build multipart CSV file uploader with bounded client preflight (50 MB limit, `.csv` validation).
  - Implement import submission (`POST /api/v1/datasets/imports`) with duplicate detection handling (`200 OK` vs `201 Created`).
  - Build Import History & Detail view showing row counts (`INSERTED`, `MATCHED_EXISTING`, `QUARANTINED`, `REJECTED`).
  - Implement recovery workflow (`POST /api/v1/datasets/imports/{id}/recover`) for interrupted imports.
- **Exit Criteria:**
  - 50 MB streaming uploads and recovery operate cleanly without browser crashes.
  - Ingestion outcomes and validation errors render accurately with row-level provenance.
- **Status:** `NOT STARTED`

---

## Phase F5 — Investigation Queue, Workspace & Lifecycle

- **Objective:** Provide a manual-first triage queue, case creation workflow, and core investigation workspace.
- **Key Tasks:**
  - Implement Investigation Queue table with deterministic pagination, status filters (`OPEN`, `UNDER_REVIEW`, `RESOLVED`), and priority filters.
  - Implement Manual Investigation Creation modal binding a valid primary transaction.
  - Build Investigation Workspace layout assembling primary transaction facts, latest risk analysis, and case timeline.
  - Implement Assignment actions (self-assign for Investigators, global assign for Admins) and state transition to `UNDER_REVIEW`.
- **Exit Criteria:**
  - Investigation creation and assignment strictly conform to backend RBAC and lifecycle validation.
  - Pessimistic locking / conflict errors (`409`, `422`) are handled gracefully with clear user guidance.
- **Status:** `NOT STARTED`

---

## Phase F6 — Evidence & AI-Assisted Investigation

- **Objective:** Complete the investigative workflow with 1-hop transaction linking, immutable evidence attachment, grounded AI briefing summaries, and human resolution.
- **Key Tasks:**
  - Implement Related Transaction linking modal enforcing the 4-way 1-hop shared-party predicate.
  - Build Evidence Attachment form supporting all 6 domain evidence types and user notes (up to 64 KB JSONB payload).
  - Build Evidence List displaying immutable snapshots ordered deterministically (`created_at ASC, id ASC`).
  - Implement AI Summary request and briefing display, with dynamic staleness indicator (`is_stale: true`) and grounded entity citations.
  - Implement Case Resolution modal requiring non-empty notes and recording one of 4 standardized outcomes.
- **Exit Criteria:**
  - Resolved cases immediately transition to permanently immutable read-only presentation.
  - AI summaries strictly present structured facts, signals, and limitations without making fraud verdicts.
- **Status:** `NOT STARTED`

---

## Phase F7 — Integration, Accessibility, Security & Hardening

- **Objective:** End-to-end integration testing, accessibility compliance, browser security hardening, and performance verification.
- **Key Tasks:**
  - Automated accessibility testing (axe-core) ensuring WCAG 2.1 AA compliance across all primary screens.
  - Full keyboard navigation and screen-reader audit for investigation workspaces.
  - End-to-end user journey tests with Playwright (login -> ingest -> triage -> investigate -> resolve).
  - Browser security audit: Content Security Policy (CSP), subresource integrity, sanitization of user notes and CSV exports.
  - Production build optimization: code splitting, route lazy-loading, bundle budget compliance (< 300 KB initial gzipped JS).
- **Exit Criteria:**
  - Zero critical or high accessibility violations.
  - All E2E smoke journeys pass reliably against staging backend.
  - Production bundle complies with size budgets.
- **Status:** `NOT STARTED`

---

## Phase F8 — Deployment, Acceptance & Frontend Release

- **Objective:** Finalize production deployment configuration, conduct formal user acceptance review, and release Frontend v1.0.0.
- **Key Tasks:**
  - Production static asset web server configuration (Nginx / Cloudflare Pages / Caddy) with security headers and history fallback routing.
  - Synchronize documentation across all master and frontend specifications.
  - Conduct formal end-to-end acceptance review with stakeholders.
  - Tag git release `frontend-v1.0.0` with accompanying release notes.
- **Exit Criteria:**
  - Frontend successfully deployed and verified against production backend.
  - Formal acceptance criteria from `FRONTEND_PRD.md` 100% satisfied.
  - Working tree clean with release tag published.
- **Status:** `NOT STARTED`

---

# 30. Final Master Integration Principle

FinSignal delivers financial transaction intelligence through a strict hierarchy of authority:

```text
Backend PostgreSQL & Python Services (Authoritative Truth)
                         ↓
       FastAPI REST Endpoints (/api/v1)
                         ↓
  Verified OpenAPI Contract (/openapi.json)
                         ↓
      Typed React Application (Presentation & Orchestration)
                         ↓
     Human Investigator Decision (Final Operational Authority)
```

The frontend never replaces, duplicates, or bypasses backend domain logic, financial precision, risk algorithms, or authorization. It exists to make the system's analytical power accessible, transparent, and actionable for human investigators.
