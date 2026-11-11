# FinSignal — Architecture & Engineering Decisions

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Architecture & Engineering Decisions  
**Scope:** Backend + ML  
**Status:** Planning / Implementation-Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-10-25

---

## 1. Purpose

This document records the major architectural, technical, data, ML, security, and product-engineering decisions for FinSignal.

The purpose is to prevent important decisions from being repeatedly reconsidered during implementation and to provide a historical explanation for why the system is structured as it is.

This document records **decisions**, not implementation instructions. Detailed implementation requirements belong in:

- `TRD.md`
- `ARCHITECTURE.md`
- `DATABASE_DESIGN.md`
- `ML_DESIGN.md`
- `API_GUIDELINES.md`
- `SECURITY.md`
- `CODING_STANDARDS.md`
- `TESTING_STRATEGY.md`
- `PROJECT_ROADMAP.md`

---

# 2. Decision Statuses

Each decision uses one of the following statuses:

| Status | Meaning |
|---|---|
| ACCEPTED | Decision is active and should guide implementation |
| ACCEPTED — DEFERRED | Decision is accepted for future consideration but not current implementation |
| SUPERSEDED | Replaced by a newer decision |
| OPEN | Requires a future decision |
| REJECTED | Explicitly considered and rejected |

---

# 3. Decision Principles

FinSignal follows these principles:

1. Prefer correctness over feature count.
2. Prefer simple architecture over premature infrastructure.
3. Preserve raw financial facts.
4. Keep derived intelligence separate from source data.
5. Prevent temporal leakage by design.
6. Treat ML as decision support.
7. Keep human investigators responsible for final decisions.
8. Keep AI grounded in structured evidence.
9. Prefer reproducibility over opaque experimentation.
10. Document meaningful trade-offs.
11. Avoid infrastructure whose complexity is not justified by current scale.
12. Keep future expansion possible without building future infrastructure prematurely.

---

# ADR-001 — Use Python for Backend and ML

**Status:** ACCEPTED

## Context

FinSignal combines API development, data processing, financial analytics, feature engineering, machine learning, and AI integration.

Python provides a strong ecosystem for:

- FastAPI;
- Pandas;
- NumPy;
- scikit-learn;
- data analysis;
- ML experimentation;
- LLM integration.

## Decision

Use **Python** as the primary backend and ML language.

## Consequences

### Positive

- One language covers API, analytics, and ML.
- Minimal serialization overhead between backend and ML layers.
- Strong data-science ecosystem.
- Easier transition from experimentation to production code.

### Negative

- Requires stronger discipline around typing and architecture.
- Some high-throughput workloads may eventually require optimization or service extraction.

---

# ADR-002 — Use FastAPI

**Status:** ACCEPTED

## Context

The platform requires a REST API for authentication, transactions, analytics, risk analysis, investigations, evidence, and AI summaries.

## Decision

Use **FastAPI**.

## Rationale

- Python-native;
- strong type-hint integration;
- Pydantic validation;
- automatic OpenAPI documentation;
- asynchronous support;
- suitable for modular API development.

## Consequences

The backend should use explicit request/response schemas rather than exposing ORM entities directly.

---

# ADR-003 — Use PostgreSQL

**Status:** ACCEPTED

## Context

FinSignal needs relational integrity across:

- accounts;
- transactions;
- merchants;
- devices;
- investigations;
- evidence;
- model outputs;
- audit records.

It also requires temporal queries and analytical aggregations.

## Decision

Use **PostgreSQL** as the primary database.

## Rationale

- strong relational integrity;
- excellent indexing;
- timestamp support;
- mature transaction semantics;
- JSON/JSONB support where useful;
- good analytical capabilities;
- portfolio diversification from MySQL-based projects.

## Consequences

PostgreSQL becomes the authoritative persistence layer for the initial release.

---

# ADR-004 — Use a Modular Monolith

**Status:** ACCEPTED

## Context

The system contains many logical domains, but the initial dataset is approximately 250,000 transactions and the expected application scale does not justify distributed services.

## Decision

Implement FinSignal as a **modular monolith**.

## Logical Modules

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

## Rationale

A modular monolith provides:

- clear domain boundaries;
- simple deployment;
- simple debugging;
- shared transactions;
- low operational overhead;
- an eventual path to service extraction if required.

## Consequences

Module boundaries must be enforced through architecture and code review.

---

# ADR-005 — Defer Microservices

**Status:** ACCEPTED — DEFERRED

## Context

Microservices would introduce:

- network boundaries;
- service discovery;
- distributed transactions;
- deployment complexity;
- observability requirements;
- operational overhead.

These costs are not justified for the initial system.

## Decision

Do not use microservices for v1.

## Future Trigger

Service extraction may be reconsidered if a component develops:

- independent scaling requirements;
- independent deployment requirements;
- substantially different availability requirements;
- clear organizational ownership;
- infrastructure justification.

---

# ADR-006 — Use JWT Authentication

**Status:** ACCEPTED

## Context

The application requires authenticated API access for analysts, investigators, and administrators.

## Decision

Use JWT-based authentication.

## Requirements

- secure password hashing;
- signed access tokens;
- expiration;
- validation;
- role claims or server-side role resolution;
- protected endpoints.

Logout/token invalidation behavior is implemented following the stateless Option A design: access tokens have short lifetimes (default 30m) and the client discards the token upon logout. No server-side token revocation table or blacklist is maintained. Calling `POST /api/v1/auth/logout` requires authentication and returns a standard confirmation without revoking the token server-side.

---

# ADR-007 — Use RBAC

**Status:** ACCEPTED

## Context

Different users require different privileges.

## Roles

```text
ADMIN
ANALYST
INVESTIGATOR
```

## Decision

Use role-based access control combined with object-level authorization.

## Rationale

Role checks alone are insufficient because users may also need access restrictions at the resource level.

---

# ADR-008 — Keep Raw Transactions Immutable

**Status:** ACCEPTED

## Context

Financial transactions are source facts. Changing them after analysis would undermine:

- auditability;
- reproducibility;
- investigations;
- ML lineage.

## Decision

Treat persisted raw transaction facts as immutable after successful ingestion.

Corrections should occur through controlled data-versioning or correction workflows rather than silently mutating historical facts.

## Consequences

Derived analytics and risk analyses can change without changing the underlying transaction record.

---

# ADR-009 — Separate Raw Facts from Derived Intelligence

**Status:** ACCEPTED

## Context

Risk scores, features, model outputs, and investigation decisions are derived from transactions.

## Decision

Do not store derived risk intelligence directly inside the raw transaction entity.

Use separate structures such as:

```text
transactions
risk_analyses
risk_factors
investigations
investigation_evidence
ai_summaries
```

## Rationale

This preserves:

- data lineage;
- model-version history;
- re-analysis capability;
- separation of concerns.

---

# ADR-010 — Do Not Store a Permanent Account Age Field

**Status:** ACCEPTED

## Context

Account age changes continuously.

Persisting a value such as `account_age_days` creates stale derived data.

## Decision

Store:

```text
created_at
```

and derive account age when required.

## Consequences

Historical account age must be calculated relative to the relevant evaluation timestamp.

---

# ADR-011 — Represent Transfers with a Counterparty Reference

**Status:** ACCEPTED

## Context

Account-to-account transfers are important for realistic financial behavior and future graph analysis.

Creating mirrored transaction records risks:

- double counting;
- inconsistent updates;
- ambiguous ownership.

## Decision

A transaction contains:

```text
account_id
counterparty_account_id
```

where applicable.

A transfer is represented from the perspective of the primary account record.

## Constraint

```text
counterparty_account_id != account_id
```

when a counterparty exists.

---

# ADR-012 — Do Not Automatically Create Mirrored Transfer Rows

**Status:** ACCEPTED

## Context

A transfer between Account A and Account B could be represented by two rows.

However, automatic mirroring can cause:

- duplicate analytical counts;
- difficult lifecycle management;
- ambiguity about whether two rows represent one or two events.

## Decision

Do not automatically create mirrored transaction rows for v1.

## Future

A graph-oriented event representation may be introduced later if justified.

---

# ADR-013 — Use Synthetic Data for Development

**Status:** ACCEPTED

## Context

The project does not require real customer financial data and using real financial data would create unnecessary privacy and security concerns.

## Decision

Use synthetic, behavior-driven financial data.

## Requirements

Synthetic data must contain:

- realistic account profiles;
- recurring behavior;
- legitimate unusual activity;
- fraud/anomaly scenarios;
- ground truth;
- temporal relationships.

The data should not be random noise disguised as financial activity.

---

# ADR-014 — Use Ground Truth Only for Evaluation

**Status:** ACCEPTED

## Context

Synthetic fraud labels are required to evaluate detection quality.

Using those labels during inference would cause target leakage.

## Decision

Ground truth may be used for:

- evaluation;
- metric calculation;
- scenario analysis;
- test validation.

Ground truth must not be used as an inference feature.

Fields include:

```text
is_fraud
fraud_scenario
scenario_instance_id
```

---

# ADR-015 — Enforce Historical Feature Availability

**Status:** ACCEPTED

## Context

Financial anomaly detection is fundamentally temporal.

A feature calculated using future activity would make offline evaluation unrealistically strong.

## Decision

For a transaction evaluated at time `T`, features may use only information available at or before `T`, according to the feature's explicit window semantics.

## Consequences

All feature engineering must be testable against temporal leakage.

---

# ADR-016 — Use Chronological Model Evaluation

**Status:** ACCEPTED

## Context

Random train/test splitting can allow future behavior to influence training.

## Decision

Use chronological data splits.

Initial example:

```text
January–June → Train
July–August → Validation
September → Test
```

Exact dates may change with dataset generation.

## Consequences

Evaluation better represents future deployment behavior.

---

# ADR-017 — Start with Isolation Forest

**Status:** ACCEPTED

## Context

FinSignal needs an ML baseline capable of identifying anomalous behavior without requiring a large labeled production dataset.

## Decision

Use **Isolation Forest** as the initial unsupervised ML baseline.

## Rationale

- available in scikit-learn;
- interpretable at the architectural level;
- appropriate for anomaly detection;
- relatively simple to train;
- works without supervised fraud labels.

## Consequences

Isolation Forest is a baseline, not proof that the system can detect all forms of fraud.

---

# ADR-018 — Use Hybrid Risk Scoring

**Status:** ACCEPTED

## Context

ML anomaly scores alone do not provide enough contextual explanation.

Deterministic financial signals such as new device, new location, velocity, and behavioral deviation are valuable evidence.

## Decision

Combine:

```text
ML anomaly signal
+
deterministic behavioral signals
=
hybrid risk assessment
```

## Consequences

The system can provide both:

- a numerical anomaly signal;
- structured reasons for investigation.

---

# ADR-019 — Do Not Call Risk Score “Fraud Probability”

**Status:** ACCEPTED

## Context

A raw anomaly score is not automatically a calibrated probability.

Calling it a probability could mislead investigators.

## Decision

Use terminology such as:

- anomaly score;
- risk score;
- risk level.

Only use fraud probability if a properly calibrated probabilistic model is later implemented and validated.

---

# ADR-020 — Use Risk Factors as Structured Evidence

**Status:** ACCEPTED

## Context

Investigators need to understand why activity was flagged.

## Decision

Store structured risk factors separately from the aggregate risk score.

Examples:

```text
NEW_DEVICE
NEW_LOCATION
UNUSUAL_TIME
HIGH_VELOCITY
LARGE_AMOUNT_DEVIATION
BEHAVIORAL_SHIFT
```

Each factor must correspond to actual evidence.

---

# ADR-021 — Use Human-in-the-Loop Investigation

**Status:** ACCEPTED

## Context

Automated anomaly detection can produce false positives.

## Decision

The system recommends and explains; a human investigator makes the final case resolution.

Allowed resolutions:

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

## Consequences

The AI/ML system must never silently convert a risk score into a final fraud decision.

---

# ADR-022 — Keep AI Downstream of Evidence

**Status:** ACCEPTED

## Context

LLMs can generate plausible but unsupported statements.

## Decision

The AI assistant receives a controlled, structured investigation context assembled by the backend.

```text
Transactions
Risk Analyses
Risk Factors
Behavioral Evidence
Investigation Metadata
        ↓
Evidence Assembly
        ↓
LLM
```

The LLM does not independently query the entire database.

---

# ADR-023 — Introduce an LLM Provider Abstraction

**Status:** ACCEPTED

## Context

The exact LLM provider may change due to:

- cost;
- availability;
- performance;
- privacy requirements;
- model quality.

## Decision

Implement a provider interface rather than coupling business logic directly to one provider SDK.

Conceptually:

```text
AIService
   ↓
LLMProvider
   ├── Provider A
   └── Provider B
```

## Consequences

Business logic remains independent of provider-specific APIs.

---

# ADR-024 — AI Must Not Decide Investigation Resolution

**Status:** ACCEPTED

## Context

The system is intended to assist investigators rather than replace them.

## Decision

AI output may summarize:

- transaction behavior;
- risk factors;
- relevant evidence;
- contextual observations.

AI may not directly set:

```text
CONFIRMED_FRAUD
LEGITIMATE
SUSPICIOUS
INCONCLUSIVE
```

A human investigator remains authoritative.

---

# ADR-025 — Protect Against Prompt Injection in Transaction Data

**Status:** ACCEPTED

## Context

Merchant names, descriptions, imported text, and other financial fields are untrusted input.

An attacker could include instruction-like text.

## Decision

Treat all transaction-derived text as data, not instructions.

The AI context builder must distinguish:

```text
system instructions
structured evidence
untrusted transaction text
```

## Required Testing

Prompt-injection regression tests must be included.

---

# ADR-026 — PostgreSQL is the Source of Truth

**Status:** ACCEPTED

## Context

Derived features and ML artifacts can be regenerated.

The database should remain authoritative for application records.

## Decision

PostgreSQL is authoritative for:

- users;
- accounts;
- transactions;
- investigations;
- evidence;
- risk-analysis metadata;
- audit records;
- dataset metadata.

ML artifacts are versioned separately but referenced from application records.

---

# ADR-027 — Store Model Version with Risk Analysis

**Status:** ACCEPTED

## Context

A risk score is meaningful only when the model and feature configuration that produced it are known.

## Decision

Every persisted risk analysis must reference a model version.

## Consequences

Investigators and developers can determine:

```text
Which model?
Which feature version?
Which score?
When generated?
```

This supports reproducibility and future re-analysis.

---

# ADR-028 — Version Dataset Imports

**Status:** ACCEPTED

## Context

Model evaluation and investigation results depend on the underlying dataset.

## Decision

Dataset imports receive version/identity metadata.

Track:

- dataset version;
- import identifier;
- source metadata;
- import time;
- row counts;
- error counts;
- status.

## Consequences

Data lineage becomes traceable.

---

# ADR-029 — Use Deterministic Synthetic Seeds

**Status:** ACCEPTED

## Context

ML and data bugs must be reproducible.

## Decision

Synthetic dataset generation must accept an explicit seed.

