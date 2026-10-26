# ML_DESIGN.md

# FinSignal — Machine Learning & Intelligence Design

## 1. Document Purpose

This document defines the machine-learning and analytical intelligence architecture for **FinSignal — Financial Transaction Intelligence & Investigation Platform**.

It translates the product and technical requirements into an implementable ML design covering:

- behavioral feature engineering
- anomaly detection
- risk scoring
- hybrid detection
- temporal correctness
- training/evaluation strategy
- model versioning
- explainability
- investigation integration
- false-positive control
- model lifecycle
- inference boundaries
- leakage prevention
- reproducibility

The central principle is:

> FinSignal should identify unusual behavior and provide evidence for investigation; it should not blindly declare every unusual transaction to be fraud.

---

# 2. ML Objectives

The ML subsystem must help FinSignal answer:

1. Is this transaction unusual relative to the account's historical behavior?
2. Is the account exhibiting a meaningful behavioral change?
3. Are multiple weak signals combining into a stronger anomaly?
4. Which measurable factors contributed to the risk assessment?
5. Which transactions or accounts should receive investigator attention?
6. Can the system provide reproducible and explainable risk results?

The system should optimize for **useful investigation prioritization**, not merely raw classification accuracy.

---

# 3. ML Scope

## 3.1 MVP Scope

The MVP includes:

- behavioral feature engineering
- transaction-level anomaly detection
- account-level behavioral analysis
- unsupervised anomaly detection
- rule-based risk signals
- hybrid risk scoring
- structured risk factors
- time-based evaluation
- model versioning
- scenario-level evaluation
- investigator-facing explanations

The initial ML baseline will use:

```text
Isolation Forest
```

combined with deterministic behavioral signals.

---

## 3.2 Deferred Scope

The following are intentionally deferred:

- deep neural networks
- graph neural networks
- real-time online learning
- reinforcement learning
- autonomous fraud decisions
- large-scale feature stores
- automated model retraining in production
- federated learning
- Kafka-based streaming ML
- complex ensemble stacks
- fully autonomous investigation agents

These may be evaluated only after the MVP demonstrates a measurable need.

---

# 4. Intelligence Architecture

The ML flow is:

```text
Transaction Data
       |
       v
Historical Context
       |
       v
Feature Engineering
       |
       v
Behavioral Features
       |
       +----------------------+
       |                      |
       v                      v
Rule-Based Signals     ML Anomaly Model
       |                      |
       +----------+-----------+
                  |
                  v
            Risk Scoring
                  |
                  v
          Risk Factors
                  |
                  v
       Investigation Trigger
                  |
                  v
        Evidence Assembly
                  |
                  v
            AI Summary
                  |
                  v
        Human Investigation
```

The ML layer therefore supports the investigation workflow rather than replacing it.

---

# 5. Intelligence Layers

FinSignal uses four intelligence layers.

## Layer 1 — Deterministic Signals

Examples:

```text
new device
new location
unusual transaction hour
high transaction velocity
large amount relative to account behavior
rapid spending increase
```

These signals are transparent and directly explainable.

---

## Layer 2 — Behavioral Features

Features describe how the current transaction compares with historical account behavior.

Examples:

```text
amount_vs_account_mean
amount_vs_account_median
amount_zscore
transactions_last_5min
transactions_last_1hour
transactions_last_24hours
merchant_frequency
device_frequency
location_frequency
category_spending_deviation
```

---

## Layer 3 — ML Anomaly Detection

The initial model identifies transactions that appear unusual in feature space.

Primary baseline:

```text
Isolation Forest
```

The model produces an anomaly signal that is normalized into the FinSignal risk-scoring framework.

---

## Layer 4 — Investigation Intelligence

Risk signals and model outputs are assembled into structured evidence.

An LLM may summarize this evidence for investigators.

The LLM does not independently generate the underlying evidence.

---

# 6. Core ML Principle

## Unusual Does Not Mean Fraud

The system must distinguish:

```text
unusual
    !=
fraudulent
```

A transaction can be unusual because of:

- annual insurance
- salary credit
- rent
- travel
- medical expense
- large electronics purchase
- business expense
- holiday spending

Therefore:

> The ML system prioritizes anomalies for review; the investigator determines the final case resolution.

---

# 7. Feature Engineering Architecture

Feature engineering is the foundation of FinSignal's intelligence layer. Features are generated purely in memory or on demand, without persistent feature tables or database migrations.

The feature engineering subsystem is implemented under `src/finsignal/features/` and organized into:

- **`schemas.py`**: Immutable Pydantic v2 schemas (`FeatureVector`, `FeatureMetadata`, DTOs).
- **`constants.py`**: Centralized thresholds and window parameters (`FEATURE_VERSION = "v1.0"`, `MIN_BASELINE_OBSERVATIONS = 3`).
- **`engine.py`**: Pure functional computation engine with zero database dependencies and zero entity mutation.
- **`repository.py`**: Asynchronous SQLAlchemy query layer separating bounded window queries from single-row lifetime aggregates.
- **`service.py`**: Service orchestrating single-transaction online evaluation and $O(N \log N)$ streaming batch feature extraction.

### Core Architectural Boundaries

1. **Separation of Features from Metadata:** `FeatureVector` contains strictly the 34 model input features. Operational diagnostics, account/transaction IDs, and event timestamps are encapsulated in `FeatureMetadata` and never exposed to ML inference models.
2. **Precision & Conversion:** All historical aggregations and monetary velocity sums maintain `Decimal` precision internally and convert to standard `float` only at the `FeatureVector` instantiation boundary.
3. **Finite Floating-Point Validation:** All float features are validated via `@model_validator(mode="after")` to guarantee finite values (`math.isfinite`), strictly forbidding `NaN`, `+Inf`, and `-Inf`.
4. **Strict Point-in-Time Membership:** For any evaluation transaction $T = (t, \text{id})$, candidate historical transactions $H = (t_h, \text{id}_h)$ are strictly eligible if and only if:
   $$t_h < t \quad \text{OR} \quad (t_h = t \text{ AND } \text{id}_h < \text{id})$$
   The evaluated transaction is strictly excluded from its own baselines and velocity counts. Sub-second tie-breaking uses 128-bit unsigned integer ordering (`uuid.int`), matching PostgreSQL B-tree byte comparisons.
5. **Ground-Truth Isolation:** Ground-truth labels (`is_fraud`, `fraud_scenario`) are never referenced, queried, or utilized as feature inputs.
6. **Window Boundaries:** All sliding windows (5m, 1h, 24h, 30d) enforce an **inclusive** lower boundary ($t_h \ge t - \text{window}$) and strict point-in-time upper boundary.

---

# 8. Implemented 34-Feature Contract (Version v1.0)

The approved model input contract comprises exactly 34 features:

### 8.1 Amount Features (2)
- **`amount`** (`float`): Transaction amount converted from Decimal at feature vector boundary.
- **`amount_log`** (`float`): Natural logarithm of amount computed via `math.log1p(amount)`.

### 8.2 Account Profile (1)
- **`account_age_days`** (`float`): Point-in-time age in fractional days ($(t - \text{account.created\_at}) / 86400.0$) using UTC timestamps. Negative ages (e.g. historical data backfills prior to account DB persistence) are clamped to `0.0`. Decoupled `FeatureMetadata.is_account_created_after_txn` flags backfill anomalies. Account age is never used to infer cold-start status.

