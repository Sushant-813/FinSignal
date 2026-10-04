# FinSignal
## Dataset Specification

**Product:** FinSignal  
**Full Name:** Financial Transaction Intelligence & Investigation Platform  
**Document:** Dataset Specification  
**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-10-04

---

# 1. Purpose

This document defines the structure, semantics, generation strategy, behavioral assumptions, fraud scenarios, validation rules, and evaluation requirements for the datasets used by FinSignal.

The dataset is designed specifically for:

- Financial transaction analytics
- Account behavioral analysis
- Anomaly detection
- Risk scoring
- Fraud investigation
- Model evaluation
- Investigation workflow testing

The dataset must represent realistic financial behavior rather than uniformly random transactions.

The central principle is:

> **The dataset must contain enough behavioral structure for the system to learn what is normal before it can identify what is unusual.**

---

# 2. Dataset Objectives

The dataset should enable FinSignal to:

1. Represent realistic financial accounts.
2. Represent realistic merchants and locations.
3. Represent normal transaction behavior.
4. Represent account-specific behavioral differences.
5. Represent legitimate unusual transactions.
6. Represent fraudulent and anomalous behavior.
7. Support temporal behavioral analysis.
8. Support transaction-level anomaly detection.
9. Support account-level behavioral analysis.
10. Support investigation workflows.
11. Support reproducible ML experiments.
12. Support future graph/network analysis.

---

# 3. Dataset Strategy

FinSignal will initially use a **synthetic, behavior-driven financial transaction dataset**.

Synthetic generation is preferred because it provides control over:

- Fraud prevalence
- Fraud scenarios
- Account behavior
- Transaction distributions
- Temporal patterns
- Device relationships
- Location relationships
- Merchant relationships
- Ground truth
- Dataset size
- Reproducibility

The generator must produce data that behaves more like a financial system than a random table of numbers.

---

# 4. Dataset Scale

The target full development dataset is:

| Entity | Target Count |
|---|---:|
| Accounts | 5,000 |
| Merchants | 500 |
| Devices | 8,000 |
| Locations | 100 |
| Transactions | ~250,000 |
| Fraud / anomalous activity | ~3% |

These values are targets rather than hard limits.

The generator must support configurable sizes.

---

# 5. Development Scaling Strategy

The full dataset should not be generated immediately.

Development should progress through controlled dataset sizes.

## Stage 1 — Development Dataset

```text
Accounts:      100
Transactions:  ~5,000
```

Purpose:

- Generator development
- Data validation
- Schema validation
- Initial analytics
- Initial feature engineering
- ML experimentation
- Debugging

---

## Stage 2 — Intermediate Dataset

```text
Accounts:      ~1,000
Transactions:  ~50,000
```

Purpose:

- Performance testing
- Behavioral validation
- Model evaluation
- Investigation workflow testing

---

## Stage 3 — Full Dataset

```text
Accounts:      5,000
Transactions:  ~250,000
```

Purpose:

- Full system validation
- Performance evaluation
- Final ML experiments
- Demonstration environment

---

# 6. Reproducibility

Dataset generation must be deterministic when provided with the same configuration and random seed.

Example:

```text
Seed: 20261004
```

The generator should expose configuration for:

- Random seed
- Number of accounts
- Number of merchants
- Number of devices
- Number of locations
- Number of transactions
- Fraud rate
- Dataset time range
- Scenario distribution

Example conceptual configuration:

```yaml
seed: 20261004

accounts:
  count: 5000

merchants:
  count: 500

devices:
  count: 8000

locations:
  count: 100

transactions:
  count: 250000

fraud:
  target_rate: 0.03
```

The actual configuration format will be finalized during implementation.

---

# 7. Dataset Entities

The dataset consists of the following primary entities:

```text
Account
Merchant
Device
Location
Transaction
```

Additional derived datasets may be generated during processing.

Examples:

```text
Cleaned Transactions
Behavioral Features
Risk Analyses
Risk Factors
Investigations
```

---

# 8. Entity Relationships

Conceptually:

```text
Account
   |
   +--------< Transaction >-------- Merchant
   |
   +--------< Device
   |
   +--------< Location
```

A transaction should reference:

- One account
- One merchant where applicable
- One device where applicable
- One location where applicable

Some transaction types may legitimately omit a merchant.