Example:

```text
20261004
```

The seed becomes part of dataset metadata where relevant.

---

# ADR-030 — Include Legitimate Unusual Activity

**Status:** ACCEPTED

## Context

A naive dataset where all unusual activity is fraudulent would encourage a model to learn:

```text
large/unusual = fraud
```

That does not represent realistic financial behavior.

## Decision

Synthetic data must contain legitimate unusual events such as:

- salary credits;
- annual insurance;
- rent;
- flights/hotels;
- hospital expenses;
- electronics purchases;
- legitimate business expenses.

## Consequences

False-positive evaluation becomes meaningful.

---

# ADR-031 — Use Multiple Fraud Scenarios

**Status:** ACCEPTED

## Context

A single fraud pattern would create a narrow ML benchmark.

## Decision

Use multiple fraud/anomaly scenarios:

```text
F001 Large Amount
F002 New Device
F003 New Location
F004 Unusual Time
F005 High Velocity
F006 Account Takeover
F007 Behavioral Shift
```

## Consequences

The model can be evaluated by scenario rather than only aggregate metrics.

---

# ADR-032 — Include Multi-Transaction Fraud Scenarios

**Status:** ACCEPTED

## Context

Some suspicious activity is behavioral rather than isolated.

## Decision

Some fraud scenarios must span multiple transactions.

Examples:

- account takeover;
- velocity attacks;
- behavioral spending shifts.

## Consequences

Evaluation includes both transaction-level and scenario-instance-level detection.

---

# ADR-033 — Defer Real-Time Streaming

**Status:** ACCEPTED — DEFERRED

## Context

Kafka or another streaming platform would add significant infrastructure complexity.

The initial product can operate on imported datasets and batch analysis.

## Decision

Use batch-oriented processing for v1.

## Future Trigger

Streaming may be reconsidered when real-time detection becomes a genuine product requirement.

---

# ADR-034 — Defer Kafka

**Status:** ACCEPTED — DEFERRED

Kafka is not required for the initial dataset scale or user workflow.

Do not introduce Kafka merely to demonstrate technology breadth.

---

# ADR-035 — Defer Celery/Redis

**Status:** ACCEPTED — DEFERRED

## Context

Background job infrastructure may become useful for long-running ingestion or ML jobs.

## Decision

Initially keep processing simple.

Introduce Celery/Redis only when:

- request time becomes unacceptable;
- workload becomes asynchronous;
- reliability requirements justify job queues.

---

# ADR-036 — Defer MLflow

**Status:** ACCEPTED — DEFERRED

## Context

MLflow is useful for mature experiment tracking and model management.

For the initial project, explicit model-version metadata and reproducible artifacts are sufficient.

## Decision

Do not introduce MLflow in v1 unless implementation experience demonstrates a clear need.

---

# ADR-037 — Defer Graph ML

**Status:** ACCEPTED — DEFERRED

## Context

Account-to-account transfers make graph analysis interesting.

However, graph ML introduces substantial additional complexity.

## Decision

Store transfer relationships in a graph-compatible relational form, but defer graph ML.

## Future Possibilities

- account relationship graphs;
- community detection;
- mule-account detection;
- transaction-network anomalies.

---

# ADR-038 — Defer RAG

**Status:** ACCEPTED — DEFERRED

## Context

The initial AI assistant can operate from structured investigation evidence.

External document retrieval is not required to explain transaction behavior.

## Decision

Do not introduce RAG or vector search in v1.

---

# ADR-039 — Use Batch ML Inference Initially

**Status:** ACCEPTED

## Context

The initial workflow is dataset-oriented and does not require millisecond-level transaction scoring.

## Decision

Use batch inference for v1.

## Consequences

The system remains simpler and easier to test.

Real-time scoring can be added later without changing the conceptual risk architecture.

---

# ADR-040 — Keep Feature Computation Separate from Model Code

**Status:** ACCEPTED

## Context

Feature logic represents domain knowledge and must remain independently testable.

## Decision

Separate:

```text
Feature Engineering
        ↓
Feature Dataset
        ↓
Model
```

The model should not contain hidden business logic for calculating financial features.

---

# ADR-041 — Use Temporal Evaluation Instead of Random Splitting

**Status:** ACCEPTED

This decision reinforces ADR-016.

Random splitting is inappropriate as the primary evaluation strategy because financial behavior changes over time and future information must not influence historical model training.

---

# ADR-042 — Use Scenario-Level and Account-Level Metrics

**Status:** ACCEPTED

## Context

Transaction-level metrics alone can hide meaningful failures.

## Decision

Evaluate at:

- transaction level;
- account level;
- fraud scenario level;
- scenario-instance level.

## Consequences

The evaluation better reflects investigation-oriented use.

---

# ADR-043 — Prioritize PR-AUC for Imbalanced Detection

**Status:** ACCEPTED

## Context

Fraud is intentionally a minority class.

Accuracy can therefore be misleading.

## Decision

Use PR-AUC alongside:

- precision;
- recall;
- F1;
- false-positive rate;
- false-negative rate;
- alert volume.

No single metric is sufficient.

---

# ADR-044 — Do Not Optimize Only for Recall

**Status:** ACCEPTED

## Context

A system that flags almost everything may achieve high recall but overwhelm investigators.

## Decision

Evaluate the trade-off between:

```text
Detection
vs
False positives
vs
Alert volume
```

Thresholds must be chosen with investigation capacity in mind.

---

# ADR-045 — Preserve Evidence Lineage

**Status:** ACCEPTED

## Context

An investigator must be able to understand where an explanation came from.

## Decision

Evidence should reference its underlying source data and preserve relevant timestamps/identifiers.

AI summaries should also retain enough metadata to identify the evidence context used to generate them.

---

# ADR-046 — Use Evidence Hashing for AI Context

**Status:** ACCEPTED

## Context

An AI summary should be traceable to the evidence used when it was generated.

## Decision

Store an evidence hash or equivalent deterministic identifier with AI summaries.

## Purpose

This supports:

- reproducibility;
- auditability;
- detection of changed evidence;
- debugging.

---

# ADR-047 — Do Not Expose ORM Entities Directly Through APIs

**Status:** ACCEPTED

## Context

Direct ORM serialization can expose:

- internal fields;
- sensitive fields;
- database implementation details;
- unintended relationships.

## Decision

Use dedicated API schemas/DTOs.

```text
Database Model
      ↓
Service
      ↓
API Schema
      ↓
Response
```

---

# ADR-048 — Use Explicit API Versioning

**Status:** ACCEPTED

## Decision

Initial API namespace:

```text
/api/v1
```

Future breaking API changes should use a new version rather than silently changing existing contracts.

---

# ADR-049 — Use Decimal Semantics for Money

**Status:** ACCEPTED

## Context

Binary floating-point arithmetic can introduce monetary precision errors.

## Decision

Use decimal-safe monetary representation in application and persistence layers.

Tests must verify exact financial calculations.

---

# ADR-050 — Use UTC for Stored Timestamps

**Status:** ACCEPTED

## Context

Financial activity can involve multiple locations and time zones.

## Decision

Persist timestamps in UTC and convert to presentation/local context when required.

Timezone-aware datetime handling is required.

---

# ADR-051 — Preserve Transaction Ordering Explicitly

**Status:** ACCEPTED

## Context

Multiple transactions may share the same timestamp.

Ordering only by timestamp is therefore insufficient for deterministic replay and feature calculation.

## Decision

When chronological ordering is required, use a deterministic secondary key such as transaction ID.

Conceptually:

```text
ORDER BY occurred_at ASC, id ASC
```

This ensures reproducible ordering.

---

# ADR-052 — Do Not Treat Timestamp Alone as a Unique Event Boundary

**Status:** ACCEPTED

## Context

Two or more events can have the same timestamp.

A historical reconstruction API that accepts only:

```text
as_of = timestamp
```

cannot always identify a unique event boundary.

## Decision

When exact event-boundary reconstruction is required, use a composite boundary such as:

```text
occurred_at + event/transaction ID
```

or an equivalent deterministic ordering mechanism.

This decision applies to historical feature reconstruction and future event-replay functionality.

---

# ADR-053 — Keep Backend Authoritative

**Status:** ACCEPTED

## Context

Financial calculations and ML outputs must not diverge between frontend and backend.

## Decision

The backend is authoritative for:

- financial analytics;
- transaction interpretation;
- risk scores;
- risk factors;
- investigation state;
- AI summaries.

A future frontend must consume these results rather than independently recomputing domain truth.

---

# ADR-054 — Synthetic Data Only for Initial Development

**Status:** ACCEPTED

No real customer financial information is required for the initial implementation.

This reduces:

- privacy risk;
- compliance burden;
- accidental data exposure;
- development complexity.

---

# ADR-055 — Defer Advanced Infrastructure Until Justified

**Status:** ACCEPTED

FinSignal will not adopt infrastructure merely because it is common in production ML systems.

Each additional technology must answer a concrete requirement.

Examples:

```text
Kafka → requires real-time event streaming
Redis → requires meaningful caching/job infrastructure
Celery → requires asynchronous background workloads
MLflow → requires mature experiment/model tracking
RAG → requires external knowledge retrieval
Graph ML → requires network-level intelligence
```

If the requirement does not exist, the technology remains deferred.

---

# ADR-056 — Investigation Trigger Policy as Server-Side Application Configuration

**Status:** ACCEPTED

## Context

Risk scoring evaluates transaction anomaly signals and produces deterministic `risk_analyses`. However, the decision to automatically create an investigation for high-risk activity is a workflow automation policy that must be configurable and decoupled from core inference computation.

## Decision

Implement the investigation auto-trigger policy as server-side application configuration (typed environment settings) rather than database-stored dynamic rule engines or runtime admin APIs.

Configuration controls:
- `INVESTIGATION_AUTO_TRIGGER_ENABLED`: Global enable/disable flag.
- `INVESTIGATION_TRIGGER_MIN_LEVEL`: Minimum risk level for auto-triggering (e.g., HIGH or CRITICAL).
- `INVESTIGATION_TRIGGER_HIGH_SCORE_THRESHOLD`: Numeric score threshold above which HIGH transactions trigger an investigation.

This keeps the modular monolith simple and testable while allowing operational adjustment per environment.

---

# ADR-057 — Temporal Feature Boundary Canonical Semantics

**Status:** ACCEPTED

## Context

Historical baseline calculations must never leak future data or allow the transaction being evaluated to contaminate its own historical summary.

## Decision

For a transaction `T` occurring at timestamp `t`, historical context is strictly defined as:
```text
occurred_at < t OR (occurred_at == t AND id < T.id)
```
Transaction `T` is strictly excluded from its own historical baseline context.

Static precomputed generation fields (such as `account_age_days` in CSV files) must never be loaded as features; point-in-time account age must always be dynamically derived from `transaction.occurred_at - account.created_at`.

---

# ADR-058 — Transaction Ingestion Idempotency & Deduplication

**Status:** SUPERSEDED by ADR-064

## Context

Concurrent or retried ingestion requests could introduce duplicate transaction records. However, `dataset_import_id` is nullable to allow standalone or simulated transaction creation outside batch imports.

## Decision

Adopt a dual-layer deduplication design:
1. Enforce a partial unique index on batch imports:
   ```sql
   CREATE UNIQUE INDEX uq_transactions_import_ext_id
       ON transactions (dataset_import_id, external_transaction_id)
       WHERE dataset_import_id IS NOT NULL;
   ```
2. For standalone/manual transactions where `dataset_import_id IS NULL`, enforce application-level idempotency within the transaction domain service using account, external_id, and occurred_at checks inside an atomic transaction.

> [!NOTE]
> **Superseded by ADR-064:** Following the Phase 2 implementation authorization and schema migration `0002_core_operational_schema`, ADR-058 has been formally superseded by ADR-064. Transaction uniqueness is now enforced at the database layer via canonical composite natural key `uq_transactions_canonical_id (source_namespace, account_id, external_transaction_id)` with row-level observation provenance tracked in `transaction_import_records`, replacing the earlier import-scoped partial index.

---

# ADR-059 — Model Artifact Integrity Verification via SHA-256

**Status:** ACCEPTED

## Context

Loading serialized ML models from disk introduces security and operational risks if artifacts are tampered with, corrupted, or replaced.

## Decision

Store a cryptographic SHA-256 hash in `model_versions.artifact_hash` upon training. Verify this digest prior to loading in the inference engine. Any hash mismatch or missing hash must immediately raise a controlled `ModelIntegrityError` and abort loading.

### Proposed Addendum — Artifact Integrity Trust Boundary (Pending Project-Owner Approval)

- **Defense-in-Depth Scope:** SHA-256 digest validation serves as an integrity and corruption check verifying that serialized bytes on disk have not suffered partial writes, storage bit rot, or unauthorized local filesystem modification prior to `joblib.load()`.
- **Trust Boundary & Threat Model:** SHA-256 digest validation does **not** authenticate model artifacts against an adversary who has achieved compromise of both PostgreSQL (updating `model_versions.artifact_hash`) and the filesystem (replacing `model.joblib`). FinSignal does not implement asymmetric PKI, digital signatures, or external hardware security modules.
- **Deserialization Risk:** Deserializing arbitrary Python objects via `joblib.load()` executes untrusted bytecode if files are malicious. Model loading must strictly remain confined within the trusted application server boundary, and path traversal defenses must enforce filesystem containment.

---

# ADR-060 — Polymorphic Evidence Source Validation at Application Layer

**Status:** ACCEPTED

## Context

Investigation evidence can reference diverse source entities (transactions, accounts, risk analyses, devices). Enforcing database foreign keys for each possible type would require complex schema patterns (EAV or multiple nullable foreign keys).

## Decision

Use an unconstrained UUID column `source_id` paired with `source_type` on `investigation_evidence` and enforce referential integrity, entity existence, context boundary, and investigator authorization at the application domain layer.

---

# ADR-061 — Defer Docker Local Containerization to Phase 12

**Status:** ACCEPTED

## Context

Phase 0 local development runs directly against native Windows PostgreSQL and uses ephemeral PostgreSQL containers in GitHub Actions CI. Mandating Docker Desktop locally for Phase 0 adds virtualization overhead and unnecessary setup prerequisites for developers without architectural benefit.

## Decision

Defer Docker local containerization to Phase 12 (Deployment & Packaging). Develop Phase 0 through Phase 11 using native Python 3.12 (managed via `uv`) and native PostgreSQL installations.

---

# ADR-062 — Structured URL Construction for Database Connections

**Status:** ACCEPTED

## Context

Database credentials (e.g. passwords containing reserved URI characters such as `@`, `:`, `/`, `?`, `#`, `%`) break naive string-interpolated connection URLs, causing driver URI parsing failures.

## Decision

Use SQLAlchemy's structured `URL.create()` API for generating runtime (`postgresql+asyncpg`) and migration (`postgresql+psycopg`) connection URLs. This guarantees proper percent-encoding of credential values while preserving exact credentials during downstream database engine connection.

---