### 8.3 Transaction Velocity Counts (3)
Evaluated across all directions and currencies within inclusive lower time boundaries:
- **`velocity_5m_count`** (`int`): Count of transactions in preceding 5 minutes ($[t - 300\text{s}, t)$).
- **`velocity_1h_count`** (`int`): Count of transactions in preceding 1 hour ($[t - 3600\text{s}, t)$).
- **`velocity_24h_count`** (`int`): Count of transactions in preceding 24 hours ($[t - 86400\text{s}, t)$).

### 8.4 Transaction Velocity Monetary Amounts (3)
Direction- and currency-matched monetary sums:
- **`velocity_5m_amount`** (`float`): Sum of amounts in preceding 5 minutes matching evaluated transaction direction and currency.
- **`velocity_1h_amount`** (`float`): Sum of amounts in preceding 1 hour matching direction and currency.
- **`velocity_24h_amount`** (`float`): Sum of amounts in preceding 24 hours matching direction and currency.

### 8.5 Amount Deviation & Baseline Quality (7)
Direction- and currency-matched lifetime baselines:
- **`amount_vs_mean_ratio`** (`float`): $\text{amount} / \bar{x}_{\text{hist}}$. Sentinel: `1.0` if history $< 3$ observations.
- **`amount_vs_median_ratio`** (`float`): $\text{amount} / \text{median}_{\text{hist}}$. Sentinel: `1.0` if history $< 3$ observations. Exact median uses arithmetic midpoint for even counts ($\frac{x_{n/2} + x_{n/2+1}}{2}$), matching PostgreSQL's `percentile_cont(0.5)::numeric`.
- **`amount_zscore`** (`float`): Sample z-score $(\text{amount} - \bar{x}_{\text{hist}}) / s_{\text{hist}}$ using sample standard deviation ($N-1$ degrees of freedom). Sentinel: `0.0` if history $< 3$ observations or zero variance.
- **`is_amount_different_from_constant_baseline`** (`int`): When sample variance is zero and history $\ge 3$, set to `1` if $\text{amount} \neq \bar{x}_{\text{hist}}$, else `0`. Sentinel: `0` when baseline is unavailable or variance is nonzero.
- **`has_direction_baseline`** (`int`): `1` if direction/currency history $\ge 3$ observations, else `0`.
- **`has_zero_variance_baseline`** (`int`): `1` if direction/currency history $\ge 3$ and sample variance equals `0.0`, else `0`.
- **`is_cold_start`** (`int`): `1` if account historical transaction count across **all currencies and directions** $< 3$, else `0`. Decoupled from account age.

### 8.6 Device Familiarity (3)
- **`has_device`** (`int`): `1` if `device_id` is present, else `0`.
- **`is_new_device`** (`int`): `1` if `device_id` is present and never observed in prior account history, else `0`.
- **`device_tx_count`** (`int`): Count of strictly prior transactions by the account using this device.

### 8.7 Merchant Familiarity (3)
- **`has_merchant`** (`int`): `1` if `merchant_id` is present, else `0`.
- **`is_new_merchant`** (`int`): `1` if `merchant_id` is present and never observed in prior account history, else `0`.
- **`merchant_tx_count`** (`int`): Count of strictly prior transactions by the account with this merchant.

### 8.8 Location Familiarity (5)
- **`has_location`** (`int`): `1` if `location_id` is present, else `0`.
- **`is_home_location`** (`int`): `1` if `location_id` matches `account.home_location_id` via UUID comparison, else `0`.
- **`is_new_location`** (`int`): `1` if `location_id` is present, does not match `account.home_location_id`, and was never observed in prior history, else `0`. A transaction at the account's registered home location is treated as familiar (`is_new_location = 0`).
- **`location_tx_count`** (`int`): Count of strictly prior transactions by the account at this location.
- **`location_frequency`** (`float`): Ratio $\text{location\_tx\_count} / \text{total\_prior\_txs}$ across all account history. Sentinel: `0.0` if total prior transactions is 0 or location is missing. Bounded in $[0.0, 1.0]$.

### 8.9 Category Behavior (3)
- **`has_category`** (`int`): `1` if `category` is present, else `0`.
- **`is_new_category`** (`int`): `1` if `category` is present and never observed in prior account history, else `0`.
- **`category_spend_share_30d`** (`float`): Ratio of historical DEBIT spending in the evaluated category to total historical DEBIT spending in that currency over the preceding 30 days ($[t - 30\text{d}, t)$). Evaluated regardless of whether the current transaction is DEBIT or CREDIT. Sentinel: `0.0` if category is null or 30-day debit denominator is zero. Bounded in $[0.0, 1.0]$.

### 8.10 Temporal Features (4)
All temporal attributes are evaluated in UTC:
- **`hour_of_day`** (`int`): Hour of transaction (0–23).
- **`day_of_week`** (`int`): Day of week (0=Monday, 6=Sunday).
- **`is_weekend`** (`int`): `1` if Saturday or Sunday, else `0`.
- **`is_unusual_hour`** (`int`): `1` if hour $\in \{1, 2, 3, 4, 5\}$ (01:00–05:59 UTC nocturnality), else `0`.

---

# 9. Explicitly Deferred Features

To keep feature extraction deterministic, performant, and aligned with Phase 6 scope, the following candidate features are explicitly deferred from `v1.0`:
- **`category_amount_mean` & `category_amount_deviation`**: Deferred pending empirical evaluation of category volume stability per account.
- **`device_first_seen_age`**: Deferred; covered effectively by `is_new_device` and `device_tx_count`.
- **Geospatial coordinates & distance**: Deferred until coordinate data is supported by domain models.

---

# 16. Behavioral Baselines

FinSignal should prefer account-relative baselines over global thresholds.

Instead of:

```text
amount > ₹50,000 = suspicious
```

prefer:

```text
amount significantly exceeds this account's normal behavior
```

This is important because:

```text
₹60,000
```

may be:

- normal for a high-spending business-like account
- extremely unusual for a low-spending personal account

---

# 17. Historical Window Strategy

Feature calculations may use multiple historical windows.

Recommended initial windows:

```text
5 minutes
1 hour
24 hours
7 days
30 days
90 days
```

Not every feature requires every window.

For example:

```text
velocity:
5m / 1h / 24h

spending behavior:
7d / 30d / 90d

merchant behavior:
30d / 90d

device behavior:
historical lifetime
```

The final feature set should be driven by measured usefulness rather than maximum feature count.

---

# 18. Temporal Leakage Prevention

This is a hard requirement.

For transaction `T` occurring at timestamp `t`:

features may only use historical information available strictly before `t`, or strictly preceding `T` if multiple transactions share the exact timestamp `t`:

```text
occurred_at < t OR (occurred_at == t AND id < T.id)
```

Information from `occurred_at > t`, or from transaction `T` itself, must not influence the historical feature values for transaction `T`.

The transaction being evaluated is strictly excluded from its own historical baseline context.

This applies to:

- transaction counts
- spending averages
- merchant frequencies
- device frequencies
- location frequencies
- category behavior
- account profiles

---

# 19. Point-in-Time Feature Construction

The canonical conceptual implementation is:

```text
for transaction T (with occurred_at = t):
    historical_context =
        transactions where (occurred_at < t)
                        OR (occurred_at == t AND id < T.id)

    features =
        build_features(T, historical_context)
```

Key invariant:
- The transaction `T` is excluded from its own historical baseline context.
- Historical context evaluation is strictly deterministic across replays.

For production-scale optimization, this can later be replaced by incremental state while preserving the exact same temporal semantics.

The optimized implementation must produce equivalent point-in-time results.

---

# 20. Feature Leakage Prevention

The following must never be used as inference features:

```text
is_fraud
fraud_scenario
scenario_instance_id
investigation_resolution
confirmed_fraud
account_age_days (static CSV precomputed field)
future transactions
future account behavior
post-investigation information
```