---

# 9. Account Specification

Accounts represent customers or financial entities whose behavior can be analyzed.

## Required Fields

| Field | Description |
|---|---|
| `account_id` | Unique account identifier |
| `account_type` | Type of account |
| `customer_age` | Synthetic customer age |
| `account_age_days` | Static age of account at generation time (informational only; production ML features must derive point-in-time age from `transaction.occurred_at - account.created_at`) |
| `home_city` | Primary account location |
| `created_at` | Account creation timestamp |
| `status` | Account status |

---

# 10. Account Types

Initial account types may include:

```text
PERSONAL
BUSINESS
PREMIUM
```

The exact taxonomy may evolve during implementation.

---

# 11. Account Behavioral Profiles

Each account must have an underlying behavioral profile.

Possible profiles:

```text
LOW_SPENDER
MODERATE_SPENDER
HIGH_SPENDER
SUBSCRIPTION_HEAVY
BUSINESS_LIKE
```

The profile itself should not be directly exposed as a model feature unless there is a legitimate product reason.

It primarily controls synthetic behavior.

---

# 12. Account Behavior Characteristics

Each account should have configurable behavioral characteristics such as:

- Typical transaction amount
- Amount variance
- Daily transaction frequency
- Preferred categories
- Preferred merchants
- Preferred transaction hours
- Preferred days
- Normal devices
- Normal locations
- Travel frequency
- Transaction-type distribution

Example:

```text
Account A

Profile:
MODERATE_SPENDER

Typical amount:
₹500 - ₹4,000

Typical daily volume:
2 - 5 transactions

Preferred categories:
FOOD
SHOPPING
GROCERIES

Normal activity:
08:00 - 23:00

Normal locations:
Bengaluru
Mysuru
```

Another account may have completely different behavior.

---

# 13. Merchant Specification

Merchants represent transaction counterparties.

## Fields

| Field | Description |
|---|---|
| `merchant_id` | Unique merchant identifier |
| `merchant_name` | Synthetic merchant name |
| `merchant_category` | Merchant category |
| `city` | Merchant city |
| `state` | Merchant state |
| `country` | Merchant country |

---

# 14. Merchant Categories

Initial categories include:

```text
FOOD
GROCERIES
SHOPPING
ELECTRONICS
TRAVEL
HOTEL
ENTERTAINMENT
UTILITIES
HEALTHCARE
RENT
INSURANCE
SUBSCRIPTION
ATM
TRANSFER
OTHER
```

Additional categories may be introduced if required by analysis.

---

# 15. Merchant Behavior

Merchants should have realistic transaction distributions.

Example approximate ranges:

| Category | Typical Amount |
|---|---:|
| Food | ₹100 – ₹2,000 |
| Groceries | ₹200 – ₹8,000 |
| Shopping | ₹500 – ₹25,000 |
| Electronics | ₹2,000 – ₹80,000 |
| Travel | ₹2,000 – ₹100,000 |
| Hotel | ₹2,000 – ₹50,000 |
| Healthcare | ₹500 – ₹100,000 |
| Rent | ₹10,000 – ₹50,000 |
| Insurance | ₹5,000 – ₹100,000 |
| Subscription | ₹100 – ₹10,000 |
| Salary | ₹25,000 – ₹2,00,000 |

These ranges are guidelines rather than fixed limits.

Distributions should contain realistic variance.

---

# 16. Device Specification

Devices represent devices used to initiate transactions.

## Fields

| Field | Description |
|---|---|
| `device_id` | Unique device identifier |
| `device_type` | Mobile / desktop / tablet / other |
| `operating_system` | Synthetic operating system |
| `first_seen_at` | First known activity timestamp |

---

# 17. Device Assignment

A normal account should generally use:

```text
1 - 3 normal devices
```

Additional devices may appear during legitimate or suspicious scenarios.

A new device should not automatically mean fraud.

For example:

- New phone
- New laptop
- Device replacement
- Legitimate travel

may all create legitimate new-device events.

---

# 18. Location Specification

Locations represent the geographic context of transactions.

## Fields

| Field | Description |
|---|---|
| `location_id` | Unique location identifier |
| `city` | City |
| `state` | State |
| `country` | Country |

The initial dataset should contain approximately:

```text
100 locations
```

---

# 19. Account Location Behavior

