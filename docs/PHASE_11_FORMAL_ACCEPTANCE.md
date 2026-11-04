# FinSignal — Phase 11 Formal Acceptance Record

**Milestone:** Phase 11 — Testing, Security & Hardening Formal Acceptance  
**Date:** 2026-11-04  
**Status:** COMPLETED & FORMALLY ACCEPTED  
**Commit Reference:** `b2ebaff91799ea7cc0e8151924d9a407c5367b7a`  
**Review Lead:** Senior Backend Architect, Security Reviewer, and ML Engineer  

---

## 1. Executive Summary

Phase 11 (Testing, Security & Hardening) has undergone rigorous, evidence-driven formal technical review and verification. All core architectural invariants, resource limits, security controls, and machine learning governance mechanisms have been verified against source code, relational migrations, and automated tests.

Following the formal engineering review (`PHASE_11_FORMAL_REVIEW_REPORT.md`), targeted security hardening was applied to reject wildcard CORS origins under credentialed authentication, documentation claims regarding login rate limiting were reconciled with the codebase, and all 7 associated architectural decisions were formally ratified.

Phase 11 is hereby **CLOSED AND ACCEPTED**.

---

## 2. Capability Verification Matrix

| Capability Area | Claimed Specification | Implemented Location | Test Coverage & Evidence | Acceptance Status |
|---|---|---|---|:---:|
| **CORS Defense & Origin Isolation** | FastAPI `CORSMiddleware` with explicit allowlist, credential isolation, and exposed `X-Request-ID`. Wildcard `*` strictly forbidden with credentials. | `src/finsignal/main.py`<br>`src/finsignal/core/config.py` | `tests/api/test_cors.py`<br>`tests/unit/test_config.py` | **VERIFIED** |
| **Bounded Streaming Upload** | 50 MB hard limit (`MAX_UPLOAD_SIZE_BYTES = 52_428_800`), chunked 64 KB streaming, immediate HTTP 413 `PayloadTooLargeError`. | `src/finsignal/api/v1/datasets.py`<br>`src/finsignal/dataset/service.py` | `tests/integration/test_datasets_api.py` (`test_upload_dataset_exceeding_max_size_fails_413`) | **VERIFIED** |
| **BOM & CSV Error Handling** | Transparent UTF-8 BOM (`utf-8-sig`), safe stream detachment (`text_stream.detach()`), transaction rollback on `csv.Error` with HTTP 422. | `src/finsignal/api/v1/datasets.py`<br>`src/finsignal/dataset/service.py` | `tests/integration/test_datasets_api.py` (`test_upload_dataset_utf8_bom_success`, `test_upload_dataset_malformed_csv_error_recovery`) | **VERIFIED** |
| **Environment Variable Isolation** | Strips generic `DEBUG` from OS environment (`_FinSignalEnvSettingsSource`), enforces `FINSIGNAL_` prefix while preserving `.env` compatibility. | `src/finsignal/core/config.py` | `tests/unit/test_config.py` (`test_settings_debug_collision_guard`, `test_settings_finsignal_prefix_and_unprefixed_compatibility`) | **VERIFIED** |
| **Sliding-Window Rate Limiter** | Sliding window (5 failed attempts per 60s per IP+email), in-flight attempt reservation bounding burst admission, non-evictable active keys. | `src/finsignal/auth/limiter.py`<br>`src/finsignal/api/v1/auth.py` | `tests/unit/test_auth_rate_limiter.py` (14 tests)<br>`tests/integration/test_auth_endpoints.py` (3 concurrency/rate tests) | **VERIFIED** |
| **Composite Counterparty FK** | Relational composite FK `fk_transactions_counterparty_namespace` on `transactions(counterparty_account_id, source_namespace)` referencing `accounts`. | `migrations/versions/0008_security_hardening.py`<br>`src/finsignal/transactions/models.py` | `tests/integration/test_constraints.py` (`test_transaction_counterparty_namespace_composite_fk`) | **VERIFIED** |
| **Append-Only Audit Immutability** | PostgreSQL trigger `trg_no_update_delete_audit_events` blocking SQL `UPDATE` and `DELETE` on `audit_events`. | `migrations/versions/0008_security_hardening.py` | `tests/integration/test_constraints.py` (`test_audit_events_immutability_trigger`) | **VERIFIED** |
| **Batched Ingestion Lookups** | Single-roundtrip canonical lookups via SQL `tuple_(account_id, external_id).in_(...)` and bounded reference caches. | `src/finsignal/dataset/ingestion/engine.py` | `tests/integration/test_transaction_ingestion.py`<br>`tests/integration/test_datasets_api.py` | **VERIFIED** |
| **Deterministic ML Splitting** | Secondary tie-breaker `(occurred_at ASC, _tie_key(id) ASC)` for identical timestamps preventing split boundary leakage. | `src/finsignal/ml/split.py` | `tests/unit/test_temporal_split.py` | **VERIFIED** |
| **Validation-Only Threshold** | Operating threshold $\tau^*$ tuned exclusively on validation partition subject to 5% alert-rate budget constraint. | `src/finsignal/ml/evaluator.py` | `tests/unit/test_ml_evaluator.py` | **VERIFIED** |
| **Model SHA-256 Integrity** | Pre-deserialization constant-time SHA-256 verification and directory path containment checks. | `src/finsignal/ml/registry.py` | `tests/integration/test_model_repository.py` | **VERIFIED** |

