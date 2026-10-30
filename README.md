# FinSignal

**Financial Transaction Intelligence & Investigation Platform**

FinSignal is an intelligent financial transaction analysis and investigation platform designed to analyze transaction behavior, identify anomalous or suspicious activity, and assist human investigators with structured contextual evidence.

The platform is designed around the core principle:
> **Detect unusual behavior, provide contextual evidence, explain the signals, and allow a human investigator to make the final decision.**

---

## Architecture & Technology Stack

FinSignal is built as a clean modular monolith adhering to strict domain separation, strong typing, and asynchronous persistence:

- **Language & Runtime:** Python 3.12+ managed with `uv`
- **API Framework:** FastAPI with strict Pydantic v2 schemas (`extra="forbid"`)
- **Database:** PostgreSQL with asynchronous SQLAlchemy 2.0 and `asyncpg`
- **Database Migrations:** Alembic (current head: `0005_intelligence_risk_models`)
- **Authentication & Security:** Argon2id password hashing, Bearer JWT tokens, and centralized role-based access control (`ADMIN`, `ANALYST`, `INVESTIGATOR`)
- **Mathematical Precision:** Python `Decimal` and PostgreSQL `NUMERIC(18,2)` with strict two-decimal `ROUND_HALF_UP` string serialization (`MoneyStr`)

---

## Implementation Status

### Completed Phases (Backend Milestone 1–8)

| Phase | Module | Key Capabilities | Status |
|:---:|---|---|:---:|
| **Phase 1** | Foundation & Tooling | Project scaffold, `uv`, Ruff, mypy, pytest, config management | **Completed** |
| **Phase 2** | Core Operational Schema | 12 canonical tables, Alembic migrations, composite foreign keys, natural keys | **Completed** |
| **Phase 3** | Authentication & Users | User registration, login, JWT issuance/validation, RBAC dependencies | **Completed** |
| **Phase 4** | Synthetic Data & Ingestion | Deterministic PRNG generator (seed 42, 250k transactions, 5k accounts, 7 fraud scenarios), idempotent CSV ingestion, advisory locking, row-level provenance | **Completed** |
| **Phase 5** | Financial Analytics | 6 REST analytics endpoints, PostgreSQL window aggregations, timezone-aware trends, statistical median outliers | **Completed with Documented Benchmark Limitation** |
| **Phase 6** | Feature Engineering | 34-feature point-in-time contract, pure functional engine, O(N log N) streaming batch extraction, zero temporal leakage, live PostgreSQL index-scan aggregation | **Completed with Documented Benchmark Deviation** |
| **Phase 7** | ML / Anomaly Detection | Isolation Forest baseline, canonical 34-feature vector contract (`v1.0`), chronological train/validation/test split, validation-only threshold tuning under 5% alert-rate budget, SHA-256 artifact integrity verification, PostgreSQL model versioning registry | **Completed with Documented Pre-Release Operational Limitation** |
| **Phase 8** | Risk Analysis & Explainability | Deterministic hybrid risk engine ($w_{\text{ml}}=0.60, w_{\text{rule}}=0.40$), validation-anchored piecewise linear score normalization, 9 heuristic rules, 4-tier risk classification, structured factor explainability, idempotent atomic persistence, REST API endpoints | **Completed** |

### Deferred Phases

- **Phase 9 — Investigation Workflows:** Human investigation cases, evidence assembly, and resolution lifecycle (`CONFIRMED_FRAUD`, `LEGITIMATE`, `SUSPICIOUS`, `INCONCLUSIVE`).
- **Phase 10 — AI Investigation Assistant:** Grounded, provider-abstracted LLM investigation summaries strictly bounded by structured evidence.
- **Phase 11 — Frontend Dashboard:** React, TypeScript, and Vite user interface.

---

## Machine Learning Subsystem (Phase 7)

Phase 7 implements unsupervised multivariate anomaly detection, artifact management, and model lifecycle governance (`src/finsignal/ml/`):