`account_age_days` in synthetic source files is a static summary at dataset generation time. Point-in-time account age must always be dynamically derived from:
```text
transaction.occurred_at - account.created_at
```
Using the static CSV column as a feature constitutes temporal leakage.

These fields are ground truth, static generation artifacts, or future information.

Using them would produce artificially strong model performance.

---

# 21. Dataset Splitting

Random train/test splitting is inappropriate as the primary evaluation strategy.

FinSignal should use chronological splitting.

Example:

```text
January - June
        |
      TRAIN

July - August
        |
    VALIDATION

September
        |
      TEST
```

The exact dates depend on the generated dataset.

The important rule is:

> The model must be evaluated on future behavior relative to training data.

---

# 22. Isolation Forest Baseline

## 22.1 Why Isolation Forest

Isolation Forest is appropriate as an initial anomaly-detection baseline because it:

- works without requiring fraud labels
- is relatively simple
- scales reasonably well
- handles high-dimensional numeric features
- identifies isolated observations
- is easy to experiment with
- provides a strong portfolio-friendly baseline

It also matches the initial synthetic dataset strategy where fraud labels exist primarily for evaluation.

## 22.2 Implemented Subsystem Architecture (`finsignal.ml`)

Phase 7 implements the anomaly detection subsystem with explicit separation of responsibilities:

1. **Feature Vectorizer (`FeatureVectorizer`):** Validates schema adherence and converts immutable Phase 6 `FeatureVector` sequences into 2D float64 NumPy matrices of shape `(N, 34)` adhering to canonical ordering.
2. **Model Estimator (`IsolationForestModel`):** Implements the `AnomalyModel` protocol, encapsulating scikit-learn's `IsolationForest` with deterministic seeding (`random_state=42`) and mathematical score negation.
3. **Chronological Data Splitter (`ChronologicalSplitter`):** Groups transactions into indivisible timestamp blocks and cuts partitions targeting 60% Train, 20% Validation, and 20% Holdout Test without lookahead leakage.
4. **Evaluation & Threshold Tuner (`ModelEvaluator`):** Evaluates validation anomaly scores, identifies the optimal decision threshold $\tau^*$ subject to an operational alert-rate budget ($\le 5\%$), and executes single-pass holdout test evaluation.
5. **Artifact Storage (`ModelArtifactStore`):** Persists serialized model binaries (`model.joblib`) and companion JSON metadata with path-traversal validation and two-phase atomic writes. Enforces pre-deserialization SHA-256 integrity verification.
6. **Metadata & Lifecycle Repository (`ModelRepository`):** Manages `model_versions` table persistence, lifecycle state transitions (`EXPERIMENTAL -> VALIDATED -> ACTIVE -> RETIRED`), and row-locked atomic promotion.
7. **Service Facade (`MLService`):** Orchestrates end-to-end model training, active-model resolution, in-memory caching, and transaction anomaly scoring.

### Strict Label Separation
Unsupervised Isolation Forest training is strictly decoupled from ground-truth fraud labels (`is_fraud`). The model fits exclusively on unsupervised feature vectors. Ground-truth labels are ingested solely during validation threshold tuning and holdout test set evaluation. Production inference transactions do not possess ground-truth labels.

---

# 23. Isolation Forest Inputs (Feature Vector v1.0)

The anomaly detection model consumes the validated, immutable 34-feature vector defined in Phase 6, strictly bound to `FEATURE_VERSION = "v1.0"`:

```text
1.  amount
2.  amount_log
3.  account_age_days
4.  velocity_5m_count
5.  velocity_1h_count
6.  velocity_24h_count
7.  velocity_5m_amount
8.  velocity_1h_amount
9.  velocity_24h_amount
10. amount_vs_mean_ratio
11. amount_vs_median_ratio
12. amount_zscore
13. is_amount_different_from_constant_baseline
14. has_direction_baseline
15. has_zero_variance_baseline
16. is_cold_start
17. has_device
18. is_new_device
19. device_tx_count
20. has_merchant
21. is_new_merchant
22. merchant_tx_count
23. has_location
24. is_home_location
25. is_new_location
26. location_tx_count
27. location_frequency
28. has_category
29. is_new_category
30. category_spend_share_30d
31. hour_of_day
32. day_of_week
33. is_weekend
34. is_unusual_hour
```

### Vectorization Rules and Contract Enforcements
- **Canonical Ordering:** Feature extraction order in `FeatureVectorizer.to_numpy()` strictly matches `CANONICAL_FEATURE_NAMES`. Any deviation raises `SchemaValidationError`.
- **Numeric Typing:** All 34 features are converted to `np.float64`. Boolean fields are cast to `1.0` (True) or `0.0` (False).
- **Null and Non-Finite Rejection:** Null (`None`), `NaN`, `+Inf`, and `-Inf` values are forbidden. Pydantic schema validation rejects missing fields at extraction time, and `FeatureVectorizer` asserts finite numerical bounds before training or inference.
- **Metadata Separation:** Diagnostic identifiers (`account_id`, `transaction_id`, `occurred_at`, `calculated_at`) are excluded from model inputs and preserved separately in `FeatureMetadata`.

---

# 24. Model Implementation & Scoring Semantics

### Hyperparameters and Estimator Configuration
The Phase 7 `IsolationForestModel` encapsulates scikit-learn's `IsolationForest` with the following baseline hyperparameters:
- `n_estimators`: 100 decision trees
- `max_samples`: `"auto"` (min(256, n_samples))
- `contamination`: `"auto"` (unsupervised offset calculation)
- `random_state`: 42 (reproducible seed)
- `n_jobs`: `-1` (parallelized tree evaluation)

### Mathematical Score Orientation
Scikit-learn's internal `score_samples(X)` yields the opposite of the standard anomaly score defined in Liu et al. (2008), returning negative numbers where lower/more negative values indicate severe anomalies. FinSignal negates the output to establish an intuitive, monotonic anomaly score:

$$S(X) = - \text{score\_samples}(X)$$

Under this formulation:
- Higher scores signify higher anomalousness (shorter path lengths to isolation).
- Normal transactions cluster around lower values.

### Decision Threshold & Binary Prediction
Given an operating threshold $\tau$, a transaction is classified as anomalous if:

$$A(X) = \mathbb{I}(S(X) \ge \tau)$$

### Score Interpretation and Limitations
Continuous anomaly scores represent empirical tree isolation depth, **not calibrated posterior probabilities of fraud**. A transaction with score $0.72$ is more isolated than one with score $0.45$, but $0.72$ must not be reported as a "72% probability of fraud." Risk calibration and contextual explanation are deferred to the Phase 8 hybrid risk scoring engine.

---

# 25. Chronological Partitioning & Discipline

### Target Partition Proportions
To prevent temporal lookahead leakage, datasets are partitioned strictly chronologically targeting:
- **Train (earliest ~60%):** Unsupervised model fitting without labels.
- **Validation (middle ~20%):** Alert-rate constrained threshold tuning.
- **Holdout Test (latest ~20%):** Single-pass final evaluation.

Because transaction density varies over time and equal-timestamp blocks are kept intact, **60/20/20 represents target proportions**, not guaranteed exact record-count quotas.