# ADR-063 — Progressive Domain Module and Schema Realization Without Premature Scaffolding

**Status:** ACCEPTED

## Context

Phase 1 (Backend Architecture & Core Structure) establishes the modular-monolith foundation, including application configuration, structured logging, request ID tracking, error handling hierarchies, and baseline system probe endpoints. The architecture specifies sixteen logical domain and feature modules (`auth`, `users`, `accounts`, `merchants`, `devices`, `locations`, `transactions`, `ingestion`, `analytics`, `features`, `risk`, `investigations`, `evidence`, `ai`, `dataset`, and `common`).

A common architectural question during early foundational phases is whether to generate empty placeholder packages (stub directories and inert `__init__.py` files) and dummy schema migrations for all future modules upfront. In a system following incremental phase-gated delivery (Phase 2 for Database & Domain Models, Phase 3 for Authentication & RBAC, Phase 4 for Transactions, etc.), premature scaffolding creates empty namespace bloat, complicates static type checking and import linting, and risks committing placeholder migrations before domain entities are fully specified.

## Decision

Retain domain module directory creation and database schema migrations strictly for their designated implementation phases:

1. Do not create empty filesystem scaffolding or placeholder directories for domain modules ahead of their scheduled roadmap phase.
2. Do not author speculative database schema migrations ahead of Phase 2 domain model definitions.
3. Realize each domain module package (`auth/`, `accounts/`, `transactions/`, etc.) and its corresponding database migrations only when active implementation of that domain begins in its scheduled phase.

## Rationale

- **Clean Namespace & Linting:** Avoids empty packages that pollute import auto-completion, generate empty-file linter warnings, or require artificial type-checker exclusions.
- **Schema Integrity:** Ensures database migrations strictly reflect validated, tested SQLAlchemy domain models created in Phase 2 rather than speculative stub tables.
- **Phase Alignment:** Preserves the incremental verification guarantees of the project roadmap, where every phase transitions from a clean baseline to verified reality.
- **Simplicity:** Aligns with core architectural principles (ADR-004, ADR-055, and PRD Principle 8) emphasizing simplicity over premature structure.

## Consequences

- Domain modules are introduced incrementally as their corresponding phases commence.
- Test suites, type checking, and linters evaluate only active, fully realized code.
- Developers must not scaffold empty module directories or migrations in advance of authorized work.

## Scope

- This decision governs the phased realization discipline for remaining backend and ML modules.
- This decision **does not** alter the logical module boundaries defined in ADR-004 or the module allocation described in the roadmap.
- Formally accepted following Phase 2 Option C implementation authorization.

---

# ADR-064 — Canonical Transaction Identity & Import-Level Row Provenance

**Status:** ACCEPTED (Supersedes ADR-058)

## Context

During the pre-implementation architectural review of Phase 2, critical limitations were identified in the transaction deduplication and identity model specified in ADR-058:

1. **Import-Scoped Duplicate Failure:** ADR-058 specified a partial unique index `(dataset_import_id, external_transaction_id) WHERE dataset_import_id IS NOT NULL`. Because `dataset_import_id` is unique per import job, ingesting the same CSV twice (or ingesting multiple dataset versions containing overlapping historical transactions) resulted in duplicate canonical transaction rows with different primary keys, corrupting financial metrics and analytics.
2. **Account Scope Requirement:** Synthetic transaction identifiers (`TXN_[0-9]{8}`) and external bank transaction references are unique per customer account, not globally unique across all accounts or multi-source environments.
3. **Loss of Import Provenance:** Merging identical transactions into a single canonical row without an intermediary ledger destroys import lineage, preventing audits from knowing which CSV files, upload jobs, or row ordinals referenced a transaction.
4. **Ambiguity in Idempotency Boundaries:** The system previously conflated HTTP transport idempotency (`Idempotency-Key`), byte-identical file deduplication (`file_hash`), canonical transaction natural identity, and import-row lineage.
5. **Standalone Transactions:** Direct API creation of individual transactions must remain supported without requiring dummy batch import records.
6. **Risk of Silent Data Overwrites:** Retrying or re-importing modified payloads risked silently updating or overwriting raw financial records, violating transaction immutability.

## Decision

Adopt canonical transaction identity scoped by source namespace, canonical account, and external transaction ID, paired with an explicit row-level provenance ledger (`transaction_import_records`):

1. **Canonical Natural Key:** Enforce canonical transaction identity at the database layer via composite unique constraint:
   ```sql
   CONSTRAINT uq_transactions_canonical_id
       UNIQUE (source_namespace, account_id, external_transaction_id);
   ```
2. **Pre-matching Account Resolution:** Ingestion pipelines must resolve incoming external account identifiers to internal canonical `accounts.id` before evaluating transaction identity. Missing accounts cause row rejection, not partial transaction creation.
3. **Source Namespace Isolation:** Introduce `source_namespace VARCHAR(64) NOT NULL DEFAULT 'SYNTHETIC'` to isolate synthetic generation runs from future external bank or partner ingestions.
4. **Nullable First-Seen Import Reference:** Retain `transactions.first_seen_import_id UUID NULL REFERENCES dataset_imports(id) ON DELETE RESTRICT`. Standalone transactions created via direct API endpoints store `NULL`, preserving standalone support without synthetic import jobs.
5. **Import Provenance Ledger (`transaction_import_records`):** Expand Phase 2 Option C scope from 11 to 12 operational tables by adding `transaction_import_records`:
   - Enforce `UNIQUE (dataset_import_id, source_row_number)` for exact row provenance.
   - Record row processing outcomes using an explicit vocabulary:
     - `INSERTED`: New canonical transaction inserted into `transactions` (`transaction_id` references new `transactions.id`).
     - `MATCHED_EXISTING`: Row matched an existing identical canonical transaction; linked to existing `transaction_id` without creating duplicates.
     - `DUPLICATE_IN_IMPORT`: Duplicate natural key within the same CSV payload; linked to the canonical `transaction_id` inserted by the first row.
     - `QUARANTINED`: Row matched an existing transaction key but had materially conflicting payload attributes (`transaction_id` is `NULL`; source row remains traceable via `dataset_import_id`, `source_row_number`, and `row_hash`).
     - `REJECTED`: Row failed syntax, schema, account resolution, or check constraints (`transaction_id` is `NULL`).
   - Track `row_hash` (SHA-256) for auditability.
6. **Strict Material Conflict Quarantine:** When an incoming row matches `(source_namespace, account_id, external_transaction_id)` but differs materially in core financial attributes (`amount`, `currency`, `occurred_at`, `account_id`, `direction`, `transaction_type`, `counterparty_account_id`):
   - Never update or overwrite existing canonical transaction records.
   - Record an error in `dataset_import_errors` with persisted `error_code = 'MATERIAL_CONFLICT'`.
   - Record the row in `transaction_import_records` with `outcome = 'QUARANTINED'` and `transaction_id = NULL`.
7. **Four Distinct Deduplication Boundaries:**
   - *HTTP Request Transport:* Enforced via `Idempotency-Key` header on API endpoints (ephemeral cache/storage).
   - *Byte-Identical File Deduplication & Concurrency:* Enforced via `dataset_imports.file_hash` (SHA-256). Storing `file_hash` alone and relying solely on a partial unique index on active statuses (`PENDING`, `PROCESSING`) cannot prevent duplicate imports under fast-completion race conditions. Concurrency safety is guaranteed by a **transaction-scoped PostgreSQL advisory lock** acquired before lookup and held through record creation:
     ```sql
     SELECT pg_advisory_xact_lock(('x' || substring(:file_hash FROM 1 FOR 16))::bit(64)::bigint);
     ```
     - *Precedence:* An applicable `COMPLETED` import takes precedence and returns its summary (`HTTP 200 OK`). An active `PENDING` or `PROCESSING` import returns `HTTP 409 Conflict` (`IMPORT_IN_PROGRESS`). A new attempt (`status = 'PENDING'`) is created **only when no applicable completed import exists** and retry policy permits it (e.g. prior attempts reached terminal status `FAILED`).
     - *Failure & Timeout:* Bounded by `SET LOCAL lock_timeout = '5s'`. Failures immediately roll back and return a transient error (`503` or `408`); an unsuccessful registration is never reported as successful.
     - *Secondary Safeguard:* `CREATE UNIQUE INDEX uq_dataset_imports_active_hash ON dataset_imports (file_hash) WHERE status IN ('PENDING', 'PROCESSING');` is retained as a defense-in-depth database constraint.
     - *Nullable Hashes:* Nullable `file_hash` uploads bypass locking and file deduplication.
   - *Canonical Natural Identity:* Enforced via `uq_transactions_canonical_id` on `transactions`.
   - *Import Row Provenance:* Enforced via `transaction_import_records`.
8. **Row-Level Idempotent Failure Recovery:** Failed or interrupted imports must reconcile committed row ordinals against `transaction_import_records` for that `dataset_import_id` rather than naively resuming from `MAX(source_row_number) + 1` (which skips rows when batch inserts fail out-of-order).
9. **Supercession Policy:** This ADR formally supersedes ADR-058 following implementation authorization and schema migration `0002_core_operational_schema`.

## Consequences

- Re-importing identical CSVs or overlapping dataset versions no longer creates duplicate transaction rows.
- Complete auditability and lineage are retained across all import jobs and individual rows.
- Canonical transactions remain strictly immutable; conflicting updates are safely quarantined for human review.
- Phase 2 operational scope is precisely bounded at 12 tables (users, accounts, merchants, devices, account_devices, locations, transactions, transaction_import_records, dataset_versions, dataset_imports, dataset_import_errors, audit_events).
- Clear behavioral contracts are established for future synthetic generator and ingestion worker implementations.

---

# ADR-065 — Synthetic Dataset Identity and Import Observation Policies

**Status:** ACCEPTED (Ratified in Phase 12)
**Date:** 2026-10-20
**Related decisions:** ADR-008, ADR-013, ADR-014, ADR-029, ADR-063, ADR-064

## Context

Phase 4 introduces a deterministic synthetic transaction generator and CSV ingestion workflow. The existing canonical transaction identity and provenance contract is defined by ADR-064. Three remaining policies must be explicit before ingestion behavior is implemented: contextual metadata divergence on canonical matches, stable generator identity across reproducible dataset runs, and the handling of byte-identical completed-file re-uploads.

## Decision A — Contextual Metadata Divergence

When an incoming row matches the canonical natural key `(source_namespace, account_id, external_transaction_id)` and all seven core material fields match the canonical transaction, but one or more contextual fields differ (`merchant_id`, `device_id`, `location_id`, `category`, `payment_method`, or `channel`):

1. **Preserve Canonical Fact:** Preserve the canonical transaction exactly as first stored in `transactions`. Do not update or overwrite it.
2. **Provenance Linkage:** Record the incoming row in `transaction_import_records` with `outcome = 'MATCHED_EXISTING'` and link `transaction_id` to the existing canonical transaction UUID.
3. **Cryptographic Fingerprint:** Calculate `row_hash` from the documented normalized, ordered 15-key source-row representation (per `transactions.hashing`), including the contextual fields. The hash serves as tamper-evident provenance evidence, not a reversible copy of the row.
4. **Material Conflict Isolation:** Do not classify a contextual-only difference as `MATERIAL_CONFLICT`; that outcome remains strictly reserved for divergence in the seven core material fields defined by ADR-064 (`account_id`, `amount`, `currency`, `occurred_at`, `transaction_type`, `direction`, `counterparty_account_id`).
5. **Acknowledge Lossy Relational Storage:** Explicitly accept the architectural limitation that alternate contextual plaintext is not stored in relational storage and cannot be reconstructed from `row_hash`. It is only recoverable if the original source CSV file is retained externally and can be matched to the import and row ordinal.
6. **Semantic Precision:** Do not claim the incoming row is fully identical to the canonical row. `MATCHED_EXISTING` signifies that the canonical financial identity and core material facts match; contextual divergence may still exist.

### Consequences

- Preserves the current 12-table operational schema and immutable-fact principle (ADR-008) without requiring premature schema expansion.
- Discards alternate contextual values from SQL queryability; downstream ML feature pipelines and investigators query only the canonical transaction's original context.
- If future investigation requirements necessitate multi-source contextual history, revisit this decision through a new ADR and schema review.

## Decision B — Stable Synthetic Identity and Reproducibility

1. **Deterministic Business Identifiers:** Generated business identifiers are deterministic strings and independent of internal database UUIDs. Initial formats:
   - Accounts: `ACC_[0-9]{6}`
   - Transactions: `TXN_[0-9]{8}`
   - Merchants: `MERCH_[0-9]{5}`
   - Devices: `DEV_[0-9]{6}`
   - Locations: `LOC_[0-9]{3}`
2. **Source Namespace Standard:** The baseline synthetic source namespace is `SYNTHETIC`. The namespace is part of canonical transaction identity through ADR-064.
3. **Strict Reproducibility Contract:** Identical `(seed, generator_version, complete configuration)` inputs must produce byte-identical output for the same supported runtime/dependency contract. The generator must not depend on global PRNG state, uncontrolled iteration order, wall-clock timestamps, or non-deterministic identifiers. Independent seeded random streams must be used.
4. **Progressive Prefix Determinism:** Progressive dataset sizes (100 accounts / ~5,000 txns; 1,000 accounts / ~50,000 txns; 5,000 accounts / ~250,000 txns) are expected to preserve the logical records in the smaller dataset as a strict prefix/subset of the larger dataset **only if this property is explicitly supported by the generator design and tests**. Do not assume that seeding one global PRNG automatically guarantees prefix stability when the target size changes. Use stable per-entity/per-account random streams or another documented deterministic construction.
5. **Namespace Isolation for Experiments:** Distinct seeds or logically different experiments must not reuse the same `(source_namespace, account_id, external_transaction_id)` key for unrelated transactions in a shared database. Use a distinct namespace (e.g. `source_namespace = 'SYNTHETIC_EXP2'`) for each concurrently coexisting logical dataset/experiment, or isolate runs in separate databases. The namespace must be explicit in generator configuration and import metadata; do not silently infer it from a seed.
6. **Idempotent Re-generation & Re-import:** Re-running the same logical dataset with the same namespace preserves business identifiers and safely matches existing canonical transactions. Database UUIDs and import-job UUIDs are generated by persistence and are not part of the generator's deterministic output.
7. **Ground Truth Isolation:** Ground-truth identifiers link to generated business transaction identifiers without adding labels to the production transaction CSV. Ground truth remains a separate artifact (`transactions_ground_truth.csv`) per ADR-013/ADR-014.

### Consequences

- Deterministic regeneration and idempotent re-import are supported without schema changes.
- Operators must intentionally isolate unrelated synthetic experiments to prevent canonical key collisions.

## Decision C — Perpetual Completed-File Deduplication and Explicit Reprocessing

