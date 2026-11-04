# FinSignal Backend + ML v1.0.0 — Release Notes

**Release Version:** `v1.0.0`  
**Release Date:** 2026-11-04  
**Git Tag:** `v1.0.0`  
**Target Environment:** Python 3.12+, PostgreSQL 16+  

---

## Overview

FinSignal v1.0.0 marks the formal release of the **Financial Transaction Intelligence & Investigation Platform Backend and Machine Learning Engine**. 

Built as a modular monolith in Python and PostgreSQL, FinSignal delivers deterministic financial data ingestion, temporal behavioral feature engineering, unsupervised anomaly detection with Isolation Forest, explainable hybrid risk scoring, structured human-in-the-loop investigation workflows, and grounded AI-assisted briefings.

---

## Key Capabilities

### 1. Financial Data Ingestion & Integrity
- **Canonical Identity & Deduplication:** Deterministic natural key `(source_namespace, account_id, external_transaction_id)` with row-level provenance (`transaction_import_records`).
- **Bounded Resource Limits:** 50 MB bounded streaming upload (`MAX_UPLOAD_SIZE_BYTES = 52_428_800`), chunked 64 KB memory processing, immediate HTTP 413 on payload overflow.
- **Robust Character Handling:** Transparent UTF-8 BOM recovery (`utf-8-sig`) and safe stream detachment preventing premature handle closure.
- **Concurrency Protection:** Transaction-scoped PostgreSQL advisory locks (`pg_try_advisory_xact_lock`) serializing identical simultaneous file uploads.
- **Failure Recovery:** Checkpoint-based resumption of failed or interrupted CSV imports without duplicate record insertion.

### 2. High-Performance Financial Analytics
- **In-Database SQL Aggregations:** Asynchronous single-roundtrip aggregation queries in PostgreSQL without loading raw data into Python process memory.
- **Monetary Precision:** Strict `NUMERIC(18, 2)` decimal semantics with explicit `ROUND_HALF_UP` quantization, completely eliminating binary floating-point representation.
- **Timezone-Aware Trends:** Daily and monthly trend bucketing supporting arbitrary IANA timezones across daylight saving transitions.
- **Outlier Detection:** Non-parametric statistical median and absolute deviation algorithms with deterministic pagination.

### 3. Behavioral Feature Engineering & Zero Temporal Leakage
- **Canonical 34-Feature Vector (`v1.0`):** Fixed schema comprising log-scaled amounts, velocity counts (5m, 1h, 24h), velocity amounts, rolling category averages, and entity familiarity frequencies.
- **Strict Temporal Boundary Enforcement:** Half-open interval queries `occurred_at < eval_t` eliminating lookahead bias and temporal leakage.
- **PostgreSQL Pushdown:** Index-scanned aggregations on `(account_id, occurred_at)` for high-throughput feature context assembly.

### 4. Machine Learning & Anomaly Detection
- **Unsupervised Anomaly Scoring:** Scikit-learn Isolation Forest model with continuous score negation $S(X) = -\text{score\_samples}(X)$.
- **Deterministic Chronological Splitting:** Compound sort key `(occurred_at ASC, _tie_key(id) ASC)` ensuring deterministic train (60%), validation (20%), and test (20%) boundaries.
- **Validation-Only Calibrated Thresholds:** Operating decision thresholds $\tau^*$ tuned exclusively on validation splits subject to a strict 5% alert-rate budget constraint.
- **Model Registry & Governance:** Relational registry (`model_versions`) tracking status (`VALIDATED`, `ACTIVE`, `RETIRED`), hyperparameters, and performance metrics.
- **Artifact Security:** Server-controlled directory storage, strict path containment rejecting directory traversal, and pre-deserialization constant-time SHA-256 verification.