### Equal-Timestamp Grouping Semantics
- **Deterministic Sorting:** Transactions are sorted by `(occurred_at, str(record_id))` to ensure stable ordering across runs.
- **Indivisible Timestamp Blocks:** All records sharing the exact same `occurred_at` timestamp are gathered into an indivisible group.
- **Group Boundary Discipline:** Partition boundaries cut strictly between timestamp groups. A timestamp group is never split across train/validation or validation/test boundaries. If adding the next group causes the accumulated count to exceed the target count (`round(n * ratio)`), accumulation halts.
- **Minimum Distinct Timestamps:** Chronological 3-way partitioning requires at least 3 distinct timestamps; datasets with fewer distinct timestamps raise `MLDomainError`.

---

# 26. Feature Versioning

Every model should reference a feature version.

Example:

```text
feature_version = v1.0
model_version = isolation-forest-v1
```

A feature version defines:

- feature names
- feature definitions
- historical windows
- transformations
- missing-value handling
- encoding
- feature ordering

Changing the semantics of a feature requires a new feature version.

---

# 27. Hybrid Risk Scoring

The final FinSignal risk score should not depend exclusively on the anomaly model.

Conceptually:

```text
risk_score =
    weighted(
        ml_anomaly_signal,
        behavioral_signals,
        velocity_signals,
        device_signals,
        location_signals,
        temporal_signals
    )
```

The exact weights must be empirically evaluated.

The initial implementation may use a transparent weighted scoring framework rather than a second opaque ML model.

---

# 28. Example Hybrid Score

Conceptual example:

```text
ML anomaly signal       40%
Behavior deviation      20%
Velocity                15%
New device              10%
New location             5%
Unusual time             5%
New merchant             5%
```

These percentages are **starting hypotheses**, not final production values.

They must be validated against:

- precision
- recall
- PR-AUC
- false-positive rate
- alert volume
- scenario coverage

---

# 29. Risk Score Semantics

The FinSignal risk score is a **prioritization score**, not automatically a probability of fraud.

Example:

```text
0–24    LOW
25–49   MEDIUM
50–74   HIGH
75–100  CRITICAL
```

These thresholds are configurable and should be validated against actual investigation capacity.

A score of:

```text
90
```

does not mean:

```text
90% probability of fraud
```

unless a separately calibrated probability model has been introduced and validated.

---

# 30. Risk Factor Generation

Every high-risk result should produce structured risk factors.

Example:

```text
AMOUNT_ANOMALY
severity = HIGH
value_numeric = 8.7
```

```text
NEW_DEVICE
severity = MEDIUM
```

```text
NEW_LOCATION
severity = HIGH
```

```text
HIGH_VELOCITY
severity = HIGH
value_numeric = 12
```

This structured representation becomes the foundation for:

- investigator UI
- explanations
- investigation evidence
- AI summaries
- model debugging

---

# 31. Multi-Signal Behavior

Single-signal anomalies should not automatically become fraud cases.

For example:

```text
new device
```

may be legitimate.

But:

```text
new device
+
new location
+
unusual hour
+
large amount
+
high velocity
```

represents a substantially stronger investigation signal.

This is why the hybrid design combines multiple contextual signals.

---

# 32. Legitimate Unusual Activity

The evaluation dataset must contain legitimate unusual transactions.

Examples:

```text
salary credit
annual insurance payment
rent
hospital expense
flight booking
hotel booking
large electronics purchase
business expense
holiday spending
```

These examples are essential for evaluating false positives.

A model that flags every large transaction is not considered successful.

---

# 33. Fraud Scenario Evaluation

The dataset includes scenarios such as:

```text
F001 — Large Amount Anomaly
F002 — New Device
F003 — New Location
F004 — Unusual Transaction Time
F005 — High Transaction Velocity
F006 — Account Takeover
F007 — Behavioral Spending Shift
```

The ML system should be evaluated both globally and by scenario.

---

# 34. Scenario-Level Metrics

For each scenario calculate:

```text
precision
recall
F1
PR-AUC where applicable
detection rate
false-positive rate
```

Example evaluation table:

| Scenario | Precision | Recall | F1 | Detection Rate |
|---|---:|---:|---:|---:|
| F001 | ... | ... | ... | ... |
| F002 | ... | ... | ... | ... |
| F003 | ... | ... | ... | ... |
| F004 | ... | ... | ... | ... |
| F005 | ... | ... | ... | ... |
| F006 | ... | ... | ... | ... |
| F007 | ... | ... | ... | ... |

This identifies which behavioral patterns the system handles well or poorly.

---

# 35. Primary Evaluation Metrics

Because fraud/anomaly datasets are imbalanced, accuracy is not a sufficient primary metric.

The main metrics are:

### Precision

```text
TP / (TP + FP)
```

Measures how many flagged transactions were actually relevant.

### Recall

```text
TP / (TP + FN)
```

Measures how many relevant anomalous/fraudulent transactions were detected.

### F1

```text
2 * precision * recall / (precision + recall)
```

Balances precision and recall.

### PR-AUC

Precision-recall area under the curve is particularly useful for imbalanced detection problems.

---

# 36. Operational Metrics

FinSignal must also measure:

```text
alerts_per_1,000_transactions
investigation_queue_size
false_positive_rate
high-risk alert volume
average alerts per account
scenario detection coverage
```

This matters because a model can achieve excellent recall while overwhelming investigators with alerts.

---

# 37. Threshold Selection

Thresholds should be selected using validation data.

The process should consider:

```text
model score distribution
precision
recall
PR-AUC
alert volume
investigator capacity
false-positive cost
false-negative cost
```

The test set must remain untouched during threshold tuning.

---

# 38. Account-Level Detection

Transaction-level detection is not sufficient.

A fraud pattern may consist of several individually moderate transactions.

Therefore FinSignal should evaluate:

```text
transaction-level detection
account-level detection
scenario-instance detection
```

For example:

```text
Account A
  transaction 1 -> moderate anomaly
  transaction 2 -> moderate anomaly
  transaction 3 -> moderate anomaly
```

may collectively represent a significant behavioral shift.

---

# 39. Scenario Instance Detection

Some fraud scenarios span multiple transactions.

The system should therefore retain:

```text
scenario_instance_id
```

in evaluation data.

This enables questions such as:

> Did the system detect the account takeover event at all?

rather than only:

> How many individual transactions were flagged?

---

# 40. Account-Level Aggregation & Phase Boundaries

A future account-level risk score may be derived from transaction results.

Conceptually:

```text
account_risk =
    aggregate(
        recent transaction risks,
        behavioral shift,
        velocity,
        concentration,
        anomaly frequency
    )
```

### 40.1 Subsystem Phase Boundaries
- **Phase 5 (Implemented):** Account unusual-spending detection (`/api/v1/analytics/accounts/{account_id}/unusual-spending`) operates purely as a deterministic statistical outlier filter:
  $$\text{threshold} = \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$$
  flagging debit transactions where $\text{amount} \ge \text{threshold}$ within the requested reporting window. It does **not** employ a machine learning model or multivariate feature weights.
- **Phase 6 (Implemented):** Point-in-time temporal and behavioral feature engineering producing the validated 34-feature `FeatureVector` under `FEATURE_VERSION = "v1.0"` with strict half-open window intervals $[t - \Delta, t)$ to prevent lookahead leakage.
- **Phase 7 (Implemented):** Unsupervised multivariate anomaly detection via `IsolationForestModel`, extracting canonical 34-feature matrices, performing chronological partitioning with timestamp grouping, optimizing decision thresholds on validation data under an operational alert-rate budget ($\le 5\%$), and verifying artifact SHA-256 integrity.
- **Phase 8 (Deferred / Out of Scope):** Hybrid risk scoring combining anomaly scores with deterministic financial heuristics into a normalized 0–100 composite risk score, classifying risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), generating explainable risk factors, and driving automated investigation workflows.

