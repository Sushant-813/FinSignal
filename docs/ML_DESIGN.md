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

# 7. Feature Engineering

Feature engineering is the most important part of the initial ML design.

The objective is to represent:

- transaction magnitude
- transaction frequency
- temporal behavior
- merchant behavior
- device behavior
- geographic behavior
- category behavior
- account-level behavioral change

---

# 8. Feature Categories

## 8.1 Transaction Amount Features

Examples:

```text
amount
amount_log
amount_vs_account_mean
amount_vs_account_median
amount_zscore
amount_percentile
```

### Example

If an account normally spends:

```text
₹500 - ₹2,000
```

and suddenly makes:

```text
₹75,000
```

the absolute amount is useful, but the deviation relative to the account is more informative.

---

# 9. Velocity Features

Velocity captures transaction frequency over time windows.

Examples:

```text
transactions_last_5min
transactions_last_15min
transactions_last_1hour
transactions_last_6hours
transactions_last_24hours
```

Additional amount-based velocity:

```text
amount_last_1hour
amount_last_24hours
```

These features support detection of:

- rapid transaction bursts
- automated attacks
- account takeover
- unusual spending bursts

---

# 10. Merchant Features

Examples:

```text
merchant_transaction_count
merchant_frequency
merchant_amount_mean
merchant_amount_deviation
is_new_merchant
```

Historical merchant behavior should be account-specific.

A merchant frequently used by one account may be unusual for another.

---

# 11. Device Features

Examples:

```text
device_transaction_count
device_frequency
is_new_device
device_account_count
device_first_seen_age
```

Important behavioral signal:

```text
is_new_device = true
```

when the transaction is associated with a device not previously observed for the account.

A device used by multiple accounts can also become an important network signal.

---

# 12. Location Features

Examples:

```text
location_frequency
is_new_location
distance_from_home
location_account_frequency
```

The initial implementation may use logical city/state/country differences rather than exact geospatial calculations.

If coordinates are available later, geospatial distance can be introduced.

---

# 13. Temporal Features

Examples:

```text
hour_of_day
day_of_week
is_weekend
is_unusual_hour
```

Temporal behavior should be account-specific.

For example:

```text
Account A normally transacts 09:00–18:00
Account B normally transacts 18:00–02:00
```

The same transaction time should therefore not automatically have the same risk meaning.

---

# 14. Category Features

Examples:

```text
category_frequency
category_amount_mean
category_amount_deviation
is_new_category
category_spend_share
```

These help identify behavioral shifts such as:

```text
normal:
food + groceries

sudden:
electronics + travel + high-value purchases
```

---

# 15. Account Behavioral Features

Account-level features capture broader behavior.

Examples:

```text
daily_transaction_count
daily_spend
weekly_spend
monthly_spend
average_transaction_amount
median_transaction_amount
category_distribution
merchant_diversity
device_count
location_diversity
```

These features should be computed from historical data available before the transaction being evaluated.

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

---

# 23. Isolation Forest Inputs

The model should consume engineered numerical features such as:

```text
amount_log
amount_zscore
transactions_last_5min
transactions_last_1hour
transactions_last_24hours
merchant_frequency
device_frequency
location_frequency
category_spending_deviation
is_new_device
is_new_location
is_new_merchant
is_unusual_hour
```

Categorical values should be encoded appropriately before model input.

The exact final feature set should be determined through controlled experiments.

---

# 24. Feature Scaling

Isolation Forest is generally less dependent on feature scaling than distance-based algorithms, but preprocessing remains important.

The pipeline should:

1. identify numeric features
2. handle missing values
3. encode categorical/binary features
4. transform heavily skewed financial variables where appropriate
5. ensure deterministic feature ordering

A reproducible preprocessing pipeline must be versioned with the model.

---

# 25. Missing Values

Missing values must not automatically be interpreted as suspicious.

Examples:

```text
missing device
missing merchant
missing location
```

may reflect legitimate transaction-channel limitations.

The feature pipeline should distinguish:

```text
unknown
```

from:

```text
unusual
```

where possible.

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

# 40. Account-Level Aggregation

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

The MVP may expose account-level analytics without introducing a separate account-level ML model.

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