Each account should have:

- One primary/home location
- Zero or more legitimate secondary locations
- A probability distribution across locations

Example:

```text
Home:
Bengaluru

Frequent:
Mysuru

Occasional:
Mumbai
Delhi

Rare:
Other locations
```

A new location should therefore be treated as a behavioral signal rather than automatic fraud.

---

# 20. Transaction Specification

Transactions are the central dataset entity.

## Required Fields

| Field | Description |
|---|---|
| `transaction_id` | Unique transaction identifier |
| `account_id` | Account performing the transaction |
| `timestamp` | Transaction timestamp |
| `amount` | Transaction amount |
| `currency` | Currency |
| `transaction_type` | Transaction type |
| `merchant_id` | Merchant reference where applicable |
| `category` | Transaction category |
| `location_id` | Location reference where applicable |
| `device_id` | Device reference |
| `payment_method` | Payment method |
| `channel` | Transaction channel |

---

# 21. Transaction Types

Initial transaction types:

```text
DEBIT
CREDIT
TRANSFER
WITHDRAWAL
DEPOSIT
```

Examples:

```text
Salary → CREDIT
Restaurant → DEBIT
ATM cash → WITHDRAWAL
Account transfer → TRANSFER
Cash deposit → DEPOSIT
```

---

# 22. Currency

The initial dataset should use:

```text
INR
```

Multi-currency support may be added later.

The schema should avoid preventing future multi-currency support.

---

# 23. Payment Methods

Initial payment methods may include:

```text
UPI
CARD
BANK_TRANSFER
ATM
NET_BANKING
CASH
```

The distribution should depend on transaction type and account behavior.

---

# 24. Transaction Channels

Possible channels:

```text
MOBILE
WEB
POS
ATM
BANK
```

The channel should be correlated with realistic transaction types.

Example:

```text
ATM withdrawal → ATM
UPI payment → MOBILE
Card purchase → POS
Bank transfer → BANK / WEB
```

---

# 25. Transaction Amount Generation

Transaction amounts must not be uniformly random.

Amount generation should depend on:

- Account profile
- Merchant category
- Transaction type
- Historical account behavior
- Legitimate events
- Fraud scenario

Examples:

```text
Food:
Low-to-moderate amounts

Electronics:
Moderate-to-high amounts

Rent:
High recurring amount

Salary:
High credit amount

ATM:
Variable withdrawal amounts
```

---

# 26. Transaction Frequency

Transaction frequency should depend on the account.

Possible behavior:

```text
Low activity:
1 - 2 transactions/day

Moderate activity:
2 - 6 transactions/day

High activity:
5 - 15 transactions/day

Business-like:
Potentially higher transaction volume
```

The exact distribution should be probabilistic rather than deterministic.

---

# 27. Temporal Behavior

Each account should have an activity profile.

Examples:

```text
Normal daytime account:
08:00 - 22:00

Night-shift account:
18:00 - 04:00

Business account:
07:00 - 21:00

Irregular account:
Broader activity distribution
```

This is important because:

> A transaction at 2 AM should not be equally suspicious for every account.

---

# 28. Merchant Preferences

Accounts should have merchant preferences.

Each account should have:

```text
Preferred Merchants
Occasional Merchants
Rare Merchants
```

Transaction generation should sample from these groups with different probabilities.

This creates realistic merchant behavior and enables:

- New merchant detection
- Merchant frequency analysis
- Behavioral deviation detection

---

# 29. Category Preferences

Accounts should also have category preferences.

Example:

```text
Account A:

FOOD          → high
GROCERIES     → high
SHOPPING      → medium
TRAVEL        → low
ELECTRONICS   → rare
```

Another account may have a completely different distribution.

---

# 30. Legitimate Unusual Activity

The dataset must deliberately contain legitimate unusual events.

Examples:

### Salary

Large credit that occurs periodically.

### Rent

Large recurring debit.

### Insurance

Large annual or periodic payment.

### Travel

Temporary change in location and spending.

### Healthcare

Potentially large medical payment.

### Electronics

Large one-time purchase.

### Business Expense

High-value transaction consistent with account type.

These transactions should remain labeled as legitimate ground truth.

---

# 31. Fraud and Anomaly Scenarios

The dataset should contain multiple fraud/anomaly scenarios.