1. **Namespace-Scoped Perpetual Deduplication:** A completed import with the same non-null SHA-256 `file_hash` within the specified target `source_namespace` remains eligible for the completed-import fast path indefinitely (`(source_namespace, file_hash)`). The API returns the existing completed import summary (`HTTP 200 OK`) unless a separately authorized reprocessing workflow is explicitly requested.
2. **Namespace Isolation for Uploads:** Deduplication must never be global on `file_hash` alone. Identical file bytes uploaded under different logical namespaces (e.g., initial upload under `SYNTHETIC` versus subsequent upload under `PUBLIC_DATASET_A`) represent distinct import identities and must be ingested independently into their respective namespaces. Returning a `SYNTHETIC` summary to a `PUBLIC_DATASET_A` upload violates namespace isolation.
3. **Advisory Lock & Concurrency Precedence:**
   - The transaction-scoped advisory lock, active-import check, and completed-import lookup must all operate over the identical composite logical deduplication identity `(source_namespace, file_hash)`.
   - *Key Derivation Contract:* The 64-bit signed integer lock key is derived in the application service (Python) by computing the SHA-256 digest over the unambiguous UTF-8 byte sequence `(source_namespace || ':' || file_hash)` and taking the first 8 bytes as a signed big-endian 64-bit integer:
     ```python
     key_bytes = hashlib.sha256(f"{source_namespace}:{file_hash}".encode("utf-8")).digest()[:8]
     lock_key = int.from_bytes(key_bytes, byteorder="big", signed=True)
     ```
     The registration transaction acquires the lock via `SELECT pg_advisory_xact_lock(:lock_key);`.
   - *Pure SQL Alternative (PostgreSQL 16+):* For standalone migration scripts or direct database clients, the equivalent PostgreSQL expression requires hex-encoding the `bytea` digest before bit conversion:
     ```sql
     SELECT pg_advisory_xact_lock(
         ('x' || substring(encode(sha256((:source_namespace || ':' || :file_hash)::bytea), 'hex') FROM 1 FOR 16))::bit(64)::bigint
     );
     ```
   - *Collision Behavior:* Because the lock key space is 64 bits, hash collisions between distinct `(source_namespace, file_hash)` tuples are statistically rare. If a collision occurs, it merely causes a brief serial queuing delay between those two specific upload transactions. Advisory locking serializes the check-and-insert sequence; actual duplicate determination is strictly governed by the SQL query `WHERE source_namespace = :source_namespace AND file_hash = :file_hash` and the partial unique index `uq_dataset_imports_active_hash`.
   - *Active Conflict Response:* An identical upload targeting the same namespace whose import is currently `PENDING` or `PROCESSING` returns `HTTP 409 Conflict` with `IMPORT_IN_PROGRESS`.
4. **Failure Recovery Preservation:** A failed or interrupted import follows the retry/recovery contract in ADR-064. Perpetual completed-file deduplication must not prevent recovery of an import that never reached `COMPLETED`.
5. **Immutability Protection:** Reprocessing must never bypass `uq_transactions_canonical_id`, overwrite canonical transactions, or mark a failed registration as successful.
6. **Administrative Authorization & Auditing:** Any future explicit reprocessing workflow must be restricted to `ADMIN`, require an explicit request and audit event (`audit_events`), retain the original import record, and create a distinct import attempt if reprocessing is approved. Rows matching existing canonical transactions will create new row-provenance records in `transaction_import_records` for that attempt; they will not create duplicate canonical transaction facts in `transactions`.
7. **Unspecified Reprocessing Shape:** The API parameter or command shape for force reprocessing is **not specified by this ADR** and must be designed before implementation. Do not add `force_reprocess=true` merely as an undocumented bypass. Define how the actor, reason, prior completed import, and new import attempt are audited.
8. **Separation of Deduplication from Data Retention:** This decision does not prescribe deleting import provenance or uploaded source files. File retention and data-retention policy remain separate operational concerns.

## Decision D — Namespace-Scoped Account Identity

1. **Schema Attribute Addition:** Add `source_namespace VARCHAR(64) NOT NULL DEFAULT 'SYNTHETIC'` to both `accounts` and `dataset_imports` in a separately approved schema migration (Checkpoint P4.0).
2. **Composite Account Identity:** Define account external identity as `(source_namespace, external_account_id)`.
3. **Database Uniqueness Constraint:** Enforce uniqueness for this pair when `external_account_id` is non-null via a partial unique index:
   ```sql
   CREATE UNIQUE INDEX uq_accounts_namespace_external_id
   ON accounts (source_namespace, external_account_id)
   WHERE external_account_id IS NOT NULL;
   ```
4. **Deterministic Ingestion Resolution:** Use the target import's explicit `source_namespace` to resolve external account IDs during ingestion. An importer must never select an arbitrary account when a reference is missing or ambiguous; missing accounts cause row rejection (`ACCOUNT_NOT_FOUND` or `AMBIGUOUS_ACCOUNT_REFERENCE`).
5. **Explicit Namespace Propagation:** The baseline synthetic dataset may use `SYNTHETIC`, but external or partner data sources must supply an explicit namespace. A default must not silently misclassify non-synthetic records.
6. **Staged Migration & Unambiguous Reconciliation:**
   - A blanket backfill of legacy records to `SYNTHETIC` is **conditional**. While repository tests create accounts with `external_account_id = NULL`, data-level provenance cannot be proven from code alone for existing development, staging, or production databases.
   - The migration must follow a staged execution pattern:
     - *Stage 1 (Nullable Columns):* Add `source_namespace VARCHAR(64) NULL` to `accounts` and `dataset_imports`.
     - *Stage 2 (Account Reconciliation & Preflight Safeguards):*
       - **Case 1 (Unambiguous Ledger):** For accounts whose linked transactions all share exactly one distinct namespace (`HAVING count(DISTINCT source_namespace) = 1`), backfill `accounts.source_namespace` from `transactions.source_namespace`.
       - **Case 2 (Contaminated / Multi-Namespace Accounts):** For accounts linked to transactions spanning multiple namespaces (`HAVING count(DISTINCT source_namespace) > 1`), preflight queries must **halt the migration** for manual operator remediation. Never assign a namespace nondeterministically via an unconstrained join.
       - **Case 3 (System / Internal Accounts):** Accounts with no transactions and `external_account_id IS NULL` are assigned default `'SYNTHETIC'`.
       - **Case 4 (Ambiguous Legacy External Accounts):** Accounts with no transactions but populated `external_account_id` cannot have their provenance proven from the ledger. Preflight checks must flag these rows for operator confirmation or assignment to an explicit quarantine namespace (e.g. `'LEGACY_UNRESOLVED'`).
       - **Case 5 (Post-Reconciliation Collisions):** Preflight must assert zero duplicate `(source_namespace, external_account_id)` pairs before index creation.
     - *Stage 3 (Dataset Import Reconciliation):*
       - **Case I1 (Unambiguous Ledger):** For imports whose linked transactions all share exactly one distinct namespace (`first_seen_import_id` or `transaction_import_records`), backfill `dataset_imports.source_namespace` from transactions.
       - **Case I2 (Contaminated Imports):** Imports whose linked transactions disagree on namespace halt migration for operator review.
       - **Case I3 (Synthetic Version Metadata):** Imports linked to `dataset_versions` with synthetic configuration are assigned `'SYNTHETIC'`.
       - **Case I4 (Unlinked / External Imports):** Imports lacking transactions or version metadata require explicit operator mapping or assignment to a legacy namespace.
       - **Case I5 (Active Imports):** Migrations must be executed during a maintenance window with zero active imports (`PENDING`, `PROCESSING`).
     - *Stage 4 (Constraint Transition & Indexing):* Set `source_namespace NOT NULL` (with `server_default='SYNTHETIC'`) and create partial unique indexes `uq_accounts_namespace_external_id` and `uq_dataset_imports_active_hash`.
7. **Transaction-Account Namespace Consistency:**
   - The platform evaluates three enforcement tiers for `transaction.source_namespace == account.source_namespace`:
     - *Option C1 (Application-Level):* Validated in ingestion and domain services prior to insertion. Keeps simple single-column FK `transactions.account_id -> accounts.id`. Trade-off: direct SQL, maintenance scripts, and bulk data operations bypass application validation.
     - *Option C2 (PostgreSQL Composite Foreign Key):* Requires `UNIQUE (id, source_namespace)` on `accounts` and composite FK `FOREIGN KEY (account_id, source_namespace) REFERENCES accounts (id, source_namespace)` on `transactions`.
     - *Option C3 (Layered Enforcement — Recommended):* Application validation returns rich diagnostics (`NAMESPACE_MISMATCH`) before insert; database composite FK provides an immutable relational structural backstop.
   - *Scope of Database Guarantee:* A composite foreign key guarantees **relational referential integrity** (no transaction row can ever reference an account in another namespace, even via direct SQL). It does *not* replace application-level validation for developer-friendly error messages, user authorization, audit logging, or business logic.
   - *Foreign-Key Coordination:* The composite foreign key can cleanly supersede the existing single-column FK `fk_transactions_account_id_accounts`, or both can be retained.
8. **No Premature Migration:** No schema migration is authorized by this ADR text alone. The migration must be designed, reviewed, tested, and applied in a separate implementation step.

### Consequences

- Different data sources and synthetic experiments can reuse the same external account ID without conflating accounts.
- Requires an Alembic schema migration and explicit namespace propagation through reference-entity import, dataset import tracking, and transaction ingestion.

### Cross-Cutting Consequences

- ADR-064 remains in force. ADR-065 clarifies behavior; it does not replace canonical transaction identity (`uq_transactions_canonical_id`), material-conflict, advisory-locking, or row-level recovery contracts.
- No new operational table is introduced by these policies.
- The account namespace column, dataset import namespace column, and uniqueness constraints have been applied and verified in migration `0003_account_import_namespace.py` (Checkpoint P4.0).
- File-level idempotency, canonical transaction identity, row-level provenance, and explicit reprocessing are separate concepts and must remain separately documented and tested.

### Implementation Prerequisites & Execution Order

Phase 4 execution followed a strict, dependency-ordered sequence:

1. **ADR-065 Formal Approval:** Project owner reviewed and accepted ADR-065 policies.
2. **Local Database Alignment:** Synchronized local development database with `0002_core_operational_schema`.
3. **Checkpoint P4.0 (Account & Import Namespace Migration):** Staged migration `0003_account_import_namespace.py` applied and verified with preflight safeguards, conditional reconciliation, and Option C3 layered enforcement before reference entities were populated.
4. **Checkpoint P4.1 (Reference Entity & Synthetic Generator Core):** Implemented generator core and reference entities (`locations`, `merchants`, `devices`, `accounts`).
5. **Checkpoint P4.2–P4.3:** Behavioral synthesis, fraud scenarios (F001–F007), scale verification, and isolated ground-truth export.
6. **Checkpoint P4.4 (Transaction Ingestion):** Ingestion engine with deterministic namespace-scoped account resolution, contextual divergence handling, and row provenance tracking.
7. **Checkpoint P4.5–P4.6:** Advisory locking, namespace-scoped deduplication, import APIs (`/api/v1/datasets/imports`), and recovery engine.

---

# ADR-066 — Deterministic Financial Analytics and PostgreSQL Aggregation Architecture

**Status:** ACCEPTED

**Date:** 2026-10-24

**Related decisions:** ADR-004, ADR-008, ADR-047, ADR-049, ADR-050, ADR-063, ADR-064

## Context

Phase 5 introduces financial analytics to provide immediate operational visibility over imported transaction data without coupling to machine learning or risk scoring. The analytical engine must compute platform overview metrics, periodic trends, category breakdowns, merchant rankings, account summaries, and unusual-spending outlier detection across multi-currency and multi-namespace partitions.

Key architectural challenges include:
1. **Compute Locality:** Determining whether aggregations should be performed by loading transaction datasets into application memory (e.g. Pandas) or directly within PostgreSQL using SQL aggregates.
2. **Monetary Precision & Serialization:** Eliminating binary floating-point representation in both calculation and API serialization, ensuring strict two-decimal string formatting.
3. **Temporal Window & Calendar Semantics:** Ensuring trend intervals (day/month) accurately reflect calendar boundaries in the user's requested IANA timezone across daylight saving transitions without coupling to the database connection's session timezone.
4. **Namespace and Object Isolation:** Guaranteeing that account queries cannot leak cross-namespace data or allow callers to tamper with tenant partition boundaries.
5. **Deterministic Outlier Detection:** Defining clear, reproducible statistical outlier detection rules that avoid floating-point math and provide stable pagination.
6. **Performance & Indexing Strategy:** Evaluating database query execution on full-scale benchmarks (250,000 transactions) and determining whether schema modifications or composite indexes are warranted.

## Decision

1. **In-Database Relational Aggregation:** Implement financial analytics via async SQLAlchemy repository queries (`AnalyticsRepository`) that execute single-roundtrip aggregations directly in PostgreSQL. Avoid pulling raw transaction datasets into Python memory for aggregation.
2. **Strict Decimal & Two-Decimal Serialization:**
   - Store all monetary quantities as `NUMERIC(18,2)`.
   - Process calculations using Python's `Decimal` with explicit `ROUND_HALF_UP` quantization.
   - Enforce Pydantic custom types `MoneyStr` (annotated string formatted via before-validator to `"0.00"`) and `OptionalMoneyStr`, forbidding binary floats.
3. **Half-Open Temporal Windows:**
   - Enforce half-open intervals `[from_time, to_time)` consistently across all endpoints: `occurred_at >= :from_time AND occurred_at < :to_time`.
   - Validate `from_time < to_time` when both boundaries are supplied.
4. **Wall-Clock Timezone-Aware Calendar Bucketing:**
   - Calculate trend series using wall-clock start/end bounds projected from the requested timezone:
     ```sql
     WITH calendar_bounds AS (
         SELECT
             (date_trunc(:interval, :from_time, :tz) AT TIME ZONE :tz) AS start_wall,
             (date_trunc(:interval, :to_time, :tz) AT TIME ZONE :tz) AS end_wall
     ),
     series AS (
         SELECT (g AT TIME ZONE :tz) AS bucket_start
         FROM calendar_bounds b,
              generate_series(b.start_wall, b.end_wall, '1 day'::interval) g
         WHERE (g AT TIME ZONE :tz) < :to_time
     )
     ```
   - Left-join the series against transactions truncated to the same timezone `date_trunc(:interval, occurred_at, :tz)`.
   - This guarantees zero-filled contiguous series and exact local midnight boundaries across daylight saving transitions (e.g., 23-hour spring-forward days) independent of the database connection's session timezone.
   - Enforce safety bucket limits before execution: maximum 366 daily buckets (`MAX_DAILY_BUCKETS`) and 120 monthly buckets (`MAX_MONTHLY_BUCKETS`).
5. **Authoritative Account Namespace Scoping:**
   - Account-specific endpoints (`/api/v1/analytics/accounts/{id}` and `/api/v1/analytics/accounts/{id}/unusual-spending`) derive their namespace strictly from the persisted `Account.source_namespace`. Caller overrides in query parameters or headers are ignored, guaranteeing strict tenant boundary enforcement.
   - Available currencies are queried strictly within the account's authoritative namespace.