### 5. Explainable Hybrid Risk Scoring
- **Composite Scoring:** Combines normalized ML anomaly signal ($w_{\text{ml}}=0.60$) with deterministic heuristic rule scoring ($w_{\text{rule}}=0.40$).
- **Anchored Normalization:** Piecewise linear scaling anchoring validation score bounds `[score_min, tau*, score_max]` to `[0.0, 50.0, 100.0]`.
- **Heuristic Rule Engine:** 9 deterministic financial risk rules (high velocity, sudden deviation, new device/location, rapid sequence).
- **Structured Rationale:** Four-tier risk classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with human-readable factor descriptions and audit logging.

### 6. Investigation & Evidence Management
- **Shared Triage Queue:** Role-based access control (ADMIN, INVESTIGATOR, ANALYST) with manual case initiation and pessimistic assignment locking.
- **Primary Transaction Invariant:** Relational guarantee binding exactly one primary transaction per investigation.
- **Evidence Immutability:** Polymorphic evidence snapshots (JSONB payload capped at 64 KB) with PostgreSQL database trigger `trg_no_update_delete_audit_events` blocking SQL UPDATE and DELETE operations.
- **Audit Trails:** Immutable audit events captured transactionally across all state transitions.

### 7. Grounded AI Investigation Assistant
- **Advisory Role Boundary:** AI generates objective briefings; all case classifications and resolutions remain human-authoritative.
- **Two-Transaction Isolation:** Snapshots loaded under `REPEATABLE READ` with row-level locks; LLM generation executes strictly outside active database transactions to prevent pool exhaustion.
- **Compare-and-Swap (CAS) Fencing:** Generation tokens ensure late-arriving responses on timed-out or recovered attempts are safely discarded.
- **Dual Fingerprinting & Dynamic Staleness:** SHA-256 `evidence_hash` detects underlying case modifications, flagging stale briefings on retrieval.
- **Grounding Verification:** Validates that every entity UUID cited in the AI briefing exists in the authoritative case context.

### 8. System Security & Hardening
- **CORS Defense:** Strict allowlist with wildcard origin `*` systematically rejected at startup when credentialed authentication is enabled. Correlation tracing header `X-Request-ID` exposed to browsers.
- **Sliding-Window Rate Limiting:** In-memory sliding-window limiter on login endpoints (5 attempts per 60s per IP+email) with atomic in-flight admission control and non-evictable active keys.
- **Namespace Isolation:** Relational composite foreign key `fk_transactions_counterparty_namespace` enforcing identical dataset partition boundaries for counterparties.

---

## Verified Test Suite & Quality Gates

- **Test Suite:** 562 passed tests (0 failed, 0 errors, 0 skipped, ~82s execution time).
- **Static Analysis:**
  - Ruff Linter: 0 errors across codebase.
  - Ruff Formatter: 210 files formatted.
  - Mypy: 0 errors across 199 source files under strict type checking.
- **Database Migrations:** Clean linear chain from baseline `0001_initial_baseline` through `0008_security_hardening`. Roundtrip downgrade-to-base and upgrade-to-head verified on disposable PostgreSQL databases.

---

## Known Operational Boundaries (Deferred to Phase 13)

1. **Docker & Containerization:** Native execution on Python 3.12 and PostgreSQL is verified. Production multi-stage `Dockerfile` and `docker-compose.yml` are scheduled for Phase 13 per ADR-073.
2. **Distributed Rate Limiting:** The login rate limiter operates in-memory per process. Horizontal multi-worker / multi-instance deployments require Redis or distributed state (Phase 13).
3. **Automated Artifact Pruning CLI:** Unreferenced model artifact files from interrupted training runs do not affect inference. Manual cleanup is documented; automated CLI tool is scheduled for Phase 13.
4. **250k Database Ingestion Benchmark:** 250k synthetic dataset generation was verified in Phase 4. Formal 250k-row PostgreSQL ingestion scale run is deferred to Phase 13.
5. **Frontend Interface:** The React/TypeScript web dashboard is scheduled as a subsequent frontend implementation phase.