Initial scenario identifiers:

```text
F001
F002
F003
F004
F005
F006
F007
```

---

# 32. F001 — Large Amount Anomaly

The transaction amount is significantly above the account's normal behavior.

Example:

```text
Historical median:
₹2,500

Suspicious transaction:
₹35,000
```

However, the generator must also produce legitimate high-value transactions so that:

```text
High amount ≠ automatic fraud
```

---

# 33. F002 — New Device

The account performs a transaction using a previously unseen device.

Potential pattern:

```text
Known account
      |
      v
New device
      |
      v
Unusual transaction
```

The scenario may be:

- Single-signal
- Combined with another signal

---

# 34. F003 — New Location

The transaction occurs from a location outside the account's normal behavior.

Example:

```text
Normal:
Bengaluru

Unexpected:
Delhi
```

A new location alone should not always result in fraud.

Legitimate travel scenarios should exist.

---

# 35. F004 — Unusual Transaction Time

The transaction occurs outside the account's normal activity window.

Example:

```text
Normal:
08:00 - 23:00

Transaction:
03:17
```

The generator should include accounts with different legitimate activity schedules.

---

# 36. F005 — High Transaction Velocity

The account performs an unusually high number of transactions within a short time period.

Example:

```text
Normal:
2 - 5 transactions/day

Observed:
8 transactions in 10 minutes
```

Velocity scenarios should involve transaction sequences rather than isolated records.

---

# 37. F006 — Account Takeover Pattern

A multi-signal scenario representing potential account compromise.

Possible combination:

```text
New Device
     +
New Location
     +
Unusual Time
     +
Large Amount
     +
High Velocity
```

The scenario should generate multiple related transactions where appropriate.

This is intentionally more complex than single-signal scenarios.

---

# 38. F007 — Behavioral Spending Shift

The account's behavior changes significantly over a period of time.

Example:

```text
Historical behavior:

Food        → high
Groceries   → high
Travel      → low
Electronics → rare

Observed period:

Electronics → very high
Travel      → high
Food        → low
```

The anomaly may be visible only through aggregate behavioral analysis.

---

# 39. Fraud Scenario Distribution

Initial target distribution:

| Scenario | Approx. Share |
|---|---:|
| Large Amount | 20% |
| New Device | 15% |
| New Location | 15% |
| Unusual Time | 10% |
| High Velocity | 15% |
| Account Takeover | 15% |
| Behavioral Shift | 10% |

These percentages apply to the synthetic fraudulent/anomalous population, not to all transactions.

They are configurable targets rather than immutable requirements.

---

# 40. Fraud Rate

The target fraudulent/anomalous activity rate is approximately:

```text
3%
```

Therefore:

```text
~97% legitimate
~3% fraudulent/anomalous
```

The generator should allow this rate to be configured.

---

# 41. Multi-Transaction Fraud

Not every fraud scenario should affect only one transaction.

Some scenarios should generate a sequence.

Example:

```text
Transaction 1
New device

Transaction 2
New location

Transaction 3
Large amount

Transaction 4
High velocity
```

This allows FinSignal to evaluate whether it can detect behavioral patterns rather than isolated anomalies.

---

# 42. Scenario Instance IDs

Multi-transaction scenarios should share a common identifier.

Example:

```text
scenario_instance_id = ATO-00042
```

Transactions:

```text
T1001 → ATO-00042
T1002 → ATO-00042
T1003 → ATO-00042
```

This allows evaluation at the scenario level.

---

# 43. Ground Truth Fields

Synthetic transaction data may contain:

```text
is_fraud
fraud_scenario
scenario_instance_id
```

These fields are strictly for:

- Dataset evaluation
- Testing
- Ground-truth analysis

They must not be used as model input features.

---

# 44. Data Leakage Prevention

The generator and ML pipeline must prevent leakage.

The following must never become model features:

```text
is_fraud
fraud_scenario
scenario_instance_id
```

The system must also avoid indirect leakage.

For example, a generated field that directly encodes:

```text
"this transaction was generated by the fraud generator"
```

must not be available during model inference.

Ground truth must remain isolated from production feature generation.

---

# 45. Account-to-Account Transfers

The dataset should include account-to-account transfers.

This is useful for:

- Transfer analytics
- Account relationship analysis
- Future network analysis
- Future graph-based fraud detection