6. **Empty Currency Response Contract:**
   - When an existing account has no transactions in the requested currency, the endpoint returns HTTP 200 with zeroed metrics and the complete list of `available_currencies` transacted by that account, rather than returning an error.
7. **Deterministic Statistical Outlier Detection:**
   - Compute the account's debit median ($M_{\text{debit}}$) over debits in `[from_time, to_time)` using PostgreSQL `percentile_cont(0.5) WITHIN GROUP (ORDER BY amount)::numeric` rounded to 2 decimals.
   - Outlier threshold: $\text{threshold} = \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$ with multiplier bounded between 1.5 and 10.0 (default 3.0).
   - Compare inclusively: `amount >= :threshold`.
   - Return total outlier count before pagination (`unusual_transaction_count`) along with paginated outliers sorted deterministically by `amount DESC, occurred_at DESC, transaction_id ASC`.
8. **Preserve Existing Database Schema Without Speculative Indexing:**
   - Introduce no new tables or migrations; Alembic head remains `0003_account_import_namespace`.
   - Benchmark query plans (`EXPLAIN (ANALYZE, BUFFERS)`) prove that PostgreSQL uses `ix_transactions_occurred_at`, reading 80,651 matching window rows in 28.02 ms.
   - Total query execution for global overview (86 ms) and trends (141 ms) is dominated by in-engine CPU/memory sorting for continuous medians and grouping. Composite indexes would not reduce this latency because filtering is already fast (28 ms). Speculative index additions are therefore rejected.

## Consequences

- **Correctness:** Eliminates floating-point discrepancies, lookahead leaks, session-timezone bugs, and DST bucket shifts.
- **Security:** Prevents IDOR and cross-namespace partition leakage via authoritative account scoping and input validation.
- **Maintainability:** Pure functional service and repository design with strict schema boundaries and zero persistence side-effects.
- **Performance Trade-Off:** Category breakdowns, merchant rankings, account activity, and unusual spending easily meet the $\le 100\text{ ms}$ P95 budget on 250,000 transactions. Global overview and trends take 135–140 ms P95 on 80k-row windows; this known limitation is explicitly documented rather than masked with speculative indexing or premature precomputed rollups.

---

# ADR-067 — Canonical 34-Feature Vector Contract and Extraction Ordering

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-10-26

**Related decisions:** ADR-017, ADR-050, ADR-058

## Context

Phase 6 established point-in-time temporal and entity features embodied in Pydantic `FeatureVector`. Unsupervised anomaly detection (Phase 7) and downstream risk scoring (Phase 8) require a strictly consistent, immutable ordering when converting structured feature models into 2D NumPy matrices (`np.float64`) for machine learning estimation and online scoring. Discrepancies in feature ordering or silent imputation of missing features would invalidate trained tree splits.

## Proposed Decision

1. **Explicit Feature Versioning:** Bind all feature extraction and model schemas to `FEATURE_VERSION = "v1.0"`. Any mismatch between model record expectations and vectorizer contracts raises `SchemaValidationError`.
2. **Canonical 34-Feature Ordering:** Enforce strict tuple ordering in `FeatureVectorizer.to_numpy()` matching `CANONICAL_FEATURE_NAMES`:
   1. `amount`
   2. `amount_log`
   3. `account_age_days`
   4. `velocity_5m_count`
   5. `velocity_1h_count`
   6. `velocity_24h_count`
   7. `velocity_5m_amount`
   8. `velocity_1h_amount`
   9. `velocity_24h_amount`
   10. `amount_vs_mean_ratio`
   11. `amount_vs_median_ratio`
   12. `amount_zscore`
   13. `is_amount_different_from_constant_baseline`
   14. `has_direction_baseline`
   15. `has_zero_variance_baseline`
   16. `is_cold_start`
   17. `has_device`
   18. `is_new_device`
   19. `device_tx_count`
   20. `has_merchant`
   21. `is_new_merchant`
   22. `merchant_tx_count`
   23. `has_location`
   24. `is_home_location`
   25. `is_new_location`
   26. `location_tx_count`
   27. `location_frequency`
   28. `has_category`
   29. `is_new_category`
   30. `category_spend_share_30d`
   31. `hour_of_day`
   32. `day_of_week`
   33. `is_weekend`
   34. `is_unusual_hour`
3. **Data Type and Null Invariance:** All feature values must be finite numbers; boolean values are explicitly cast to `1.0` or `0.0`. Null or NaN values are strictly forbidden and rejected at the Pydantic schema validation layer.

---

# ADR-068 — Validation-Only Alert-Rate Constrained Threshold Selection

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-10-26

**Related decisions:** ADR-017, ADR-058

## Context

Scikit-learn's Isolation Forest produces continuous anomaly scores $S(X) = - \text{score\_samples}(X)$ where higher values signify greater anomaly. Because unsupervised anomaly scores are uncalibrated, selecting an operating decision threshold $\tau$ directly dictates the operational alert volume. In financial fraud operations, investigative capacity is bounded. Setting an arbitrary threshold risks alert flooding or silent failure to detect fraud clusters. Furthermore, tuning a threshold on the test set causes statistical contamination.

## Proposed Decision

1. **Chronological Split Separation:** Split dataset into target proportions of 60% Train, 20% Validation, and 20% Holdout Test. Training is purely unsupervised (zero fraud labels exposed).
2. **Validation-Only Tuning:** Tune threshold $\tau^*$ exclusively on the validation split using ground-truth fraud labels from synthetic scenarios.
3. **Operational Alert Rate Constraint:** Restrict candidate thresholds to those satisfying $\text{alert\_rate}(\tau) \le \text{max\_alert\_rate}$ (default 0.05, 5%). Select $\tau^*$ maximizing validation F1:
   $$\tau^* = \arg\max_{\tau : \text{alert\_rate}(\tau) \le 0.05} F_1(\tau)$$
4. **Candidate Set and Boundary Semantics:** Evaluate candidate thresholds from observed validation scores plus a boundary candidate `max_score + 1e-6` which guarantees zero alerts (`alert_rate = 0.0`). Under non-negative alert rate budgets, a valid threshold is always found (yielding $F_1 = 0.0$ if no positive alerts fall within budget).
5. **Conservative Tie-Breaking:** When multiple thresholds yield identical maximum F1 within the budget, select the higher threshold (more conservative, minimizing false positives).
6. **Sealed Holdout Test Pass:** Compute final evaluation metrics (Precision, Recall, F1, PR-AUC, Alert Rate, Scenario Recall, Cluster Recall) via a single evaluation pass over the holdout test partition using $\tau^*$.

---

# ADR-069 — Active Model Dynamic Resolution and Promotion Concurrency

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-10-26

**Related decisions:** ADR-059, Proposed ADR-068

## Context

Financial transactions must be scored against the currently approved active machine learning model. During continuous deployment and retraining, model promotions must take effect across application workers without requiring service restarts or distributed cache invalidation messaging (e.g. Redis pub/sub), while preventing multiple models from being concurrently active in the same family.

## Proposed Decision

1. **PostgreSQL as Source of Truth:** On every scoring request, query PostgreSQL for the model record where `name = :family_name AND status = 'ACTIVE'`.
2. **In-Memory Cache Validation:** Cache deserialized model instances in process memory keyed by `model_id`. Validate that `cached[0] == model.artifact_hash`. If absent or hash differs, load from disk with pre-deserialization SHA-256 verification.
3. **Row-Locked Atomic Promotion:** `ModelRepository.promote_to_active()` locks both the candidate and current active model rows using `SELECT ... FOR UPDATE`, transitions the existing active model to `RETIRED`, flushes, transitions the candidate to `ACTIVE`, and commits.
4. **Database-Level Partial Unique Index:** Enforce that at most one model per family can be active via PostgreSQL partial unique index `uq_model_versions_active_family` on `(name)` where `status = 'ACTIVE'`.
5. **Concurrency Boundaries:** Verified for sequential promotions and direct SQL duplicate rejection. Concurrent promotion race conditions under multi-session load have not been tested with concurrent test fixtures and remain an unverified operational boundary.

---

# Proposed Operational Design — Administrative Model Artifact Pruning and Reconciliation Tool

**Status:** DEFERRED TO PHASE 13 (Operational Tooling)

**Date:** 2026-10-26

**Related decisions:** ADR-059, Proposed ADR-069

## Context

Model training persists serialized artifacts (`model.joblib` and `metadata.json`) to the filesystem prior to database record registration and transaction commit. If database registration or transaction commit fails, an unreferenced artifact directory remains on disk. Deleting files in client-side exception handlers was rejected because network or transaction outcomes can be ambiguous, creating risks of deleting valid files.

## Proposed Design

Implement a standalone administrative CLI tool (`finsignal-admin prune-unreferenced-artifacts`) before production release:
1. Scan `{model_artifacts_dir}/` for subdirectories.
2. Query `model_versions.artifact_uri` for all referenced artifacts.
3. Identify unreferenced directories older than a safety threshold (e.g., 24 hours).
4. Provide `--dry-run` and interactive confirmation modes before deletion.
5. **Implementation Status:** Not implemented in Phase 7. Required as a pre-release operational task before production deployment.

---

# ADR-070 — Hybrid Risk Scoring, Validation-Anchored Normalization, and Canonical Analysis Identity

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-10-30

**Related decisions:** ADR-017, ADR-018, ADR-019, ADR-020, ADR-027, Proposed ADR-067, Proposed ADR-068

## Context

Financial transaction intelligence requires combining multivariate unsupervised anomaly detection (Isolation Forest) with domain-specific deterministic heuristics (velocity surges, amount deviations, entity novelty, temporal anomalies) into an interpretable investigation prioritization score. Furthermore, raw Isolation Forest scores are uncalibrated and continuous, requiring normalization that preserves decision threshold alignment without leaking sealed test data or violating temporal discipline.

## Proposed Decision

1. **Hybrid Scoring Formulation:** Linear weighted combination:
   $$\text{raw} = (w_{\text{ml}} \cdot S_{\text{norm}}) + (w_{\text{rule}} \cdot S_{\text{rule}})$$
   with defaults $w_{\text{ml}} = 0.60, w_{\text{rule}} = 0.40$ ($w_{\text{ml}} + w_{\text{rule}} = 1.0$).
2. **Piecewise Linear Normalization (`piecewise_linear_anchored_v1`):**
   Raw anomaly scores $S(X) = -\text{score\_samples}(X)$ are mapped to $[0.0, 100.0]$ anchored to validation-derived bounds:
   $$s_{\min} \mapsto 0.0, \quad \tau^* \mapsto 50.0, \quad s_{\max} \mapsto 100.0$$
   Enforces invariant $s_{\min} < \tau^* < s_{\max}$. The sealed holdout test partition is strictly protected and never accessed during threshold selection or calibration.
3. **Deterministic Heuristic Rules:** Evaluates 9 deterministic financial heuristics yielding structured, explainable `risk_factors` with cumulative rule score $S_{\text{rule}} = \min(100.0, \sum \text{points})$.
4. **Canonical Analysis Identity & Concurrency:**
   Each analysis is uniquely identified by the 4-tuple `(transaction_id, model_version_id, config_version, feature_vector_hash)` enforced by PostgreSQL unique constraint `uq_risk_analyses_identity`.
   In-flight concurrency races are handled via atomic savepoint rollback (`session.begin_nested()`) on PostgreSQL SQLSTATE `23505`, recovering the existing analysis record safely.
5. **Role-Based & Lifecycle Access Gating:**
   `ACTIVE` models are accessible by `ADMIN`, `ANALYST`, and `INVESTIGATOR`.
   `VALIDATED` models are restricted to `ADMIN` (shadow/canary testing).
   `EXPERIMENTAL` and `RETIRED` models are ineligible for transaction evaluation.

---

# ADR-071 — Manual-First Investigation Queue, At-Most-One Primary Transaction Index Invariant, and Append-Only Evidence Immutability

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-11-01

**Related decisions:** ADR-007, ADR-008, ADR-009, ADR-020, ADR-021, ADR-026, ADR-045, Proposed ADR-070

## Context

Operational investigation of suspicious financial activity requires a dedicated case management and evidence collection workflow. Prior to Phase 9, transactions could be flagged by the hybrid scoring engine and structured risk factors, but no formal workflow existed for investigators to review workspaces, link related transactions, assemble evidence snapshots, and record immutable operational decisions.

Key architectural trade-offs:
1. **Case Creation Initiation:** Automated threshold-based case creation risks queue flooding and alert fatigue prior to establishing operational triage baselines.
2. **Primary Transaction Invariant:** Every investigation must focus on a primary transaction, but PostgreSQL schema constraints must balance relational rigor with application atomicity.
3. **Related Transaction Discovery:** Graph-based multi-hop discovery adds graph traversal and cyclic query complexity to a relational modular monolith.
4. **Evidence Immutability:** Evidence must represent durable, unalterable historical snapshots rather than volatile live pointers to mutable records.
5. **Shared Triage Queue & Concurrency:** Multiple investigators review unassigned cases simultaneously, risking assignment race conditions and conflicting resolutions.

## Proposed Decision

1. **Manual-First Case Creation:**
   - Case creation (`POST /api/v1/investigations`) is initiated manually by `ADMIN`, `INVESTIGATOR`, or `ANALYST` roles.
   - Cases enter a shared triage queue (`assigned_to = NULL`, `status = 'OPEN'`).
   - Automated risk-threshold case creation is intentionally deferred to future operational phases.
2. **Primary Transaction Semantics (At-Most-One DB vs. Exactly-One App Invariant):**
   - The PostgreSQL partial unique index `uq_investigation_single_primary` on `investigation_transactions(investigation_id) WHERE relationship_type = 'PRIMARY'` guarantees that an investigation can have **at most one** `PRIMARY` transaction link in the database.
   - The application creation workflow (`InvestigationService.create_investigation`) guarantees that every successfully committed investigation has **exactly one** `PRIMARY` link by inserting the `Investigation`, the primary `InvestigationTransaction`, and the `AuditEvent` in a single uncommitted transaction.
   - A single transaction can serve as the `PRIMARY` transaction across multiple separate investigations.
3. **1-Hop Related Transaction Scope (4-Way Shared-Party Predicate):**
   - Related transactions are strictly limited to direct 1-hop associations sharing the exact same `source_namespace` as the primary transaction.
   - Must satisfy at least one of four shared-party criteria (`account_id` or `counterparty_account_id` matching). Multi-hop and recursive graph search are out of scope.
4. **Append-Only Evidence Snapshots & Database Trigger Immutability:**
   - Supports 6 distinct evidence types paired strictly with their source entities.
   - Evidence records omit `updated_at`. Modifying or deleting evidence is rejected by database trigger `trg_no_update_delete_evidence`.
   - Payloads are bounded to 64 KB JSON. Source entity existence and investigation scope are verified before persistence.