- **Canonical 34-Feature Vector (`FeatureVectorizer`):** Transforms Phase 6 `FeatureVector` into 1D/2D IEEE 754 `float64` NumPy arrays adhering strictly to `CANONICAL_FEATURE_NAMES` in fixed order (`FEATURE_VERSION = "v1.0"`). Rejects `NaN`, `Inf`, and missing values at boundary.
- **Isolation Forest Baseline (`IsolationForestModel`):** Wraps `scikit-learn` Isolation Forest with deterministic score negation $S(X) = -\text{score\_samples}(X)$. Higher values indicate greater anomaly severity. Binary anomaly classification is determined by $A(X) = \mathbb{I}(S(X) \ge \tau)$. Anomaly scores represent uncalibrated severity, strictly separated from calibrated fraud probabilities (deferred to Phase 8).
- **Chronological Data Splitter (`ChronologicalSplitter`):** Enforces temporal ordering `(occurred_at, str(record_id))` and partitions datasets into target proportions (60% train, 20% validation, 20% holdout test) while keeping equal-timestamp groups indivisible to prevent lookahead leakage.
- **Validation-Only Threshold Tuning (`ModelEvaluator`):** Selects decision threshold $\tau$ strictly on the validation set to maximize F1 under an operational alert-rate budget constraint ($\text{AlertRate} \le 5.0\%$). Evaluates generalized performance on the untouched holdout test partition.
- **Cryptographic Artifact Integrity (`ModelArtifactStore`):** Manages model serialization with atomic two-phase write (`.tmp` write followed by atomic replace), strict filesystem path-containment checks (`.resolve().relative_to()`), and constant-time SHA-256 digest validation prior to `joblib` deserialization.
- **Database Model Registry & Lifecycle (`ModelRepository`, `MLService`):** Tracks model lifecycle states (`TRAINED`, `VALIDATED`, `ACTIVE`, `DEPRECATED`, `FAILED`) in PostgreSQL `model_versions` table via Alembic migration `0004_model_versions.py`. Enforces a partial unique index ensuring at most one active model per algorithm family, safe transactional row-level promotion locking (`SELECT ... FOR UPDATE`), and in-memory active-model caching verified against database digest.
- **Operational Limitation:** Safe administrative artifact pruning and reconciliation for unreferenced disk artifacts remains an identified pre-release task (unimplemented).

---

## Feature Engineering Subsystem (Phase 6)

Phase 6 provides on-demand, in-memory behavioral feature engineering with strict lookahead-leakage prevention (`src/finsignal/features/`):

- **34 Model Features (`FeatureVector`):** Immutable Pydantic v2 schema (`frozen=True`, `extra="forbid"`) enforcing finite floats (`math.isfinite`):
  - Amount & Log: `amount`, `amount_log` (via `math.log1p`).
  - Account Profile: `account_age_days` (UTC, clamped $\ge 0.0$; `is_account_created_after_txn` reported in `FeatureMetadata`).
  - Velocities: `velocity_5m_count`, `velocity_1h_count`, `velocity_24h_count` (all currencies/directions); `velocity_5m_amount`, `velocity_1h_amount`, `velocity_24h_amount` (direction- and currency-matched).
  - Baselines & Quality: `amount_vs_mean_ratio`, `amount_vs_median_ratio`, `amount_zscore`, `is_amount_different_from_constant_baseline`, `has_direction_baseline`, `has_zero_variance_baseline`, `is_cold_start` (provisional threshold: `MIN_BASELINE_OBSERVATIONS = 3`).
  - Entity Familiarity: `has_device`, `is_new_device`, `device_tx_count`, `has_merchant`, `is_new_merchant`, `merchant_tx_count`, `has_location`, `is_home_location`, `is_new_location`, `location_tx_count`, `location_frequency`.
  - Category Spending: `has_category`, `is_new_category`, `category_spend_share_30d` (preceding 30d DEBIT spend in matching currency).
  - Temporal Behavior: `hour_of_day`, `day_of_week`, `is_weekend`, `is_unusual_hour` (01:00–05:59 UTC).