### 40.2 Validation-Only Alert-Rate Constrained Threshold Tuning
Because unsupervised Isolation Forest anomaly scores $S(X) = - \text{score\_samples}(X)$ are uncalibrated, FinSignal utilizes validation split scenario labels to select an optimal operating threshold $\tau^*$:

1. **Constrained Objective:**
   $$\tau^* = \arg\max_{\tau : \text{alert\_rate}(\tau) \le \text{max\_alert\_rate}} F_1(\tau)$$
   where the default $\text{max\_alert\_rate} = 0.05$ (5% alert budget).
2. **Candidate Thresholds & Boundary Semantics:**
   Candidate thresholds evaluated by `ModelEvaluator.tune_threshold()` consist of all unique validation anomaly scores plus an upper boundary candidate `max_score + 1e-6`.
   - Because `max_score + 1e-6` strictly exceeds all observed scores, it produces zero alerts ($\text{alert\_rate} = 0.0$).
   - For any valid non-negative alert rate budget ($\text{max\_alert\_rate} \ge 0.0$), this boundary candidate satisfies the budget constraint ($0.0 \le \text{max\_alert\_rate}$), ensuring that an operating threshold is always deterministically found (yielding $F_1 = 0.0$ if no positive alerts fall within budget).
3. **Conservative Tie-Breaking:**
   When multiple candidate thresholds yield the same maximum F1 score within budget, the algorithm selects the higher threshold (more conservative, producing fewer or equal alerts).
4. **Single-Pass Holdout Test Evaluation:**
   Once $\tau^*$ is selected, the finalized model and threshold are evaluated exactly once over the sealed holdout test split. The evaluator computes:
   - Confusion matrix counts ($TP, FP, TN, FN$) and alert rate
   - Precision, Recall, and $F_1$ score
   - Area Under the Precision-Recall Curve (PR-AUC / Average Precision)
   - Scenario-specific recall for each fraud scenario code (e.g. F001–F007)
   - Cluster / scenario-instance recall evaluating whether grouped fraud patterns were detected

---

# 41. Investigation Triggering

Not every anomalous transaction should automatically create an investigation.

Risk scoring evaluates transactions; investigation triggering is an application-level workflow policy that operates on the resulting `risk_analyses`.

A trigger policy may consider:

```text
risk_score
risk_level
multiple risk factors
recent account alert history
scenario severity
```

Default policy:

```text
CRITICAL
    -> automatically create investigation (if auto-trigger enabled)

HIGH
    -> auto-trigger depending on server-side configured threshold

MEDIUM
    -> retain for manual analyst triage and review

LOW
    -> no investigation
```

### Trigger Policy Mechanism

The trigger policy is managed as server-side application configuration (e.g. typed application settings loaded from environment or config files). It does not require a complex runtime admin API for MVP.

Configuration keys include:
- `INVESTIGATION_AUTO_TRIGGER_ENABLED`: boolean flag to enable/disable automated creation
- `INVESTIGATION_TRIGGER_MIN_LEVEL`: minimum risk level for auto-triggering (e.g. HIGH or CRITICAL)
- `INVESTIGATION_TRIGGER_HIGH_SCORE_THRESHOLD`: numeric threshold (0–100) above which HIGH transactions trigger an investigation

This separation ensures risk scoring remains a deterministic calculation, while workflow automation remains configurable and testable.

---

# 42. Risk Result Persistence

The persistence chain is:

```text
Transaction
    |
    v
Risk Analysis
    |
    +---- Risk Factor
    +---- Risk Factor
    +---- Risk Factor
```

A transaction may have multiple risk analyses over its lifetime because different model versions may evaluate it.

This enables:

```text
model comparison
reprocessing
historical reproducibility
```

---

# 43. Model Versioning

A model version must identify at minimum:

```text
model name
model version
algorithm
feature version
training dataset version
parameters
evaluation metrics
artifact reference
lifecycle status
```

Example:

```text
name:
transaction-anomaly

version:
1.0.0

algorithm:
IsolationForest

feature_version:
1.0

dataset_version:
synthetic-2026-10-v1
```

---

# 44. Model Lifecycle

Model states:

```text
EXPERIMENTAL
     |
     v
VALIDATED
     |
     v
ACTIVE
     |
     v
RETIRED
```

Only an `ACTIVE` model should be used for normal production inference.

A model must not become active solely because it has a higher aggregate metric.

Operational and scenario-level behavior must also be reviewed.

---

# 45. Reproducibility

A model result should be reproducible using:

```text
dataset version
feature version
model version
model parameters
preprocessing configuration
random seed where applicable
```

The goal is to make it possible to answer:

> Why did this transaction receive this risk result?

without relying on undocumented state.

---

# 46. Training Pipeline

Conceptual pipeline:

```text
Dataset
   |
   v
Validation
   |
   v
Temporal Split
   |
   v
Historical Feature Generation
   |
   v
Feature Validation
   |
   v
Preprocessing
   |
   v
Model Training
   |
   v
Validation Evaluation
   |
   v
Threshold Selection
   |
   v
Scenario Evaluation
   |
   v
Model Registration
```

Training should never use the test period for model selection.

---

# 47. Test Set Protection

The final test period should be treated as an evaluation boundary.

Do not use it to:

- tune model hyperparameters
- choose thresholds
- select features
- adjust weights
- decide model architecture

Otherwise the test set becomes part of training indirectly.

---

# 48. Hyperparameter Strategy

The initial Isolation Forest experiment may evaluate:

```text
n_estimators
max_samples
contamination
max_features
random_state
```

The exact search space should remain small.

The project goal is not to perform unlimited hyperparameter optimization.

The goal is to establish:

```text
baseline
measurement
iteration
```

---

# 49. Contamination Parameter

Isolation Forest's contamination setting must be treated carefully.

The synthetic dataset has an approximate fraud rate, but:

```text
fraud rate != anomaly rate
```

A legitimate unusual transaction may be anomalous without being fraud.

Therefore contamination should not blindly equal:

```text
3% fraud
```

It should be treated as a model hyperparameter selected using validation behavior.

---

---

## 49.1 Model Artifact Storage, Serialization & Known Limitations

### Directory Layout & Relative URI Contract
Model artifacts are stored in an isolated filesystem root controlled by `settings.model_artifacts_dir`:
```text
{model_artifacts_dir}/
  └── {model_id}/
        ├── model.joblib      # Serialized IsolationForestModel instance
        └── metadata.json     # Companion metadata (model_id, sha256_hash, feature_version, params, timestamp)
```
The database records the relative artifact path `model_versions.artifact_uri = "{model_id}/model.joblib"`.

### Two-Phase Atomic Serialization
To guard against partial writes:
1. `joblib.dump()` writes the fitted model to a temporary file: `model.{random_hex}.tmp`.
2. The SHA-256 cryptographic digest of the complete serialized file is calculated.
3. The temporary file is atomically renamed to `model.joblib` via `os.replace()`.
4. Companion `metadata.json` is persisted alongside the artifact.

### Pre-Deserialization Integrity Check
Before invoking `joblib.load()`:
1. The target path is verified against path-traversal attacks via `.resolve().relative_to(base_dir)`.
2. The file bytes are streamed, and their SHA-256 digest is computed.
3. The computed digest is compared against `model_versions.artifact_hash` using constant-time comparison.
4. Any mismatch immediately aborts deserialization and raises `ModelIntegrityError`.