5. **Row-Level Concurrency Protection:**
   - Mutations employ PostgreSQL `SELECT ... FOR UPDATE` row locks.
   - Concurrent self-assignment races yield one winner (200 OK) and one 409 Conflict (`CASE_ALREADY_ASSIGNED`).
   - Explicit attempts by an investigator to take a peer's assigned case are rejected with 403 Forbidden (`FORBIDDEN`).
   - Terminal case immutability: once `RESOLVED`, an investigation cannot be modified, reassigned, or amended with evidence by any role, including `ADMIN`.
6. **Transactional Audit Integration:**
   - Investigation lifecycle changes, assignments, transaction linkings, and evidence attachments emit `AuditEvent` records within the primary database transaction, capturing the authenticated user ID as the actor.
7. **Entity Title Scope Clarification:**
   - The `investigations` entity deliberately omits a case `title` column, anchoring cases directly to their primary transaction UUID and priority to eliminate subjective or redundant ticketing metadata.
   - The `investigation_evidence` entity explicitly requires a `title VARCHAR(255)` column as originally designed, providing human-readable labels for captured snapshots and investigator observations.

---

# ADR-072 — Two-Phase Synchronous AI Summary Generation, REPEATABLE READ Snapshot Isolation, Dual-Fingerprint Staleness Detection, and CAS Token Fencing

**Status:** ACCEPTED (Ratified in Phase 12)

**Date:** 2026-11-04

**Related decisions:** ADR-007, ADR-022, ADR-023, ADR-024, ADR-025, ADR-026, ADR-045, ADR-046, Proposed ADR-071

## Context

Human investigators reviewing complex financial transaction cases require rapid, objective, structured briefings that summarize observed transaction activity, risk factors, related counterparties, and attached evidence records. However, integrating Large Language Models (LLMs) into financial investigation workflows presents severe architectural and security risks:
1. **Advisory Boundary Integrity:** LLMs can generate plausible but ungrounded claims or hallucinated evidence. The AI assistant must never make definitive fraud determinations, alter investigation status, modify evidence, or bypass human review.
2. **Transaction Concurrency & Database Lock Starvation:** LLM API calls or model inference introduce high latency (seconds). Holding database connections or row locks during external provider execution would quickly exhaust connection pools and freeze concurrent investigation workflows.
3. **Snapshot Consistency & Race Conditions:** Concurrent additions of evidence, related transactions, or risk re-analyses while an AI summary is generating could yield an internally inconsistent context snapshot or silently overwrite newer findings.
4. **Prompt Injection & Untrusted Data:** Financial transaction descriptions, merchant names, investigator notes, and evidence payloads are untrusted strings that could contain prompt injection attacks designed to force specific classification verdicts.
5. **Orphaned / Stale Leases:** Workers or processes crashing mid-generation could leave records permanently stranded in `PENDING` state, blocking future summary requests.

## Proposed Decision

1. **Dedicated AI Package Separation (`src/finsignal/ai/`):**
   - Decouple all AI-specific concerns into a dedicated domain package. `src/finsignal/investigations/` maintains investigation case workflows and evidence without importing or coupling to LLM dependencies.
2. **Two-Transaction Lifecycle under `REPEATABLE READ` Isolation:**
   - **Transaction 1 (Reservation & Consistent Snapshot):**
     - Opens with `conn.execution_options(isolation_level="REPEATABLE READ")` before calling `session.begin()`.
     - Locks the `investigation` row via `SELECT ... FOR UPDATE` to serialize case mutation checks.
     - Verifies authorization (investigator assignment) and rejects terminal cases (`RESOLVED` or `CLOSED` return 409 Conflict).
     - Lazily recovers expired pending attempts and verifies no active pending attempt is in progress.
     - Loads the complete investigation graph (primary transaction, related transactions, risk analysis, risk factors, evidence records, and account standing) in a single consistent read snapshot.
     - Computes dual cryptographic fingerprints (`evidence_hash` and `context_hash`).
     - Inserts a `PENDING` record with a cryptographically unique `generation_token` (UUID) into `ai_summaries` and commits.
     - Handles PostgreSQL serialization failures (SQLSTATE `40001`) with bounded exponential backoff retries (up to 3 attempts).
   - **Provider Execution Outside Transactions:**
     - Executes provider generation strictly outside database transaction boundaries. Zero database connections or locks are held during external model latency.
   - **Transaction 2 (Terminal Update & CAS Fencing):**
     - Opens a separate database transaction to persist the terminal result.
     - Uses atomic compare-and-swap (CAS) matching on `(id = :summary_id AND status = 'PENDING' AND generation_token = :token)`.
     - If the token was rotated by recovery, the CAS update affects 0 rows, safely discarding the late response.
     - Atomically commits the terminal status (`COMPLETED` or `FAILED`), structured output, and an `AuditEvent` (`AI_SUMMARY_GENERATED` or `AI_SUMMARY_FAILED`).
3. **Database Constraints & Prevention of Concurrent Active Attempts:**
   - Enforce database check constraint `chk_ai_summaries_lifecycle_state` requiring:
     - `PENDING`: `completed_at IS NULL AND summary IS NULL AND error_message IS NULL`
     - `COMPLETED`: `completed_at IS NOT NULL AND summary IS NOT NULL AND error_message IS NULL`
     - `FAILED`: `completed_at IS NOT NULL AND summary IS NULL AND error_message IS NOT NULL`
   - Enforce PostgreSQL partial unique index `uq_ai_summaries_one_pending_per_investigation` on `(investigation_id) WHERE status = 'PENDING'` guaranteeing at the database engine level that no two workers can execute active generations concurrently for the same case.
   - Enforce `ON DELETE RESTRICT` on `fk_ai_summaries_investigation_id` with SQLAlchemy ORM `passive_deletes="all"`.
4. **Expired PENDING Recovery with Transactional Audit Logging:**
   - Pending summaries older than `ai_pending_timeout_seconds` (default 60s) are lazily transitioned to `FAILED` with generation token rotation.
   - Persists an `AI_SUMMARY_FAILED` audit event in the same transaction if and only if the conditional recovery update affects a row (`cursor_res.rowcount == 1`), eliminating duplicate audit records and guaranteeing all-or-nothing rollback atomicity.
5. **Authoritative Evidence Hashing & Dynamic Staleness Detection:**
   - Compute `evidence_hash` via SHA-256 over canonical sorted JSON of case metadata, primary transaction, risk analysis, risk factors, related transactions, evidence items, and account `status` and `account_type`.
   - Modifying account standing (e.g. `ACTIVE` to `FROZEN`) or account classification (`CHECKING` to `SAVINGS`) materially alters the hash.
   - `GET /api/v1/investigations/{id}/ai-summary` recomputes the authoritative hash and dynamically sets `is_stale: true` when underlying case or account facts have changed, allowing clients to request updated summaries via `POST` with `force_refresh=True`.
6. **Prompt Delimiter Isolation & Defense-in-Depth:**
   - Wraps structured JSON case context in cryptographic nonce tags (`<case_context nonce="{uuid}">`).
   - Neutralizes closing tag delimiters in untrusted input (`</` -> `<\u002F`).
   - System prompt explicitly declares all transaction descriptions, notes, and merchant names as untrusted data, forbidding the model from executing embedded instructions.
7. **Two-Stage Output and Grounding Validation:**
   - Validates JSON output against Pydantic schema `AISummaryOutput` (`executive_summary`, `observed_facts`, `derived_signals`, `potential_interpretations`, `uncertainties_and_limitations`).
   - Grounding check validates that every cited UUID in `cited_evidence_ids` and `cited_transaction_ids` exists in the context snapshot. Fabricated references trigger `AISummaryGroundingError` (HTTP 502).
   - Validating citation existence verifies reference integrity, but semantic claim verification remains human-investigator authoritative.
8. **Provider Abstraction & Mock Baseline:**
   - Implements `BaseAIProvider` and `MockAIProvider` with deterministic scenario outputs and configurable fault injection (`fail_generation`, `timeout`, `malformed_json`, `grounding_failure`). Live external LLM provider integrations remain deferred.

## Consequences

- **Safety:** AI is strictly advisory; cases in terminal `RESOLVED` status reject generation; references are ground-checked against real entities.
- **Reliability:** Zero database locks held during model calls; CAS generation tokens prevent stale overwrites; partial unique index prevents duplicate in-progress executions.
- **Auditability:** Every generation outcome (completion, timeout, recovery, validation failure) is captured in `ai_summaries` and recorded in `audit_events`.
- **Limitation:** Only `MockAIProvider` is active in the current release; live LLM credentials and vector search/RAG remain deferred.

---

# ADR-073 — Phase 12 Scope Revision: Backend/ML v1.0.0 Release and Deferral of Docker Containerization to Phase 13

**Status:** ACCEPTED

**Date:** 2026-11-04

**Related decisions:** ADR-001, ADR-003, ADR-004, ADR-061

## Context

Technical requirement TR-015 and early project planning documents specified Docker-based local development and containerization. ADR-061 previously deferred local containerization to Phase 12 to maintain focus on core financial domain modeling, temporal feature extraction, and ML explainability.

During the Phase 11 review and Phase 12 release preparation, all core backend, database, ML, risk scoring, investigation workflow, and AI assistant capabilities were fully verified natively against Python 3.12 and PostgreSQL (559/559 passing automated tests, strict Ruff and Mypy compliance). Concurrently coupling the v1.0.0 milestone with production Docker packaging, Docker Compose multi-container orchestration, and deployment automation introduces operational risks unrelated to backend domain correctness.

## Decision

1. **Redefine Phase 12 Scope:** Restructure Phase 12 from "Docker, Deployment & Backend/ML Release" to "Backend/ML Release & Finalization".
2. **Versioned Source Code Release:** Deliver FinSignal v1.0.0 as a tested, versioned software library and application release covering the complete Backend + ML platform.
3. **Establish Phase 13 for Containerization & Deployment:** Formally defer production Dockerfile authoring, Docker Compose configuration, production deployment procedures, and cloud infrastructure orchestration to Phase 13 ("Production Deployment & Containerization").
4. **Clarify Release Boundary:** Explicitly document that v1.0.0 represents an architecturally verified backend application and ML model runtime targeting native Python 3.12 and PostgreSQL, not a production-deployed cloud service.
5. **Amend TR-015:** Annotate TR-015 to indicate that Docker containerization is scheduled for Phase 13.

## Consequences

- **Scope Control:** Allows formal verification and versioned tagging of the complete backend and ML codebase without conflating container orchestration defects.
- **Traceability:** Preserves historical context from ADR-061 while transparently scheduling deployment work into a dedicated, subsequent phase.
- **Operational Requirement:** Multi-container packaging and deployment scripts must be completed in Phase 13 prior to production deployment.

---

# ADR-074 — Frontend Technology Stack & Dependency Selection

**Status:** ACCEPTED

**Date:** 2026-11-06

**Related decisions:** ADR-002, ADR-004, ADR-048, ADR-053

## Context

The main technical requirements document (`TRD.md` Section 3.5) established the high-level frontend technology choices: React, TypeScript, Vite, Tailwind CSS, and Apache ECharts.

To transition from planning into implementation (Phase F0), concrete library and tooling decisions must be ratified for client-side routing, server-state management, client-side form orchestration, schema validation, HTTP communication, UI primitives, icons, and automated testing.

## Decision

Approve the proposed React Single-Page Application (SPA) architecture and the supporting library ecosystem:

1. **Core Technology Baseline (Preserved from `TRD.md`):**
   - UI Library: **React**
   - Language: **TypeScript** (Strict Mode enabled)
   - Build Tool & Development Server: **Vite**
   - Styling: **Tailwind CSS** (design tokens per `FRONTEND_DESIGN.md`)
   - Visual Analytics: **Apache ECharts**

2. **Approved Supporting Libraries:**
   - Client-Side Routing: **React Router**
   - Server State, Caching & Data Lifecycle: **TanStack Query**
   - Form Orchestration: **React Hook Form**
   - Form & Input Validation: **Zod**
   - HTTP Transport: **Native Fetch API** encapsulated in typed domain API modules (Axios is rejected)
   - API Contract Typing: **`openapi-typescript`**
   - Accessible UI Primitives: **Radix UI** primitives following selected structural patterns from shadcn/ui
   - Iconography: **Lucide React**
   - Unit & Component Testing: **Vitest**, **React Testing Library**, **user-event**
   - API Network Mocking: **Mock Service Worker (MSW)**
   - End-to-End Testing: **Playwright**
   - Package Management: **npm** with pinned `package-lock.json` and Node.js 20+ LTS

## Governance Requirements & Constraints

1. **Version Selection Discipline:** Architectural approval of a technology is strictly distinguished from installing specific package versions. Mutually compatible, stable, and actively supported versions must be selected at implementation kickoff in Phase F0.
2. **Deterministic Locking:** All dependencies must be strictly pinned through `package-lock.json`. Unpinned production dependencies, floating CDN scripts, and unvetted transitive upgrades are forbidden.
3. **No Unapproved Dependencies:** No additional external libraries or abstractions may be introduced without documented justification and formal approval.
4. **No Premature Global State:** Redux, Zustand, or any other global state management library is rejected for the initial MVP. Server state is owned by TanStack Query; localized interaction state is managed by React component state or lightweight React Context. A global store will be considered only if a demonstrated, concrete state-sharing requirement emerges.

## Consequences

### Positive

- Clean separation between server state (cached, deduplicated, lifecycle-managed) and UI interaction state.
- Leverages standard browser Fetch without third-party HTTP client bloat.
- Provides accessible, keyboard-operable UI components via headless Radix primitives.
- Ensures fast, deterministic unit testing via Vitest and realistic network-boundary tests via MSW.

### Negative

- Requires disciplined dependency management and package-lock maintenance.
- Requires team adherence to server-state patterns to avoid reinventing global state.

---

# ADR-075 — Frontend Authentication, Session Lifecycle & Token Storage Strategy

**Status:** ACCEPTED

**Proposed:** 2026-11-06  
**Accepted:** 2026-11-10

**Related decisions:** ADR-006, ADR-007, ADR-053

## Context

