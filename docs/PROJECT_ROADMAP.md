# FinSignal — Project Roadmap

**Project:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Document:** Project Roadmap  
**Scope:** Backend + ML only  
**Status:** Planning / Implementation-Ready  
**Version:** 1.0.0  
**Last Updated:** 2026-10-04

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
- PostgreSQL development environment;
- Docker configuration foundation;
- environment configuration;
- `.env.example`;
- Git conventions;
- base documentation structure;
- initial CI skeleton.

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
- Docker development environment works.

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

---

# 7. Phase 2 — Database & Domain Models

## Objective

Build the persistent domain model.

## Primary Entities

```text
users
accounts
merchants
devices
account_devices
locations
transactions
dataset_versions
dataset_imports
dataset_import_errors
model_versions
risk_analyses
risk_factors
investigations
investigation_transactions
investigation_evidence
ai_summaries
audit_events
```

## Key Tasks

- implement SQLAlchemy models;
- implement migrations;
- define foreign keys;
- define constraints;
- define indexes;
- establish timestamp conventions;
- implement transaction representation;
- implement transfer relationships;
- establish immutable transaction semantics;
- establish audit model.

## Exit Criteria

- clean database migrations succeed;
- domain entities persist correctly;
- foreign keys and constraints work;
- repository tests pass;
- transaction semantics are verified;
- no derived risk data is stored directly on raw transactions.

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
- object-level authorization is enforced;
- security tests pass.

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

## Exit Criteria

- deterministic dataset generation works;
- generated data passes structural validation;
- legitimate unusual events exist;
- fraud scenarios exist;
- ground truth is isolated;
- CSV import works;
- invalid records are reported;
- no silent data loss occurs.

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

## Exit Criteria

- analytics endpoints work;
- calculations are verified against hand-calculated datasets;
- aggregation tests pass;
- temporal boundaries are tested;
- API performance is acceptable at development scale.

---

# 11. Phase 6 — Feature Engineering

## Objective

Transform transaction history into behavior-aware ML features without temporal leakage.

## Feature Groups

### Amount

- amount;
- amount vs account mean;
- amount vs account median;
- amount z-score.

### Velocity

- transactions in last 5 minutes;
- transactions in last hour;
- transactions in last 24 hours.

### Device

- known/new device;
- device frequency.

### Location

- known/new location;
- location frequency;
- distance-related signal where supported.

### Merchant

- merchant frequency;
- new merchant;
- merchant/category deviation.

### Time

- hour;
- day of week;
- weekend;
- unusual hour.

### Behavioral

- spending deviation;
- category spending deviation;
- historical averages.

## Critical Rule

For a transaction at time `T`, only information available at or before `T` may be used.

## Exit Criteria

- feature calculations are deterministic;
- hand-calculated tests pass;
- temporal leakage tests pass;
- future labels cannot enter features;
- feature schema is versioned/documented.

---

# 12. Phase 7 — ML / Anomaly Detection

## Objective

Introduce a baseline unsupervised anomaly-detection model.

## Initial Model

**Isolation Forest**

The baseline must be simple enough to understand, evaluate, and explain.

## Pipeline

```text
Historical Transactions
        ↓
Feature Generation
        ↓
Feature Validation
        ↓
Preprocessing
        ↓
Isolation Forest
        ↓
Anomaly Score
        ↓
Risk Layer
```

## Key Tasks

- model training pipeline;
- feature selection;
- preprocessing;
- model persistence;
- model version metadata;
- deterministic seeds;
- batch inference;
- evaluation pipeline;
- chronological data splits.

## Temporal Split

Example:

```text
January–June → Train
July–August → Validation
September → Test
```

The exact split may be adjusted based on generated dataset dates.

## Exit Criteria

- model trains successfully;
- inference works;
- model is reproducible;
- no ground-truth leakage;
- chronological evaluation works;
- baseline metrics are generated;
- scenario-level evaluation works.

---

# 13. Phase 8 — Risk Analysis & Explainability

## Objective

Convert model outputs and deterministic signals into an interpretable risk assessment.

## Risk Architecture

```text
Deterministic Signals
        +
ML Anomaly Score
        ↓
Hybrid Risk Scoring
        ↓
Risk Level
        ↓
Risk Factors
```

## Risk Levels

```text
LOW
MEDIUM
HIGH
CRITICAL
```

These thresholds are configuration and must be evaluated rather than arbitrarily assumed.

## Risk Factors

Examples:

```text
NEW_DEVICE
NEW_LOCATION
UNUSUAL_TIME
HIGH_VELOCITY
LARGE_AMOUNT_DEVIATION
BEHAVIORAL_SHIFT
```

## Key Tasks

- risk scoring;
- threshold configuration;
- factor generation;
- evidence generation;
- risk-analysis persistence;
- model-version association;
- risk explanation API.

## Exit Criteria

- risk scores are deterministic for fixed inputs;
- risk levels map correctly;
- risk factors correspond to real evidence;
- model version is recorded;
- no risk score is presented as calibrated fraud probability without calibration;
- explainability tests pass.

---

# 14. Phase 9 — Investigation & Evidence

## Objective

Turn suspicious activity into a structured investigation workflow.

## Investigation Lifecycle

```text
OPEN
  ↓
UNDER_REVIEW
  ↓
RESOLVED
```

## Resolutions

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

## Key Tasks

- investigation creation;
- investigation assignment;
- investigation retrieval;
- related transaction linking;
- evidence assembly;
- evidence persistence;
- investigator notes where supported;
- investigation status transitions;
- resolution;
- audit trail.

## Investigation Context

The investigator should be able to access:

```text
Account
  ↓
Transactions
  ↓
Risk Analyses
  ↓
Risk Factors
  ↓
Behavioral Context
  ↓
Related Transactions
  ↓
Evidence
```

## Exit Criteria

- suspicious activity can create investigations;
- investigators can inspect contextual evidence;
- multiple related transactions can be associated;
- invalid state transitions are rejected;
- resolution is authorized and audited;
- original transaction facts remain immutable.

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