Graph analysis is not part of the MVP.

However, preserving the relationship now avoids unnecessarily constraining the dataset later.

---

# 46. Data Quality Requirements

Generated data must pass automated validation.

At minimum:

## Identity

- Transaction IDs must be unique.
- Account IDs must be unique.
- Merchant IDs must be unique.
- Device IDs must be unique.
- Location IDs must be unique.

## References

- Every transaction account must exist.
- Every merchant reference must exist where required.
- Every device reference must exist.
- Every location reference must exist.

## Financial

- Amounts must be valid.
- Amounts must not contain invalid negative values unless the transaction semantics explicitly allow them.
- Currency must be valid.

## Temporal

- Timestamps must be valid.
- Timestamps must fall within the configured dataset period.
- Account/device relationships must respect first-seen timestamps.

---

# 47. Dataset Validation Metrics

After generation, the system should report:

```text
Total Accounts
Total Merchants
Total Devices
Total Locations
Total Transactions

Fraud Count
Fraud Rate

Scenario Distribution

Duplicate Transaction Count
Missing Required Values
Invalid References
Invalid Amounts
Invalid Timestamps
```

Example:

```text
Dataset Validation Report

Accounts:              5,000
Merchants:               500
Devices:               8,000
Locations:               100
Transactions:        250,000

Fraud Transactions:    7,482
Fraud Rate:              2.99%

Duplicate IDs:              0
Invalid References:         0
Invalid Amounts:            0
Missing Required Fields:    0
```

---

# 48. Behavioral Validation

Schema validation is not sufficient.

The generator should also be validated statistically.

Examples:

- Transaction amount distribution
- Transaction frequency distribution
- Category distribution
- Merchant concentration
- Account-level spending distribution
- Time-of-day distribution
- Location distribution
- Device distribution
- Fraud scenario distribution

The objective is to ensure the dataset exhibits meaningful behavioral structure.

---

# 49. Reproducibility Validation

Running the generator twice with the same configuration and seed should produce equivalent output.

Example:

```text
Configuration A
Seed = 20261004

Generation #1
        |
        v
Dataset A

Generation #2
        |
        v
Dataset B
```

Expected:

```text
Dataset A == Dataset B
```

where deterministic output is expected.

---

# 50. Temporal Dataset Splitting

ML evaluation should primarily use chronological splits.

Example:

```text
+----------------+----------------+------------+
| Training       | Validation     | Test       |
+----------------+----------------+------------+
| Jan - Jun      | Jul - Aug      | September  |
+----------------+----------------+------------+
```

The exact dates will depend on the generated dataset period.

Future transactions must not influence historical features.

---

# 51. Historical Feature Rule

When calculating a transaction's behavioral features:

> Only information available at or before the transaction's evaluation point may be used.

For example:

A transaction occurring on:

```text
2026-07-15
```

must not use:

```text
2026-07-16
```

activity to calculate its historical behavioral baseline.

This rule is essential to prevent temporal leakage.

---

# 52. Dataset Storage Layers

The data pipeline should conceptually distinguish:

```text
Raw Dataset
     |
     v
Validated Dataset
     |
     v
Cleaned Dataset
     |
     v
Enriched Dataset
     |
     v
Feature Dataset
```

Model outputs should remain separate:

```text
Feature Dataset
      |
      v
Risk Analysis
      |
      v
Investigation
```

---

# 53. Raw vs Derived Data

Raw financial facts must remain distinguishable from derived intelligence.

## Raw

Examples:

- Transaction amount
- Timestamp
- Account ID
- Merchant ID
- Device ID
- Location ID

## Derived

Examples:

- Amount z-score
- Transaction velocity
- New device indicator
- Behavioral deviation
- Risk score
- Risk level

## Investigation Intelligence

Examples:

- Risk factors
- Evidence
- AI summary
- Human resolution

This separation should be preserved throughout the architecture.

---

# 54. Dataset Versioning

Dataset versions should be identifiable.

Example:

```text
dataset-v1.0
dataset-v1.1
dataset-v2.0
```

A dataset version should ideally record:

- Generator version
- Configuration
- Random seed
- Generation timestamp
- Dataset period
- Number of entities
- Fraud rate
- Scenario distribution

---

# 55. Generator Requirements

The synthetic data generator should:

1. Accept configurable parameters.
2. Support deterministic seeds.
3. Generate related entities.
4. Generate account-specific behavior.
5. Generate realistic transactions.
6. Generate legitimate unusual events.
7. Generate fraud/anomaly scenarios.
8. Generate multi-transaction scenarios.
9. Generate ground truth separately from production features.
10. Validate generated data.
11. Produce dataset statistics.
12. Support small development datasets and larger evaluation datasets.

---

# 56. Generator Architecture

Conceptually:

```text
Configuration
     |
     v
Random Seed
     |
     v
Account Generator
     |
     +---- Merchant Generator
     |
     +---- Location Generator
     |
     +---- Device Generator
     |
     v
Behavior Profile Assignment
     |
     v
Normal Transaction Generator
     |
     +---- Legitimate Unusual Events
     |
     +---- Fraud Scenario Generator
     |
     v
Ground Truth Assignment
     |
     v
Dataset Validation
     |
     v
Dataset Export
```

---

# 57. Dataset Outputs

The generator should be capable of producing separate logical outputs such as:

```text
accounts.csv
merchants.csv
devices.csv
locations.csv
transactions.csv
```

Ground-truth information may either be stored separately or clearly isolated from production-facing datasets.

Example:

```text
transactions.csv
transactions_ground_truth.csv
```

The exact file structure will be finalized during implementation.

---

# 58. Privacy Requirements

The dataset must not contain real personally identifiable financial information.

It should use:

- Synthetic account IDs
- Synthetic customer attributes
- Synthetic merchant names
- Synthetic locations
- Synthetic devices
- Synthetic transactions

No real:

- Bank account numbers
- Card numbers
- Customer names
- Phone numbers
- Email addresses
- Government IDs

should be required for the dataset.

---

# 59. Security Considerations

Synthetic ground-truth information should not be exposed through production APIs where it could compromise the evaluation or investigation workflow.

For example, production transaction responses should not expose:

```text
is_fraud
fraud_scenario
scenario_instance_id
```

unless explicitly requested by a controlled evaluation workflow.

---

# 60. Future Dataset Extensions

Future versions may introduce:

- Multiple currencies
- Cross-border transactions
- Merchant risk profiles
- Account networks
- Beneficiary relationships
- Shared devices
- Shared locations
- IP/network information
- Chargebacks
- Failed transactions
- Card-present/card-not-present indicators
- Graph relationships
- Synthetic customer segments

These are not required for the initial dataset.

---

# 61. Acceptance Criteria

The dataset specification will be considered successfully implemented when:

### AC-001

The generator can create the development dataset.

### AC-002

The generated dataset passes structural validation.

### AC-003

All foreign-key relationships are valid.

### AC-004

Transaction IDs are unique.

### AC-005

The target fraud rate is approximately achieved.

### AC-006

All defined fraud scenarios can be generated.

### AC-007

At least some fraud scenarios contain multiple related transactions.

### AC-008

Legitimate unusual transactions are present.

### AC-009

Accounts exhibit distinct behavioral patterns.

### AC-010

Transaction frequency and amount distributions are non-uniform and realistic.

### AC-011

The same seed and configuration produce reproducible results.

### AC-012

Ground-truth fields are isolated from model features.

### AC-013

Temporal leakage is prevented during feature generation.

### AC-014

The dataset can scale from the development dataset to the full target dataset.

### AC-015

Dataset statistics and validation reports are generated.

---

# 62. Open Questions

The following decisions will be finalized during technical design:

1. Exact Python libraries used for data generation.
2. Exact probability distributions for transaction amounts.
3. Exact account behavioral-profile distributions.
4. Exact dataset time range.
5. Exact CSV schema and column ordering.
6. Exact handling of invalid imported data.
7. Exact fraud-scenario generation algorithms.
8. Whether ground truth is stored in a separate dataset.
9. Exact database ingestion strategy.
10. Exact feature-generation pipeline.

These decisions belong primarily in:

- `TRD.md`
- `DATABASE_DESIGN.md`
- `ML_DESIGN.md`

---

# 63. Document Status

**Version:** 1.0.0  
**Status:** Draft  
**Previous Document:** `PRD.md`  
**Next Document:** `TRD.md`

This document defines the dataset requirements that the technical architecture and ML design must satisfy.