FinSignal backend implements stateless Bearer JWT authentication (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`). The backend configuration (`src/finsignal/core/config.py`) establishes `access_token_expire_minutes` with a **default expiration of 30 minutes** (1,800 seconds), dynamically returned to the client in the login response payload (`TokenResponse.expires_in`). The configuration allows setting expiration between 1 and 1,440 minutes (24 hours).

The backend does not implement refresh tokens, server-side session persistence, or token revocation blocklists (ADR-006). A secure, realistic browser authentication strategy must be selected for holding, applying, and invalidating access tokens.

## Detailed Comparison of Evaluated Approaches

### Option 1 — In-Memory Access-Token Storage (Proposed MVP)

- **Mechanics:** The access token is held strictly in JavaScript memory within an application authentication service or React Context. Outgoing requests attach the token via `Authorization: Bearer <token>`.
- **Persistence:** Token is never written to persistent browser storage (`localStorage`, `sessionStorage`, or cookies).
- **Reload Behavior:** A full browser page reload (F5), navigation away from the application, or opening a new tab completely clears the token from memory.
- **Expiration Behavior:** With the verified 30-minute default access-token lifetime and no refresh endpoint, the session expires in 30 minutes. Once expired, API requests return HTTP 401, forcing the user to log in again.
- **Security Boundaries:**
  - *Mitigation:* Reduces persistent token exposure on disk and eliminates token survival after browser restart or tab closure.
  - *Limitation:* **Does NOT protect an active session against active Cross-Site Scripting (XSS).** Any malicious same-origin script executing in the browser can still intercept in-memory variables, invoke authenticated API methods through the in-memory client, or exfiltrate the token while the session is live.
- **Usability Impact:** High friction on accidental page reloads and at the 30-minute expiration mark. Investigators working on long-running cases may lose unsubmitted form inputs if forced to re-authenticate unexpectedly.

### Option 2 — Browser Persistent Storage (`localStorage` or `sessionStorage`)

- **Mechanics:** The access token is saved in `localStorage` or `sessionStorage` upon login and retrieved on application initialization.
- **Persistence:** `localStorage` persists indefinitely across browser restarts and all tabs in the origin. `sessionStorage` survives page reloads within the current tab, but is typically cleared when the tab is closed.
- **Reload Behavior:** The user remains authenticated across page reloads (F5), significantly reducing workflow interruption.
- **Security Boundaries:**
  - *Limitation:* Both `localStorage` and `sessionStorage` are completely accessible to any same-origin JavaScript. A successful XSS vulnerability or compromised browser extension can directly read and exfiltrate the token.
  - `localStorage` substantially expands the window of vulnerability because the stolen token remains accessible long after the user finishes their immediate session.
- **Usability Impact:** Minimal friction; seamless page reload and multi-tab experience until the 30-minute token expires.

### Option 3 — Backend-Supported HttpOnly, Secure Cookies with CSRF Defense

- **Mechanics:** The backend issues authentication tokens inside an HTTP cookie tagged with `HttpOnly; Secure; SameSite=Strict` (or `Lax`). The browser automatically includes the cookie in same-origin or authorized cross-origin requests.
- **Persistence:** Governed by cookie headers (`Max-Age` / `Expires`).
- **Reload Behavior:** Survives page reloads seamlessly while the cookie remains valid.
- **Security Boundaries:**
  - *Mitigation:* JavaScript code (and therefore XSS scripts) cannot directly read or steal the token from the cookie jar.
  - *Limitation:* Vulnerable to Cross-Site Request Forgery (CSRF) unless paired with strict CSRF tokens, anti-CSRF headers, and strict SameSite configuration.
- **Architectural Prerequisite:** **Cannot be implemented as a frontend-only change.** Requires coordinated backend architectural modifications:
  1. Backend cookie issuance on `POST /api/v1/auth/login`.
  2. Backend cookie clearance on `POST /api/v1/auth/logout`.
  3. Coordinated CORS credentials configuration (`allow_credentials=True` with explicit non-wildcard origins).
  4. CSRF protection middleware and Double-Submit or synchronizer token patterns.
  5. Formal session refresh/rotation and revocation semantics.

## Trade-off Analysis & Recommendation

| Criteria | Option 1: In-Memory | Option 2: Web Storage | Option 3: HttpOnly Cookies |
|---|---|---|---|
| **Direct Script Token Access** | Accessible to active XSS | Accessible to active & passive XSS | Completely inaccessible to script |
| **Post-Session Disk Persistence** | None (Zero disk trace) | High (`localStorage` persists indefinitely) | Configurable / Session-bound |
| **Page Reload (F5) Usability** | Poor (Requires re-login) | Good (Survives reload) | Excellent (Survives reload) |
| **Session Lifetime** | 30 minutes (Verified default) | 30 minutes (Verified default) | Flexible (Supports refresh rotation) |
| **Backend Modification Required** | None (Uses existing Bearer API) | None (Uses existing Bearer API) | Substantial backend re-architecture |

### Decision — ACCEPTED (2026-11-10)

**Adopt Option 1 — In-Memory Access-Token Storage for the FinSignal Frontend MVP.** The system owner explicitly approved this option on 2026-11-10.

#### Binding implementation requirements

1. Hold the access token only in a narrowly scoped in-memory authentication/session service. Do not persist it in `localStorage`, `sessionStorage`, cookies, IndexedDB, or another browser persistence mechanism.
2. Attach the token to protected API requests using `Authorization: Bearer <access_token>` through the centralized API client.
3. Never expose token values through component props, URL parameters, query keys, logs, error reports, analytics, or browser-visible diagnostics.
4. Do not put the token in a persisted global state store or persistence plugin.
5. Clear the in-memory token and authenticated user/query state on explicit client logout and on a confirmed invalid/expired-session response (`401`). Do not treat `403` as session expiry.
6. After a full page reload or opening a new tab, require the user to authenticate again. Do not implement silent refresh without a separately approved backend refresh contract.
7. After authentication expiry or reload, preserve at most a validated, safe internal destination so the user can return to the relevant workspace after signing in. Do not persist access tokens, sensitive evidence, private notes, or unsaved sensitive form payloads to achieve route restoration.
8. Treat `TokenResponse.expires_in` as the authoritative lifetime supplied by the backend. The documented default is 30 minutes; deployments may configure a different value. Do not hard-code 30 minutes in frontend logic.
9. The backend remains authoritative for authentication and authorization. `/auth/me` establishes current-user presentation context; frontend role checks are not a security boundary.
10. Document the security boundary accurately: in-memory storage reduces persistent token exposure but does **not** protect an active session from same-origin XSS or malicious script execution.

#### Deferred alternative and review trigger

If reload/re-authentication friction materially harms investigator workflows, evaluate Option 3 (backend-supported `HttpOnly`, `Secure`, appropriately `SameSite` cookies with explicit CSRF protection, credentialed CORS, refresh/rotation, expiry, and revocation semantics) as a coordinated full-stack decision. This is not authorized by this ADR and must not be approximated as a frontend-only change. Reconsider only with evidence from MVP usage or a changed security/product requirement.

Option 2 (`sessionStorage`/`localStorage`) is not selected for the MVP.

---

# ADR-076 — OpenAPI-Driven TypeScript Contract Generation & Network Boundary Validation

**Status:** ACCEPTED

**Date:** 2026-11-06

**Related decisions:** ADR-047, ADR-048, ADR-053

## Context

The FastAPI backend exposes an authoritative OpenAPI 3.1 specification at `/openapi.json` derived directly from Pydantic v2 schemas. Manual replication of TypeScript types in the frontend introduces inevitable schema drift, subtle field type mismatches (such as string decimals vs numbers), and omission of optionality constraints.

## Decision

Approve **`openapi-typescript`** as the standard tooling for generating static TypeScript interfaces from the running backend OpenAPI specification.

## Governance & Engineering Requirements

1. **Source of Truth:** Types must be generated directly from the live or exported `/openapi.json` of the running FastAPI backend, never from handwritten mock files.
2. **Separation of Generated Code:** Generated types must be written to an isolated directory (e.g. `src/api/generated/schema.ts`) and kept strictly separated from handwritten application code.
3. **Immutability of Output:** Developers must not manually modify, patch, or edit generated TypeScript files. Any schema defect must be corrected upstream in the backend Pydantic models.
4. **Repository & CI Strategy:** Generated types will be committed to the repository to allow offline builds and local frontend development without requiring a running database or backend service. CI must execute an automated contract drift check (`npm run check:types-drift`) that boots the backend or compares exported schemas to ensure generated types remain in exact synchronization.
5. **Feature Module Integration:** Feature API clients (`src/features/*/api/*.ts`) must consume generated types for all request bodies, query parameters, and response models.
6. **Compile-Time Typing vs. Runtime Validation:**
   - *Important Distinction:* **OpenAPI-generated TypeScript types provide compile-time type checking only; they perform zero validation at runtime.** TypeScript types are erased upon JavaScript compilation.
   - The application does not claim 100% runtime contract safety solely from generated types.
   - Runtime response validation (e.g., using Zod schemas) will not be introduced globally by default to avoid redundant parsing overhead, but should be employed selectively at critical boundaries (such as complex financial decimal validation or external file parsing) where a concrete operational need justifies it.

## Consequences

### Positive

- Zero schema drift between backend Pydantic models and frontend TypeScript compilation.
- Zero runtime overhead or bundle weight added by static type definitions.
- Automatic propagation of backend schema changes to frontend type-checking during development.

### Negative

- Requires backend execution or an exported schema artifact whenever API contracts evolve.

---

# ADR-077 — Transaction & Dataset Import Collection Read API Requirements

**Status:** ACCEPTED

**Date:** 2026-11-06

**Related decisions:** ADR-008, ADR-028, ADR-058, ADR-064, ADR-065

## Context

The Frontend PRD (`FRONTEND_PRD.md` Screens 7.1 and 8.2) requires an analyst/investigator to explore, sort, and filter transaction records across namespaces, currencies, date ranges, and accounts. Additionally, Screen 7.1 requires viewing past dataset import executions and their error logs.

The comprehensive documentation audit revealed that while `API_GUIDELINES.md` sections 21, 22, and 70 document `GET /api/v1/transactions` and `GET /api/v1/transactions/{id}`, these endpoints were not implemented in the FastAPI router during Backend Phases 1–12 (only `/transactions/{id}/risk` and `/investigations/{id}/transactions` exist). Furthermore, `src/finsignal/api/v1/datasets.py` lacks a collection listing endpoint (`GET /api/v1/datasets/imports`).

## Decision

1. **Approve Requirement for Missing Endpoints:** Ratify the requirement to implement the following three read endpoints in the FastAPI backend:
   - `GET /api/v1/transactions` (paginated collection querying and multi-field filtering)
   - `GET /api/v1/transactions/{id}` (single transaction fact retrieval)
   - `GET /api/v1/datasets/imports` (paginated dataset import history)
2. **Scope as Backend API Readiness Enhancement:** Treat the implementation of these endpoints as a separately scoped backend API readiness enhancement within Phase F0.
3. **Preserve Release Integrity:** Do not rewrite Backend + ML v1.0.0 release history. v1.0.0 remains the released backend milestone. These three endpoints represent an operational contract enhancement required to enable Frontend MVP workflows.
4. **Technical Specification:** All three endpoints must be implemented strictly according to the dedicated technical specification in `docs/BACKEND_API_READINESS.md`.

## Consequences

### Positive

- Fully unblocks the frontend MVP transaction exploration and dataset visibility screens with authentic PostgreSQL-backed contracts.
- Avoids fragile client-side mocks or scope compromises.

### Negative

- Requires backend implementation, testing, and documentation verification during Phase F0 before frontend Phase F3/F4 development can commence.

---

# ADR-078 — Frontend Zod 3 to Zod 4 Migration (`4.6.7`)

**Status:** ACCEPTED (2026-11-11)

**Related decisions:** ADR-074, ADR-076

## Context

The independent Phase F1 post-implementation audit identified 11 `npm audit` vulnerabilities, including 1 high-severity advisory (`1243066`: memory exhaustion when validating oversized constrained collections, affecting `zod < 4.6.6`) on direct production dependency `zod@3.25.76` (`package.json` `"zod": "^3.25.23"`). Although `zod` had not yet been invoked in Phase F1 runtime code, it ships in the production dependency tree (`npm audit --omit=dev` flagged `zod` as the sole production vulnerability). `@hookform/resolvers@5.9.2` already supports `"zod": "^3.25.0 || ^4.0.0"`, and no Zod 3-specific breaking APIs were used in existing `frontend/src/` or `frontend/tests/`.

## Decision

Approve and execute the upgrade of `zod` from `3.25.76` to `^4.6.7` (locked at `4.6.7` in `frontend/package-lock.json`), verified with React Hook Form (`7.91.0`) and `@hookform/resolvers` (`5.9.2`), and require sensible collection length limits (such as `.max(...)`) on untrusted array/string inputs in future Phase F2+ form schemas.

## Rationale

- Eliminates the sole high-severity production dependency advisory without weakening audit policy or introducing npm `overrides`.
- Migrates before feature form schemas are authored in Phase F2+, avoiding later multi-feature schema rewrites.

## Alternatives Considered

1. **Pin Zod 3.x with a risk-acceptance waiver:** Leaves a known high-severity DoS advisory in the production dependency graph and fails `npm audit --omit=dev`.
2. **Replace Zod with another validator:** Violates ADR-074 stack selection and loses unified `@hookform/resolvers` schema typing.

## Consequences

- `npm audit --omit=dev` passes with `0` vulnerabilities.
- Future validation schemas must use Zod 4 APIs and enforce bounded collection constraints under TypeScript `strict: true`.

---

# ADR-079 — Vitest 3 to Vitest 5 Migration (`5.1.0`) & Node.js 24 Runtime Alignment

**Status:** ACCEPTED (2026-11-11)

**Related decisions:** ADR-074 (partially amends Node.js runtime baseline and Vite floor)

## Context

The Phase F1 post-implementation audit identified 2 critical development-tooling vulnerabilities in `vitest@3.2.7` (`tinypool <= 2.1.1` prototype pollution to RCE advisories `1241260`/`1241261` and `@vitest/mocker` path-traversal/code-injection advisories `1193683`/`1193684`/`1242767`), with remediation requiring a semver-major upgrade to `vitest@5.1.0`. However, `vitest@5.1.0` specifies `"engines": { "node": "^22.12.0 || ^24.0.0 || >=26.0.0" }` (dropping Node 20) and `"peerDependencies": { "vite": "^6.4.0 || ^7.0.0 || ^8.0.0", ... }`, whereas Phase F0 `ADR-074` targeted Node.js `20+` LTS (`frontend/.nvmrc = 20`, `package.json` `engines.node = ">=20.0.0"`, and `"vite": "^6.3.5"` while locked at `6.4.6`).

## Decision

1. Upgrade `vitest` from `3.2.7` to `^5.1.0` (locked at `5.1.0` in `frontend/package-lock.json`).
2. Align `frontend/.nvmrc` from `20` to `24` (matching active Node.js `v24.18.0` LTS verification), update `frontend/package.json` `"engines.node"` to `"^22.12.0 || >=24.0.0"`, and align `"vite"` range to `"^6.4.0"` (keeping locked `vite@6.4.6` without an unrelated Vite major upgrade).

## Rationale

- Eliminates all critical development-tooling vulnerabilities and removes `tinypool@1.1.1` (22 packages removed) while preserving existing Vitest + `jsdom` + MSW testing architecture (`47/47` tests passing).
- Updating `.nvmrc` prevents `.github/workflows/ci.yml` (`actions/setup-node@v4`) from provisioning Node 20 against Vitest 5's incompatible engine constraint.

## Alternatives Considered

1. **Upgrade to Vitest `4.1.12` instead of `5.1.0`:** Retains Node 20 compatibility but lags behind the owner-approved Vitest 5 target.
2. **Keep `vitest@3.2.7` or leave `.nvmrc` at `20`:** Retains critical `tinypool` advisories or breaks CI Node version parity.

## Consequences

- Zero critical or high vulnerabilities remain in the frontend dependency tree.
- Local development and CI environments must use Node.js `^22.12.0 || >=24.0.0` (`.nvmrc = 24`).
- Superseded aspect of `ADR-074`: `Node.js 20+ LTS` baseline is replaced by `^22.12.0 || >=24.0.0` (`.nvmrc = 24`).

---

# ADR-080 — Temporary Development Dependency Security Exception for `minimatch@10.2.6`

**Status:** PENDING OWNER APPROVAL (Proposed 2026-11-11)

**Related decisions:** ADR-074, ADR-079

## Context

After migrating `zod` to `4.6.7` (`ADR-078`) and `vitest` to `5.1.0` (`ADR-079`), `npm audit --omit=dev` reports `0` production vulnerabilities, while full `npm audit` reports `7 moderate` development-only advisories for `GHSA-g3hv-75wg-m249` (*minimatch has potential denial of service via globparts amplification*, affected range `7.0.0 - 11.0.0`).

The verified dependency path is dev-only ESLint CLI tooling:

- `typescript-eslint@8.72.2` (latest upstream release) → `@typescript-eslint/{eslint-plugin,parser,type-utils,utils,typescript-estree}@8.72.2` → `minimatch@10.2.6`.

`@typescript-eslint/typescript-estree@8.72.2` depends on `"minimatch": "^10.2.2"`, and `10.2.6` is the latest release in the `10.x` line (the upstream fix is `minimatch@11.0.1+`). Running `npm audit fix` without `--force` reports `up to date` and performs no upgrades.

## Technical Finding vs. Risk Acceptance Governance

- **Technical finding (Verified):** No production bundle (`dist/`) exposure exists; `npm audit --omit=dev` passes with `0` vulnerabilities. No compatible non-forcing upstream upgrade exists without adding an unvetted npm `overrides` rule or running `npm audit fix --force`.
- **Owner risk acceptance decision:** **`PENDING OWNER APPROVAL`** — this exception is **not** accepted until explicitly approved by the project owner.

## Proposed Decision (Awaiting Owner Approval)

Approve a temporary, scoped development-only exception allowing `minimatch@10.2.6` under `@typescript-eslint/typescript-estree@8.72.2` during Phase F1 without adding manual npm `overrides` or running `npm audit fix --force`, subject to mandatory re-evaluation before Phase F7/F8 release or immediately when upstream `typescript-eslint` adopts `minimatch@^11.0.1`.

## Alternatives Considered

1. **Add an npm `overrides` entry forcing `minimatch@^11.0.1`:** May introduce subtle breaking behavior inside `@typescript-eslint/typescript-estree` glob handling and bypasses normal upstream semver resolution without maintainer approval.
2. **Run `npm audit fix --force`:** Risks breaking/downgrading ESLint packages across incompatible major versions.
3. **Wait in Phase F1 until upstream releases a patched `@typescript-eslint`:** Blocks F1 formal sign-off despite zero production exposure.

## Consequences (If Approved)

- Permits Phase F1 formal acceptance with `npm audit --omit=dev` (`0` vulnerabilities) enforced strictly while tracking the 7 moderate dev-only advisories until upstream remediation.
- Requires revisiting this exception in CI/dependency checks prior to Phase F7 hardening and upgrading `typescript-eslint` as soon as a compatible patch releases.

# 4. Decision Dependency Map

```text
Python
  ↓
FastAPI
  ↓
Modular Monolith
  ↓
PostgreSQL
  ↓
Domain Model
  ↓
Transaction Ingestion
  ↓
Financial Analytics
  ↓
Temporal Features
  ↓
Isolation Forest
  ↓
Hybrid Risk
  ↓
Investigation
  ↓
Evidence
  ↓
AI Summary
```

Security and testing apply across every layer.

---

# 5. Decision Review Rules

An accepted decision should be revisited when:

- new requirements contradict it;
- implementation reveals a material flaw;
- scale changes significantly;
- security requirements change;
- compliance requirements emerge;
- a deferred technology becomes justified.

A decision should not be changed solely because another technology is more fashionable.

---

# 6. How to Supersede a Decision

When an accepted decision changes:

1. retain the original ADR;
2. mark it `SUPERSEDED`;
3. create a new decision;
4. reference the previous decision;
5. explain the reason for change;
6. update affected architecture/technical documents;
7. record the implementation impact in `PROJECT_LOG.md`.

Do not rewrite history without explanation.

---

# 7. Open Decisions

The following decisions remain intentionally open until implementation provides enough information:

1. Exact JWT revocation/logout strategy.
2. Exact password policy.
3. Exact model artifact storage location — Implementation-informed recommendation (Phase 7): Default to filesystem directory `{model_artifacts_dir}/{model_id}/model.joblib` with companion `metadata.json`. (Status: OPEN, recommendation pending owner approval).
4. Exact LLM provider — Implementation-informed resolution (Phase 10): Abstracted via `BaseAIProvider` and implemented via `MockAIProvider` with deterministic scenario generation, fault injection, and latency simulation. Production external LLM providers (Anthropic, OpenAI) remain deferred until justified. (Status: RESOLVED FOR BACKEND+ML V1.0).
5. Exact AI model — Implementation-informed resolution (Phase 10): Configured via application setting `Settings.ai_model` (default `"mock-v1"`) and recorded per-generation in `ai_summaries.model`. (Status: RESOLVED).
6. Exact risk-score thresholds — Implementation-informed resolution (Phase 8): Defaults to linear cutoffs [0.00, 25.00) LOW, [25.00, 50.00) MEDIUM, [50.00, 75.00) HIGH, [75.00, 100.00] CRITICAL, with configurable escalation floors. (Status: RESOLVED).
7. Exact feature normalization strategy — Implementation-informed resolution (Phase 8): Resolved via piecewise_linear_anchored_v1, anchoring validation score bounds [score_min, tau*, score_max] -> [0.0, 50.0, 100.0]. (Status: RESOLVED).
8. Exact model artifact serialization format — Implementation-informed recommendation (Phase 7): Use `joblib.dump()` with two-phase atomic temporary file rename and pre-deserialization SHA-256 integrity check. (Status: OPEN, recommendation pending owner approval).
9. Exact deployment platform.
10. Exact rate-limiting implementation defaults.
11. Exact background-job strategy if batch processing becomes slow.
12. Exact frontend architecture after Backend + ML completion — Resolved via ADR-074 (Frontend Stack: ACCEPTED), ADR-075 (Authentication & Token Storage Strategy: ACCEPTED), ADR-076 (OpenAPI Type Generation: ACCEPTED), ADR-077 (Transaction & Dataset Import Read APIs: ACCEPTED), ADR-078 (Zod 4.6.7 Migration: ACCEPTED), and ADR-079 (Vitest 5.1.0 & Node 24 Alignment: ACCEPTED).
13. Temporary development dependency security exception for `minimatch@10.2.6` (`GHSA-g3hv-75wg-m249`, `typescript-eslint@8.72.2`) — Documented in ADR-080. (Status: PENDING OWNER APPROVAL).
14. Exact retention window for completed-file re-upload deduplication — Resolved via ADR-065 (Perpetual retention for byte-identical files with separately authorized administrative reprocessing).
15. Policy for differing contextual metadata on canonical match — Resolved via ADR-065 (Candidate 1: Immutable canonical preservation with row-hash provenance).
16. Account external identifier uniqueness and namespace resolution contract — Policy selected via proposed ADR-065 Decision D (Namespace-Scoped Account Identity `(source_namespace, external_account_id)`); schema migration and existing data backfill pending implementation authorization.
17. Sparse/new-account baseline strategy — Resolved in Phase 6 via Candidate 2+3 Hybrid (Provisional minimum observation threshold N=3 with neutral sentinels and cold-start indicator).

### Resolved Decision Note: Contextual Metadata Divergence on Canonical Match
- **Status:** RESOLVED via proposed ADR-065 (Decision A: Candidate 1 — Immutable Canonical Preservation with Hash Provenance).
- Canonical transaction facts remain strictly immutable. Alternate contextual values are not stored in relational storage; `transaction_import_records.row_hash` records tamper-evident proof that an alternate payload appeared.

### Resolved Decision Note: Completed Import Deduplication Retention
- **Status:** RESOLVED via proposed ADR-065 (Decision C: Namespace-Scoped Perpetual Deduplication).
- Byte-identical files within the same target `source_namespace` (`(source_namespace, file_hash)`) return HTTP 200 with the existing import summary indefinitely. Deduplication is strictly namespace-scoped; identical files uploaded to different namespaces are treated as distinct import identities. Explicit reprocessing is a separate administrative workflow.

### Policy Selection Note: Account External Identifier Uniqueness and Namespace Resolution Contract (ADR-065 Decision D)

- **Status:** POLICY SELECTED via proposed ADR-065 (Decision D: Namespace-Scoped Account Identity `(source_namespace, external_account_id)`).
- **Architectural Policy:** Incoming source account identifiers must be resolved deterministically using `(source_namespace, external_account_id)`. The transaction's source namespace must agree with the referenced account's source namespace.
- **Migration Dependency:** The current database schema (`0002_core_operational_schema.py`) does not yet include `accounts.source_namespace`, `dataset_imports.source_namespace`, or the composite unique constraints. An authorized Alembic migration (Checkpoint P4.0), executing a staged execution pattern (nullable column -> duplicate preflight & reconciliation -> NOT NULL & partial unique index), is an explicit prerequisite before reference-entity account generation (Checkpoint P4.1) and transaction ingestion (Checkpoint P4.4). No schema migration is authorized by this policy selection alone.


### Resolved Decision Note: Sparse/New-Account Baseline Strategy (Phase 6 Resolution Checkpoint)

- **Status:** RESOLVED in Phase 6 (Feature Engineering Implementation) via Hybrid Candidate 2 + 3.
- **Resolution Rationale & Architecture:**
  1. *Centralized Threshold:* Approved provisional minimum observation threshold `MIN_BASELINE_OBSERVATIONS = 3` scoped strictly to the evaluated transaction's direction and currency.
     - *Justification:* 3 observations is the pragmatic minimum allowing sample variance calculation ($N - 1 = 2$ degrees of freedom) without indefinitely locking new accounts into cold-start status. This threshold is recorded as an operational baseline policy, not a statistically validated guarantee.
  2. *Neutral Sentinels for Sparse History ($N < 3$):*
     - `amount_vs_mean_ratio = 1.0`
     - `amount_vs_median_ratio = 1.0`
     - `amount_zscore = 0.0`
     - `has_direction_baseline = 0`
     - `has_zero_variance_baseline = 0`
     - `is_amount_different_from_constant_baseline = 0`
  3. *Zero-Variance Handling ($N \ge 3 \text{ and } s^2 = 0$):*
     - `amount_zscore = 0.0` (neutral, avoiding arbitrary inflated z-scores)
     - `has_zero_variance_baseline = 1`
     - `is_amount_different_from_constant_baseline = 1` only when the evaluated amount differs from the invariant historical mean.
  4. *Decoupled Cold-Start Semantics:*
     - `is_cold_start = 1` if total account prior transaction count across all directions and currencies is $< 3$, else `0`.
     - Cold-start status is strictly decoupled from account age. Clamped negative account age (from historical data backfilling prior to account DB persistence) does not trigger cold start.
  5. *30-Day Category Spend Share Bounding:*
     - Evaluated over preceding 30 days $[t - 30\text{d}, t)$ using historical DEBIT transactions in matching currency. Returns `0.0` if category is missing or denominator is zero; result is bounded in $[0.0, 1.0]$.

### Resolved Decision Note: AI Assistant Architecture, Evidence Hashing & Grounding (Phase 10 Resolution Checkpoint)

- **Status:** RESOLVED in Phase 10 via Proposed ADR-072.
- **Resolution Rationale & Architecture:**
  1. *Two-Transaction Synchronous Lifecycle:* Transaction 1 executes under `REPEATABLE READ` isolation to lock case state, verify authorization, lazily recover expired pending attempts, and capture an immutable snapshot. Model execution runs outside active database transactions. Transaction 2 commits terminal status and audit events using CAS token fencing.
  2. *Dual Fingerprinting:* `evidence_hash` covers the entire case graph including primary transaction, risk analysis, risk factors, related transactions, evidence items, and account `status` and `account_type`. `context_hash` captures the bounded prompt context.
  3. *Dynamic Staleness:* `GET /api/v1/investigations/{id}/ai-summary` dynamically recomputes the authoritative hash against current database state and flags `is_stale: true` if underlying case or account facts have changed.
  4. *Two-Stage Validation:* Pydantic schema validation followed by strict grounding citation validation ensures that every cited entity UUID exists in the supplied snapshot.
  5. *Mock Baseline:* Operates via `MockAIProvider` with fault injection; live external LLM provider integrations remain deferred.

Open decisions must not block decisions that are already sufficiently established.

---

# 8. Decisions Explicitly Out of Current Scope

The following are intentionally not being decided for the current Backend + ML release:

- frontend UI architecture;
- frontend state-management library;
- frontend component library;
- frontend deployment;
- advanced visualization implementation;
- browser E2E framework;
- Kafka cluster architecture;
- distributed service topology;
- graph database schema;
- RAG architecture;
- production-scale ML platform architecture.

These belong to later project phases.

---

# 9. Decision Quality Criteria

Before accepting a new major technical decision, evaluate:

### Correctness

Does it preserve financial and analytical correctness?

### Simplicity

Does it solve the requirement without unnecessary infrastructure?

### Security

Does it introduce new attack surfaces?

### Testability

Can its behavior be verified reliably?

### Reproducibility

Can results be recreated?

### Maintainability

Can another developer understand and modify it?

### Scalability

Does it leave a reasonable migration path if scale increases?

### Portfolio Value

Does it demonstrate meaningful engineering rather than technology accumulation?

---

# 10. Final Architectural Direction

The current FinSignal architecture is intentionally centered around:

```text
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │     REST API        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       Domain Logic       Analytics / ML     Investigation
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                         PostgreSQL
                               │
                               ▼
                       Evidence Context
                               │
                               ▼
                         AI Provider
```

The architecture deliberately avoids unnecessary distributed infrastructure while preserving clear boundaries for future evolution.

The current goal is a system that is:

- technically credible;
- financially correct;
- temporally sound;
- ML-aware;
- explainable;
- secure;
- testable;
- reproducible;
- investigation-oriented;
- AI-assisted without being AI-controlled.

---

# 11. Final Decision Principle

**Do not add complexity because it looks impressive. Add complexity when the system has earned the requirement for it.**

FinSignal's first release should demonstrate that a developer can build a trustworthy financial intelligence platform from:

```text
Reliable Data
+
Strong Domain Modeling
+
Temporal Feature Engineering
+
Practical ML
+
Explainable Risk
+
Structured Investigation
+
Grounded AI
+
Security
+
Testing
```

That foundation is more valuable than prematurely introducing distributed systems, streaming platforms, or advanced ML infrastructure.