- **Separation of Diagnostics:** Execution metadata (`FeatureMetadata`) is kept strictly decoupled from model inputs.
- **Dual Pipeline Architecture:**
  - *Online Single Evaluation:* Point-in-time historical context query via async PostgreSQL repository + pure computation engine.
  - *Streaming Batch Extraction:* $O(N \log N)$ chronological extraction using Welford's algorithm and dual heaps without database queries during extraction; preserves caller input collection and guarantees account state isolation.
- **Zero Leakage:** Strictly excludes evaluated transaction from its own baseline and enforces point-in-time eligibility `occurred_at < eval_t OR (occurred_at == eval_t AND id < eval_id)`. Ground truth is never accessed.

---

## Financial Analytics API (Phase 5)

Phase 5 exposes six deterministic financial intelligence endpoints under `/api/v1/analytics/*`:

- `GET /api/v1/analytics/overview`: Platform-wide or filtered macro-metrics (counts, debit/credit volumes, net cash flow, continuous medians, min/max).
- `GET /api/v1/analytics/trends`: Contiguous zero-filled daily or monthly trend buckets in the requested IANA timezone over half-open interval `[from_time, to_time)`.
- `GET /api/v1/analytics/categories`: Directional spending or volume distribution grouped by transaction category with exact percentage share.
- `GET /api/v1/analytics/merchants`: Top merchants ranked by volume (`amount`) or frequency (`count`) with dual percentage calculations (percentage of total debit and percentage of merchant spend).
- `GET /api/v1/analytics/accounts/{account_id}`: Account-specific summary, temporal footprint, active calendar days, top categories, top merchants, and available transacted currencies (authoritatively scoped to `Account.source_namespace`).
- `GET /api/v1/analytics/accounts/{account_id}/unusual-spending`: Deterministic debit outliers exceeding an inclusive multiple of the account's historical debit median ($\text{amount} \ge \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$).

---

## Risk Analysis & Explainability Subsystem (Phase 8)

Phase 8 introduces deterministic hybrid risk scoring and structured explainability (`src/finsignal/risk/`):

- **Validation-Anchored Normalization (`normalize_ml_score`):** Continuous Isolation Forest anomaly scores are mapped into a version-specific $[0.0, 100.0]$ scale using piecewise linear interpolation anchored to empirical bounds ($s_{\min} \mapsto 0.0$, operating threshold $\tau^* \mapsto 50.0$, $s_{\max} \mapsto 100.0$) derived strictly from the validation split during training.
- **Deterministic Heuristic Rules (`RiskRuleEngine`):** 9 rule evaluators generate structured `RiskFactorDTO` records across entity velocity, amount deviation, new device/location/merchant/category indicators, and cold-start accounts, summing into a bounded rule score $[0.0, 100.0]$.
- **Hybrid Scoring Contract (`HybridScoringEngine`):** Linearly combines normalized ML score ($w_{\text{ml}}=0.60$) and rule score ($w_{\text{rule}}=0.40$), with optional evidence-gated escalation floors (`CRITICAL` $\ge 75.0$, `HIGH` $\ge 50.0$) into an investigation prioritization score $[0.00, 100.00]$ mapped to categorical tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Idempotency & Concurrency Governance:** Guaranteed via canonical 64-character SHA-256 feature fingerprints, composite effective configuration hashes (`rc_v1.0#<hash>`), database identity uniqueness constraint `uq_risk_analyses_identity`, and race-safe PostgreSQL unique violation classification (`23505`).
- **Protected REST API:**
  - `GET /api/v1/transactions/{transaction_id}/risk`: Pure historical query returning latest analysis and factors.
  - `POST /api/v1/transactions/{transaction_id}/risk/analyze`: Point-in-time on-demand risk analysis, idempotent reuse, atomic savepoint persistence, and transactional audit event logging (`TRANSACTION_RISK_ANALYZED`). Restricted to `ADMIN`, `ANALYST`, and `INVESTIGATOR`.

