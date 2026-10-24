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
- **Database Migrations:** Alembic (current head: `0003_account_import_namespace`)
- **Authentication & Security:** Argon2id password hashing, Bearer JWT tokens, and centralized role-based access control (`ADMIN`, `ANALYST`, `INVESTIGATOR`)
- **Mathematical Precision:** Python `Decimal` and PostgreSQL `NUMERIC(18,2)` with strict two-decimal `ROUND_HALF_UP` string serialization (`MoneyStr`)

---

## Implementation Status

### Completed Phases (Backend Milestone 1–5)

| Phase | Module | Key Capabilities | Status |
|:---:|---|---|:---:|
| **Phase 1** | Foundation & Tooling | Project scaffold, `uv`, Ruff, mypy, pytest, config management | **Completed** |
| **Phase 2** | Core Operational Schema | 12 canonical tables, Alembic migrations, composite foreign keys, natural keys | **Completed** |
| **Phase 3** | Authentication & Users | User registration, login, JWT issuance/validation, RBAC dependencies | **Completed** |
| **Phase 4** | Synthetic Data & Ingestion | Deterministic PRNG generator (seed 42, 250k transactions, 5k accounts, 7 fraud scenarios), idempotent CSV ingestion, advisory locking, row-level provenance | **Completed** |
| **Phase 5** | Financial Analytics | 6 REST analytics endpoints, PostgreSQL window aggregations, timezone-aware trends, statistical median outliers | **Completed with Documented Benchmark Limitation** |

### Deferred Phases

- **Phase 6 — Feature Engineering:** Point-in-time sliding-window historical features (velocity, deviation, frequency) with strict lookahead-leakage prevention.
- **Phase 7 — Machine Learning Models:** Multivariate anomaly detection (Isolation Forest, supervised benchmark) and continuous risk scoring.
- **Phase 8 — Risk Engine:** Rule-based heuristics, multi-factor risk scoring, and alert generation.
- **Phase 9 — Investigation Workflows:** Human investigation cases, evidence assembly, and resolution lifecycle (`CONFIRMED_FRAUD`, `LEGITIMATE`, `SUSPICIOUS`, `INCONCLUSIVE`).
- **Phase 10 — AI Investigation Assistant:** Grounded, provider-abstracted LLM investigation summaries strictly bounded by structured evidence.
- **Phase 11 — Frontend Dashboard:** React, TypeScript, and Vite user interface.

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

## Verification and Quality Gates

The implementation is verified by an exhaustive automated test suite and strict type-checking:

```bash
# Run complete test suite (320 tests)
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
