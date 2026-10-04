# FinSignal — Architecture & Engineering Decisions

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Architecture & Engineering Decisions  
**Scope:** Backend + ML  
**Status:** Planning / Implementation-Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-10-04

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

Logout/token invalidation behavior must be implemented according to the security design rather than assuming JWTs are automatically revocable.

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

**Status:** ACCEPTED

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

---

# ADR-059 — Model Artifact Integrity Verification via SHA-256

**Status:** ACCEPTED

## Context

Loading serialized ML models from disk introduces security and operational risks if artifacts are tampered with, corrupted, or replaced.

## Decision

Store a cryptographic SHA-256 hash in `model_versions.artifact_hash` upon training. Verify this digest prior to loading in the inference engine. Any hash mismatch or missing hash must immediately raise a controlled `ModelIntegrityError` and abort loading.

---

# ADR-060 — Polymorphic Evidence Source Validation at Application Layer

**Status:** ACCEPTED

## Context

Investigation evidence can reference diverse source entities (transactions, accounts, risk analyses, devices). Enforcing database foreign keys for each possible type would require complex schema patterns (EAV or multiple nullable foreign keys).

## Decision

Use an unconstrained UUID column `source_id` paired with `source_type` on `investigation_evidence` and enforce referential integrity, entity existence, context boundary, and investigator authorization at the application domain layer.

---

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
3. Exact database migration tooling configuration.
4. Exact model artifact storage location.
5. Exact LLM provider.
6. Exact AI model.
7. Exact risk-score thresholds.
8. Exact feature normalization strategy.
9. Exact model artifact serialization format.
10. Exact deployment platform.
11. Exact rate-limiting implementation defaults.
12. Exact background-job strategy if batch processing becomes slow.
13. Exact frontend architecture after Backend + ML completion.

### Detailed Open Decision: Sparse/New-Account Baseline Strategy (Phase 6 Resolution Checkpoint)

- **Question:** How should the temporal feature engineering engine compute baseline metrics (e.g. spending mean, velocity ratio) when an account has zero or very few historical transactions?
- **Why it matters:** Naive calculation produces division-by-zero, NaNs, or extreme anomaly ratios that generate false-positive alert storms on legitimate new customer accounts.
- **Required Information:** Empirical distribution of account age and transaction volume in the Phase 5 synthetic dataset; baseline stability analysis under low sample sizes.
- **Resolution Phase:** Phase 6 (Feature Engineering Engine) prior to baseline feature construction.
- **Candidate Approaches:**
  1. *Global / segment fallback:* Impute population or account-tier mean and standard deviation.
  2. *Cold-start indicator flag + neutral defaults:* Add `is_new_account` boolean feature and set deviation features to 0.0 / neutral baseline.
  3. *Minimum transaction threshold:* Require N transactions (e.g. 5 transactions) before computing ratio features; below threshold, assign neutral sentinel value (e.g. 1.0 ratio).
  4. *Hybrid approach:* Combine cold-start indicator with tier-based default priors.

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