---

## 3. Database Migration Investigation Findings

1. **Linear DAG:** Alembic migrations form an unbroken linear chain from `0001_initial_baseline` through `0008_security_hardening`.
2. **Current Development Database Discrepancy:**
   - In local development environment, `alembic current` reports `0003_account_import_namespace`.
   - Cause: The persistent development database (`finsignal_dev`) was last upgraded in Phase 4. All subsequent phase migrations (0004–0008) were verified via the project's disposable test database harness (`tests/integration/conftest.py`), which spins up ephemeral `finsignal_test_ephem_*` databases, runs `upgrade head`, and drops them after test execution.
   - Per project instructions, `finsignal_dev` was deliberately preserved without unauthorized alteration. Upgrading `finsignal_dev` to head is an authorized operational step for Phase 13.

---

## 4. Associated Architectural Decisions (ADRs)

The following architectural decisions supporting Phase 11 work are formally ratified and accepted:

1. **ADR-065:** Synthetic Dataset Identity & Import Observation Policies — `ACCEPTED`.
2. **ADR-067:** Canonical 34-Feature Vector Contract & Extraction Ordering — `ACCEPTED`.
3. **ADR-068:** Validation-Only Alert-Rate Constrained Threshold Selection — `ACCEPTED`.
4. **ADR-069:** Active Model Dynamic Resolution & Promotion Concurrency — `ACCEPTED`.
5. **ADR-070:** Hybrid Risk Scoring, Validation-Anchored Normalization & Canonical Analysis — `ACCEPTED`.
6. **ADR-071:** Manual Investigation Queue, Primary Transaction Invariant & Evidence Immutability — `ACCEPTED`.
7. **ADR-072:** Two-Phase Synchronous AI Summary Generation, REPEATABLE READ & CAS Fencing — `ACCEPTED`.

---

## 5. Documented Operational Limitations Accepted for v1.0.0

1. **Model Artifact Pruning CLI:** Unreferenced model artifact cleanup CLI (`finsignal-admin prune-unreferenced-artifacts`) is formally deferred to Phase 13 operational tooling per ADR-073. It does not affect inference correctness or security, and safe manual recovery exists.
2. **Performance Benchmarking Scope:** 5,000-row feature extraction, analytics, and ML inference benchmarks are empirical verified. The formal 250k database ingestion benchmark is deferred to Phase 13.
3. **Rate Limiter Deployment Boundary:** Sliding-window login rate limiting is in-memory and per-process. Multi-worker / multi-instance production deployments require Redis-backed distributed rate limiting (scheduled for Phase 13).
4. **Audit Immutability Scope:** PostgreSQL row trigger provides defense-in-depth against application UPDATE/DELETE queries, but does not provide hardware/cryptographic WORM immutability or block superuser TRUNCATE operations.

---

## 6. Formal Acceptance Sign-Off

Phase 11 meets all core functional, security, and verification requirements. The implementation is technically sound, stable, and approved for release finalization in Phase 12.