---

## Verification and Quality Gates

The implementation is verified by an exhaustive automated test suite and strict type-checking:

```bash
# Run complete test suite (450 tests)
uv run pytest

# Static analysis and linting
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests

# Verify database migrations
uv run alembic current
uv run alembic heads
```

### Performance Benchmarks

#### Analytics Benchmark (Phase 5)
- **Medium Scale (100 accounts, 5,000 transactions, seed=42):**
  - `/overview`: P95 = 0.81 ms (Budget $\le 50.0\text{ ms}$)
  - `/trends`: P95 = 1.53 ms (Budget $\le 50.0\text{ ms}$)
- **Full Scale (5,000 accounts, 250,000 transactions, seed=42, 80,651 matching window rows):**
  - `/categories`: P95 = 85.72 ms (Budget $\le 100\text{ ms}$)
  - `/merchants`: P95 = 83.06 ms (Budget $\le 100\text{ ms}$)
  - `/accounts/{id}`: P95 = 1.25 ms (Budget $\le 100\text{ ms}$)
  - `/accounts/{id}/unusual-spending`: P95 = 0.54 ms (Budget $\le 100\text{ ms}$)
  - `/overview`: P95 = 135.74 ms (Exceeds 100 ms budget due to in-memory sorting of 80k decimal rows for continuous median)
  - `/trends`: P95 = 140.16 ms (Exceeds 100 ms budget due to in-memory hash grouping across 80k decimal rows)
  - Query plan (`EXPLAIN (ANALYZE, BUFFERS)`) confirms `ix_transactions_occurred_at` index scan executes in 28.02 ms.

#### Feature Engineering Benchmark (Phase 6)
- **Medium Scale (100 accounts, 5,000 transactions, seed=42):**
  - Batch extraction (5,000 txs): **0.851 s** (~5,875 tx/sec; Budget $\le 3.0\text{ s}$)
  - Peak memory overhead: **27.82 MB** (Budget $\le 50.0\text{ MB}$)
  - Online single evaluation latency: P50 = 7.23 ms, P90 = 8.51 ms, P95 = 8.84 ms (Exceeds aspirational 5.0 ms budget due to unpooled local asyncpg DB roundtrips in development; pure computation engine executes in $< 50\ \mu\text{s}$)
  - Query plan (`EXPLAIN (ANALYZE, BUFFERS)`) confirms `ix_transactions_account_occurred` index range scan executes in 0.041 ms with 3 shared buffer hits and 0 sequential scans.

#### Machine Learning Anomaly Detection Benchmark (Phase 7)
- **Empirical Results (Local Windows Test Environment, Python 3.12, scikit-learn 1.9.1, AMD Ryzen 7 5800H):**
  - **Feature Vectorization ($N=1,000$):** Mean latency $\approx 7.3\ \mu\text{s}$ per feature vector.
  - **Pure Single-Sample Scoring ($N=200$):** Mean $= 5.09\text{ ms}$, P50 $= 5.01\text{ ms}$, P90 $= 5.46\text{ ms}$, P95 $= 5.92\text{ ms}$, P99 $= 6.57\text{ ms}$ (Satisfies proposed P95 $\le 8.0\text{ ms}$ target for measured environment).
  - **Batch Inference Throughput ($N=10,000$):** Total time $= 48.7\text{ ms}$ ($\approx 205,000\text{ transactions/second}$).
  - **Model Training Throughput ($N=5,000$, 100 trees):** Total time $= 0.12\text{ s}$ ($\approx 41,000\text{ samples/second}$).
  - **End-to-End Single-Sample Scoring ($N=50$):** P95 $= 9.88\text{ ms}$ (includes async database query, point-in-time feature generation, array vectorization, and model inference).