### Known Operational Limitation (Unreferenced Artifact Orphans)
- **Failure Mode:** Disk persistence occurs before database transaction commitment in `MLService.train_and_register()`. If database insertion, constraint verification, or connection commit fails, an unreferenced artifact directory remains on disk.
- **Handling Rationale:** Deleting artifacts in client-side exception handlers was deliberately rejected due to commit ambiguity (e.g., if a commit succeeded on the database server but the network dropped before the client received the acknowledgement, client-side deletion would destroy a valid active model).
- **Proposed Pre-Release Task:** An administrative pruning and reconciliation tool (`finsignal-admin prune-unreferenced-artifacts`) is proposed as a required operational task before production release to detect and clean unreferenced artifact directories. This tool is **unimplemented** in Phase 7.

---

# 50. Feature Importance and Explainability

Isolation Forest does not provide traditional supervised feature coefficients.

FinSignal should therefore explain results using:

1. deterministic behavioral signals
2. feature deviations
3. risk factors
4. model score
5. historical comparisons

Example explanation:

```text
Transaction amount was 8.4× the account's
30-day median transaction amount.

The transaction occurred from a device
not previously associated with this account.

Five transactions occurred within the
previous 15 minutes.
```

This is more useful to an investigator than simply saying:

```text
Model score: 0.93
```

## 50.1 Model Lifecycle, Active Model Resolution & Caching

### Model Lifecycle State Machine
Model versions stored in `model_versions` transition through strict lifecycle states:
- `EXPERIMENTAL` $\to$ `VALIDATED` (upon passing validation threshold tuning and test evaluation), or `RETIRED`.
- `VALIDATED` $\to$ `ACTIVE` (via atomic promotion), or `RETIRED`.
- `ACTIVE` $\to$ `RETIRED` (upon subsequent model promotion or deprecation).
- `RETIRED` $\to$ Terminal state; no further transitions permitted.

### Active Model Resolution & In-Memory Caching
- **PostgreSQL Source of Truth:** `MLService.score_transaction()` resolves the active model dynamically by querying PostgreSQL (`WHERE name = :name AND status = 'ACTIVE'`) using the caller's session.
- **In-Memory Cache Validation:** An in-memory cache dictionary `_model_cache` local to the `MLService` instance maps `model_id -> (artifact_hash, IsolationForestModel, threshold)`. If `model.id` exists in the local cache and `cached[0] == model.artifact_hash`, the in-memory estimator is reused. If not cached or if the artifact hash differs, the artifact is loaded from disk with SHA-256 verification.
- **Process Scope:** In multi-worker deployments, each worker process maintains an independent local in-memory cache. Read Committed database isolation ensures that newly committed active models become visible on each worker's subsequent query.

### Promotion Concurrency & Limitations
- **Row-Level Locking:** `ModelRepository.promote_to_active()` acquires `SELECT ... FOR UPDATE` locks on both the candidate model and the currently active model within a single database transaction.
- **Atomic Deactivation:** The current active model is transitioned to `RETIRED` and flushed before promoting the candidate to `ACTIVE`.
- **Database Index Constraint:** The PostgreSQL partial unique index `uq_model_versions_active_family` (`CREATE UNIQUE INDEX ... WHERE status = 'ACTIVE'`) enforces at the database engine level that at most one model per family may be active.
- **Concurrency Testing Scope:** Atomic promotion and partial unique index collision handling are verified by automated tests (`test_model_repository.py`). Concurrent multi-session promotion under race contention remains unverified with concurrent stress fixtures.

---

# 51. Explanation Boundary

The system must distinguish:

### Evidence

Measured facts:

```text
amount = ₹75,000
account median = ₹2,100
new_device = true
transactions_last_15min = 6
```

### Interpretation

Derived statement:

```text
This transaction is significantly outside
the account's historical spending pattern.
```

### AI Summary

Natural-language synthesis:

```text
The transaction shows several deviations...
```

The AI summary must never be treated as the original evidence.

## 51.1 Empirical Benchmark Methodology, Environment Scope & Observed Measurements

Performance benchmarks implemented in [`tests/integration/test_ml_benchmark.py`](file:///d:/PROJECTS/FinSignal/tests/integration/test_ml_benchmark.py) evaluate Phase 7 latency, throughput, and resource utilization under controlled test harnesses:

### Benchmark Methodology & Harness Details
1. **Feature Vectorization Latency (`test_benchmark_vectorization_latency`):**
   - Sample size: $N = 1,000$ dummy `FeatureVector` instances.
   - Warm-up: None. Garbage collection: Uncontrolled.
   - Measurement: `time.perf_counter()` timing `FeatureVectorizer.to_numpy()`.
   - Result: $\approx 7.3\ \mu\text{s}$ per feature vector.
2. **Pure Single-Sample Scoring Latency (`test_benchmark_pure_model_scoring`):**
   - Model: `IsolationForestModel` fitted on $N = 1,000$ synthetic transactions (34 features).
   - Sample size: $N = 200$ individual calls scoring a single sample `(1, 34)` via `model.score_samples()`.
   - Warm-up: None. Garbage collection: Uncontrolled.
   - Percentile calculation: NumPy default `np.percentile`.
   - Results: P50 $\approx 5.30$ ms, P90 $\approx 5.75$ ms, P95 $\approx 5.92$ ms (earlier run $6.26$ ms).
3. **Pure Batch Scoring Throughput (`test_benchmark_pure_model_scoring`):**
   - Input: $N = 10,000$ feature rows `(10000, 34)` evaluated in a single call.
   - Result: $\approx 205,302$ transactions/second.
4. **Model Training Latency (`test_benchmark_training_duration`):**
   - Sample size: $N = 5,000$ transactions, 100 decision trees.
   - Result: $\approx 0.12$ seconds.
5. **End-to-End Online Scoring Latency (`test_benchmark_end_to_end_inference_latency`):**
   - Pipeline: Complete invocation of `service.score_transaction()` including PostgreSQL active-model lookup, feature extraction (`FeatureService`), vectorization, and scoring.
   - Warm-up: Exactly 1 warm-up scoring call to prime the in-memory cache.
   - Sample size: $N = 50$ real synthetic transactions evaluated sequentially.
   - Results: P50 $\approx 8.7$ ms, P90 $\approx 9.5$ ms, P95 $\approx 9.88$ ms.

### Benchmark Scope & Proposed Target
- **Proposed Target:** The project owner is reviewing a proposed pure single-sample scoring target of **P95 $\le 8.0$ ms** for the measured local Windows/Python 3.12 development environment.
- **Environment Scope:** All reported metrics were observed on a local development workstation running Windows and Python 3.12 with local PostgreSQL. They are empirical observations under test conditions, not hardware-independent service-level agreements (SLAs).

---

# 52. LLM Integration

The LLM receives structured investigation context.

Conceptually:

```text
Investigation
+
Transactions
+
Risk Factors
+
Behavioral Comparisons
+
Evidence
```

becomes:

```text
LLM input
```

The LLM produces:

```text
investigation summary
key observations
supporting evidence
uncertainties
recommended review points
```

It does not produce the final fraud decision.

---

# 53. LLM Safety Constraints

The LLM must:

- use only supplied evidence
- distinguish facts from interpretations
- avoid inventing transactions
- avoid inventing merchants
- avoid inventing locations
- avoid inventing model results
- avoid claiming certainty unsupported by evidence
- explicitly acknowledge missing information

Example:

```text
Evidence indicates...
```

is preferable to:

```text
This transaction is definitely fraudulent.
```

---

# 54. Provider Abstraction

The ML/AI layer should not hard-code the application to a single LLM provider.

Conceptual interface:

```text
InvestigationSummaryProvider
```

Possible implementations:

```text
OpenAIProvider
AnthropicProvider
LocalModelProvider
MockProvider
```

The actual provider selected for the MVP remains an implementation decision.

---

# 55. AI Output Persistence

AI-generated summaries are stored separately from investigations.

This permits:

- regeneration
- provider comparison
- prompt versioning
- historical review
- failure tracking

An AI summary must never overwrite investigator notes or resolution.

---

# 56. Failure Handling

ML failures must not corrupt transaction data.

If inference fails:

```text
transaction remains persisted
risk analysis may be marked FAILED
investigation creation is skipped or retried
```

If AI generation fails:

```text
investigation remains available
evidence remains available
AI summary becomes FAILED
human investigation continues
```

AI is therefore an enhancement layer rather than a system dependency for financial-data integrity.

---

# 57. Batch Processing

The MVP may process transactions in batches.

Conceptual flow:

```text
load transactions
      |
      v
sort by occurred_at
      |
      v
generate point-in-time features
      |
      v
apply preprocessing
      |
      v
run model
      |
      v
persist risk analyses
```

Batch size should be configurable.

---

# 58. Inference Ordering

For historical batch inference, transaction ordering should be deterministic.

Recommended ordering:

```text
occurred_at ASC
id ASC
```

The secondary identifier is important when multiple transactions have identical timestamps.

This prevents ambiguous feature state.

---

# 59. Duplicate Timestamps

Multiple transactions may share the same `occurred_at`.

The ML pipeline must therefore define a deterministic tie-breaking rule.

For example:

```text
ORDER BY occurred_at ASC, id ASC
```

When strict event-boundary semantics are required, the feature-generation process must respect this same ordering.

---

# 60. Feature Pipeline Architecture

The feature pipeline should be modular.

Conceptually:

```text
FeaturePipeline
    |
    +-- AmountFeatures
    +-- VelocityFeatures
    +-- MerchantFeatures
    +-- DeviceFeatures
    +-- LocationFeatures
    +-- TemporalFeatures
    +-- CategoryFeatures
    +-- AccountBehaviorFeatures
```

Each component should have:

- clear inputs
- clear outputs
- deterministic behavior
- tests
- versioning

---

# 61. Feature Registry

The project should maintain a machine-readable or documented registry of features.

Example:

| Feature | Type | Window | Leakage Risk | Description |
|---|---|---|---|---|
| `amount_log` | Numeric | Current | Low | Log-transformed amount |
| `amount_zscore` | Numeric | Historical | High | Amount deviation |
| `transactions_last_1h` | Numeric | 1h | High | Recent transaction count |
| `is_new_device` | Boolean | Lifetime | High | Device unseen previously |
| `is_unusual_hour` | Boolean | Historical | High | Time outside normal pattern |

This registry becomes part of the feature version.

---

# 62. Data Quality Before ML

No ML model should run blindly on invalid data.

Required preconditions include:

```text
valid account reference
valid timestamp
valid amount
valid currency
valid transaction type
valid categorical values
```

Malformed records should be rejected or isolated during ingestion.

---

# 63. Outlier Handling

Extreme values should not automatically be removed.

In financial anomaly detection, extreme values may be exactly what the model needs to detect.

Therefore:

```text
outlier = potential signal
```

rather than:

```text
outlier = automatically invalid
```

Invalid values should be handled during data validation, while legitimate extreme transactions remain available to the ML pipeline.

---

# 64. Class Imbalance

The dataset intentionally contains approximately:

```text
3% fraud
97% non-fraud
```

This means raw accuracy can be misleading.

For example:

```text
97% accuracy
```

could theoretically be achieved by predicting everything as non-fraud.

Therefore evaluation must emphasize:

```text
precision
recall
F1
PR-AUC
false-positive rate
alert volume
```

---

# 65. Baseline Comparisons

The Isolation Forest model should be compared against simple baselines.

Possible baselines:

### Baseline A — Amount Rule

```text
flag if amount exceeds account threshold
```

### Baseline B — Z-Score Rule

```text
flag if amount_zscore > threshold
```

### Baseline C — Rule-Based Hybrid

```text
weighted behavioral signals
```

### Baseline D — Isolation Forest

```text
unsupervised anomaly model
```

This determines whether ML actually adds value beyond straightforward behavioral rules.

---

# 66. Ablation Testing

Feature groups should be tested independently.

Example:

```text
all features
      vs
remove device features
      vs
remove location features
      vs
remove temporal features
      vs
remove velocity features
```

This helps determine which signals actually contribute to detection.

---

# 67. Model Monitoring

Even though full production model monitoring is deferred, the architecture should support measuring:

```text
score distribution
risk-level distribution
alert volume
feature distribution
missing-value rates
scenario detection
false-positive rate
```

Significant changes may indicate:

- data drift
- behavior drift
- ingestion problems
- model degradation

---

# 68. Data Drift

Potential drift indicators include:

```text
mean transaction amount
transaction frequency
category distribution
device distribution
location distribution
risk-score distribution
```

Drift monitoring is initially analytical rather than fully automated.

---

# 69. Model Drift

Model performance should be periodically evaluated when labeled outcomes become available.

Metrics include:

```text
precision
recall
F1
PR-AUC
false-positive rate
alert volume
scenario-level recall
```

A model should not be retrained merely because time has passed.

Retraining should be driven by measured degradation or meaningful data changes.

---

# 70. Human Feedback Loop

Investigation outcomes provide valuable feedback.

Example:

```text
model flags transaction
       |
       v
investigator reviews
       |
       v
LEGITIMATE / SUSPICIOUS / CONFIRMED_FRAUD
```

These outcomes may later support supervised learning.

However, the MVP should not automatically feed investigator decisions back into model training without a controlled dataset-building process.

---

# 71. Future Supervised Learning

Once enough reliable investigation outcomes exist, the project may evaluate:

```text
Logistic Regression
Random Forest
Gradient Boosting
XGBoost / LightGBM
```

The selection must be based on measured performance and explainability rather than algorithm popularity.

A supervised fraud classifier would require careful label-quality analysis.

---

# 72. Graph Intelligence

The database already supports relationships that can later support graph analysis:

```text
account -> device
account -> merchant
account -> location
account -> account
```

Potential future graph signals:

```text
shared device count
shared merchant networks
transfer communities
account clusters
rapid money movement paths
```

Graph ML is intentionally deferred.

---

# 73. RAG and Historical Investigation Knowledge

A future retrieval system could provide investigators with:

```text
similar historical cases
investigation procedures
policy documents
prior resolved patterns
```

This is not required for the initial ML subsystem.

If introduced, retrieved documents must remain distinct from transaction evidence.

---

# 74. Security and Privacy

ML pipelines must follow the same data minimization principles as the application.

Do not train models on:

- passwords
- authentication secrets
- unnecessary personal identifiers
- raw sensitive data that is not needed for the task

Synthetic data is preferred for development.

---

# 75. Reproducible Experiments

Every experiment should record:

```text
dataset version
feature version
model version
parameters
random seed
evaluation period
metrics
threshold
```

An experiment without these details should not be considered reproducible.

---

# 76. Experiment Tracking

A lightweight experiment record can initially be stored as:

```text
JSON/Markdown
```

or model metadata.

A dedicated experiment tracking platform such as MLflow is intentionally deferred.

The project should first establish disciplined experiment metadata before introducing additional infrastructure.

---

# 77. ML Artifact Management

Model artifacts should not be committed blindly into Git.

Preferred structure:

```text
model metadata
    +
artifact URI/reference
    +
SHA-256 artifact hash
```

For the MVP, local artifact storage may be sufficient.

### Artifact Integrity Verification

Model artifacts must be cryptographically verified prior to loading:
- When saving a newly trained model version, compute its SHA-256 hash and persist it in `model_versions.artifact_hash`.
- When loading an artifact for inference, re-calculate the SHA-256 digest of the artifact file and compare it against `model_versions.artifact_hash`.
- If the hash mismatches or is absent, the loader must reject the artifact with a controlled `ModelIntegrityError`.

Future deployment can use:

- object storage
- model registry
- MLflow
- cloud artifact storage

---

# 78. Performance Targets

The MVP should prioritize correctness over extreme inference latency.

Target considerations:

```text
batch inference:
acceptable for development-scale datasets

single transaction inference:
fast enough for interactive investigation workflows
```

The exact latency target should be measured after implementation rather than guessed prematurely.

---

# 79. ML Testing Strategy

Tests should cover:

### Feature Tests

- amount features
- velocity features
- temporal features
- device features
- location features
- merchant features

### Leakage Tests

- future transactions excluded
- future timestamps excluded
- fraud labels excluded
- investigation outcomes excluded

### Model Tests

- deterministic training where configured
- expected output range
- model artifact loading
- inference compatibility

### Risk Tests

- score normalization
- threshold mapping
- risk-level assignment
- risk-factor generation

### Integration Tests

- transaction → feature → model → risk analysis
- risk analysis → investigation trigger
- investigation → evidence
- evidence → AI summary

---

# 80. Determinism

The ML pipeline should be deterministic wherever practical.

Set explicit random seeds for:

```text
dataset generation
train/validation processing
Isolation Forest
```

When non-determinism is unavoidable, record it as part of experiment metadata.

---

# 81. Explainability Requirements

Every flagged transaction should have enough structured information to answer:

```text
Why was this transaction flagged?
```

At minimum:

```text
risk score
risk level
model version
risk factors
key behavioral deviations
```

An investigator should not need to inspect model internals to understand the basic reason for an alert.

---

# 82. Risk Factor Quality

Risk factors should be:

### Specific

Bad:

```text
Suspicious behavior
```

Better:

```text
Transaction amount is 7.8× the account's 30-day median.
```

### Measurable

Whenever possible, include:

```text
observed value
baseline value
deviation
time window
```

### Traceable

A factor should be reproducible from transaction/account data.

---

# 83. Example Investigation Context

A structured investigation context might contain:

```json
{
  "transaction": {
    "amount": 75000,
    "occurred_at": "2026-09-14T02:17:00Z"
  },
  "risk": {
    "score": 91.4,
    "risk_level": "CRITICAL"
  },
  "factors": [
    {
      "code": "AMOUNT_ANOMALY",
      "severity": "HIGH",
      "value": "7.8x account median"
    },
    {
      "code": "NEW_DEVICE",
      "severity": "HIGH"
    },
    {
      "code": "UNUSUAL_TIME",
      "severity": "MEDIUM"
    }
  ]
}
```

The LLM should summarize this context rather than invent additional facts.

---

# 84. Recommended ML Module Structure

A possible backend structure:

```text
app/
└── intelligence/
    ├── features/
    │   ├── amount.py
    │   ├── velocity.py
    │   ├── merchant.py
    │   ├── device.py
    │   ├── location.py
    │   ├── temporal.py
    │   └── account_behavior.py
    │
    ├── preprocessing/
    │   └── pipeline.py
    │
    ├── models/
    │   ├── base.py
    │   └── isolation_forest.py
    │
    ├── scoring/
    │   ├── hybrid_score.py
    │   └── risk_levels.py
    │
    ├── explanations/
    │   └── risk_factors.py
    │
    ├── evaluation/
    │   ├── metrics.py
    │   ├── scenarios.py
    │   └── temporal_split.py
    │
    └── ai/
        ├── provider.py
        └── investigation_summary.py
```

The exact package structure may evolve during implementation.

---

# 85. Separation of Responsibilities

### Feature Layer

Responsible for:

```text
raw data -> behavioral features
```

### Model Layer

Responsible for:

```text
features -> anomaly signal
```

### Scoring Layer

Responsible for:

```text
signals -> normalized risk score
```

### Explanation Layer

Responsible for:

```text
signals -> structured risk factors
```

### Investigation Layer

Responsible for:

```text
risk -> case workflow
```

### AI Layer

Responsible for:

```text
structured evidence -> natural-language summary
```

No layer should silently take responsibility for another layer.

---

# 86. Anti-Patterns to Avoid

Do not:

- train directly on fraud labels and call the result anomaly detection
- randomly split time-series transaction data
- use future transactions in historical features
- treat every large transaction as fraud
- persist every feature without justification
- make the LLM the fraud detector
- store risk scores directly on the transaction record
- tune thresholds on the final test set
- optimize only for accuracy
- create Kafka/MLflow infrastructure before it is needed
- hide model behavior behind an unexplained score

---

# 87. MVP ML Implementation Sequence

Recommended order:

```text
1. Dataset validation
        ↓
2. Temporal ordering
        ↓
3. Historical feature engine
        ↓
4. Feature tests
        ↓
5. Baseline rule detector
        ↓
6. Isolation Forest
        ↓
7. Risk-score normalization
        ↓
8. Risk-factor generation
        ↓
9. Temporal evaluation
        ↓
10. Scenario evaluation
        ↓
11. Persistence integration
        ↓
12. Investigation triggering
        ↓
13. Evidence assembly
        ↓
14. LLM summary integration
```

This sequence reduces debugging complexity.

---

# 88. ML Acceptance Criteria

The ML subsystem is considered MVP-complete when:

- [ ] Historical features are generated without temporal leakage.
- [ ] Feature calculations are deterministic where practical.
- [ ] Feature definitions are versioned.
- [ ] A rule-based baseline exists.
- [ ] Isolation Forest baseline exists.
- [ ] A hybrid risk score is implemented.
- [ ] Risk levels are configurable.
- [ ] Structured risk factors are generated.
- [ ] Model versions are persisted.
- [ ] Dataset lineage is preserved.
- [ ] Time-based evaluation is implemented.
- [ ] Scenario-level evaluation is implemented.
- [ ] Precision, recall, F1 and PR-AUC are reported.
- [ ] Alert volume is measured.
- [ ] False positives are explicitly evaluated.
- [ ] Legitimate unusual transactions are represented in evaluation.
- [ ] Account-level detection can be measured.
- [ ] Model failures do not corrupt transaction data.
- [ ] AI summaries consume structured evidence rather than inventing it.
- [ ] Human investigators remain responsible for final resolution.

---

# 89. Open ML Decisions

The following should remain empirical implementation decisions:

1. Exact feature list for version 1.
2. Historical window for each feature.
3. Isolation Forest hyperparameters.
4. Contamination strategy.
5. Hybrid scoring weights.
6. Risk-level thresholds.
7. Investigation trigger thresholds.
8. Minimum data required before calculating account baselines.
9. Exact handling of sparse/new accounts.
10. LLM provider and model.
11. AI prompt structure.
12. Model artifact storage mechanism.
13. Experiment tracking approach.

These decisions should be documented in `DECISIONS.md` as they are finalized.

---

# 90. Final Intelligence Principle

FinSignal's ML system should be judged by whether it helps an investigator answer:

> "What is unusual here, how unusual is it relative to this account, what evidence supports the alert, and what should I investigate next?"

It should **not** be judged solely by whether it can produce the highest possible classification score.

The intended intelligence chain is:

```text
Behavior
   ↓
Deviation
   ↓
Anomaly
   ↓
Risk
   ↓
Evidence
   ↓
Investigation
   ↓
Human Decision
```

The final design principle is:

> **Detect patterns, preserve context, expose evidence, quantify uncertainty, and keep the human investigator in control.**
