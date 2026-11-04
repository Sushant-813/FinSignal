# FinSignal

## Product Requirements Document (PRD)

| Field | Value |
|---|---|
| **Product** | FinSignal |
| **Full Name** | Financial Transaction Intelligence & Investigation Platform |
| **Document** | Product Requirements Document |
| **Version** | 1.0.0 |
| **Status** | Draft |
| **Last Updated** | 2026-10-04 |

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Problem Statement](#2-problem-statement)
3. [Product Vision](#3-product-vision)
4. [Product Goals](#4-product-goals)
5. [Product Non-Goals](#5-product-non-goals)
6. [Target Users](#6-target-users)
7. [Core Product Workflow](#7-core-product-workflow)
8. [Transaction Lifecycle](#8-transaction-lifecycle)
9. [Core Product Capabilities](#9-core-product-capabilities)
10. [Data Cleaning and Normalization](#10-data-cleaning-and-normalization)
11. [Financial Analytics](#11-financial-analytics)
12. [Behavioral Intelligence](#12-behavioral-intelligence)
13. [Risk and Anomaly Detection](#13-risk-and-anomaly-detection)
14. [Risk Factors](#14-risk-factors)
15. [Investigation Workflow](#15-investigation-workflow)
16. [Investigation Status](#16-investigation-status)
17. [Investigation Resolution](#17-investigation-resolution)
18. [Investigation Evidence](#18-investigation-evidence)
19. [AI Investigation Assistant](#19-ai-investigation-assistant)
20. [AI Safety Boundaries](#20-ai-safety-boundaries)
21. [Authentication and Authorization](#21-authentication-and-authorization)
22. [Dataset Strategy](#22-dataset-strategy)
23. [Synthetic Behavioral Profiles](#23-synthetic-behavioral-profiles)
24. [Fraud / Anomaly Scenarios](#24-fraud--anomaly-scenarios)
25. [Legitimate Unusual Activity](#25-legitimate-unusual-activity)
26. [Ground Truth](#26-ground-truth)
27. [Evaluation Philosophy](#27-evaluation-philosophy)
28. [Temporal Evaluation](#28-temporal-evaluation)
29. [Functional Requirements](#29-functional-requirements)
30. [Non-Functional Requirements](#30-non-functional-requirements)
31. [MVP Scope](#31-mvp-scope)
32. [Deferred Features](#32-deferred-features)
33. [Success Criteria](#33-success-criteria)
34. [Product Principles](#34-product-principles)
35. [High-Level Product Architecture](#35-high-level-product-architecture)
36. [Traceability to Future Documentation](#36-traceability-to-future-documentation)
37. [Document Status](#37-document-status)

---

## 1. Product Overview

FinSignal is a financial transaction intelligence and investigation platform designed to analyze transaction behavior, identify anomalous or suspicious activity, and assist human investigators in understanding why an activity was flagged.

The platform combines:

- Financial transaction analytics
- Data validation and cleaning
- Behavioral profiling
- Feature engineering
- Machine-learning-based anomaly detection
- Risk scoring
- Investigation workflows
- Evidence aggregation
- AI-assisted investigation summaries
- Human-in-the-loop decision making

FinSignal is not intended to be a simple fraud classifier.

The system is designed around the following principle:

> **Detect unusual behavior, provide contextual evidence, explain the signals, and allow a human investigator to make the final decision.**

The platform therefore separates:

1. **Observed financial facts**
2. **Derived behavioral intelligence**
3. **Machine-generated risk signals**
4. **Investigator decisions**

This separation is fundamental to the system's design.

---

## 2. Problem Statement

Financial transaction datasets can contain large volumes of activity that are difficult to analyze manually.

Traditional transaction analysis often suffers from several problems:

- Large transaction volumes make manual review impractical.
- Simple threshold-based rules generate excessive false positives.
- A high-value transaction is not necessarily fraudulent.
- Legitimate users may have very different spending behaviors.
- Suspicious behavior may only become apparent when multiple signals are considered together.
- Investigators need account history and behavioral context, not just a risk score.
- Black-box model predictions can be difficult for investigators to trust.
- Automated systems may incorrectly treat model output as a final fraud decision.
- Raw transaction data may contain missing, malformed, duplicated, or inconsistent records.
- Investigation workflows are often disconnected from analytics and model output.

FinSignal addresses these problems by combining transaction intelligence, behavioral analysis, anomaly detection, contextual evidence, and investigator review in a single platform.

---

## 3. Product Vision

> **Build an intelligent financial transaction analysis platform that transforms raw transaction data into actionable behavioral signals and investigation-ready evidence.**

FinSignal should help an analyst or investigator answer:

- What happened?
- Is this behavior unusual for this account?
- How unusual is it?
- What signals caused the transaction to be flagged?
- How does this activity compare with the account's historical behavior?
- Are there related transactions showing a broader pattern?
- Is this likely to be a legitimate unusual event or suspicious activity?
- What evidence supports the investigation?
- What should the investigator review next?

The platform should prioritize **context over isolated scores**.

---

## 4. Product Goals

### 4.1 Primary Goals

#### G1. Transaction Intelligence

Provide meaningful financial analytics over imported transaction data.

The system should allow users to understand:

- Transaction volume
- Transaction amounts
- Spending trends
- Spending categories
- Merchant activity
- Account behavior
- Transaction frequency
- Time-based patterns
- Geographic behavior
- Payment/channel behavior

#### G2. Data Quality and Reliability

Ensure that transaction data is validated, cleaned, normalized, and suitable for downstream analysis.

The system should identify:

- Missing required fields
- Invalid values
- Duplicate transactions
- Invalid references
- Invalid timestamps
- Invalid transaction amounts
- Inconsistent categorical values
- Other data-quality problems

The system should report data-quality issues rather than silently hiding them.

#### G3. Behavioral Modeling

Establish a behavioral baseline for accounts.

FinSignal should recognize that:

> **Normal behavior is account-dependent.**

For example, a ₹40,000 transaction may be highly unusual for one account but completely normal for another.

Behavioral analysis should consider factors such as:

- Typical transaction amount
- Transaction frequency
- Preferred merchants
- Preferred categories
- Typical transaction times
- Typical locations
- Normal devices
- Spending patterns
- Historical behavior

#### G4. Anomaly and Risk Detection

Identify transactions or behavioral patterns that deviate significantly from established account behavior.

The system should detect signals such as:

- Unusually large transactions
- New devices
- New locations
- Unusual transaction times
- High transaction velocity
- Sudden behavioral changes
- Unusual merchant activity
- Combinations of multiple suspicious signals

The output should be represented as a **risk score or anomaly score**, not automatically as a probability of fraud unless the underlying model has been properly calibrated for that interpretation.

#### G5. Investigation Support

Provide investigators with sufficient context to investigate flagged activity.

An investigator should be able to move from:

> Flagged transaction → Account → Historical behavior → Related transactions → Risk factors → Evidence → Investigation decision

The investigation interface should reduce the need to manually gather context from multiple screens or systems.

#### G6. Explainability

Every flagged activity should provide understandable reasons for why it was flagged.

Examples:

- Transaction amount is significantly above the account's historical average.
- Transaction occurred from a previously unseen device.
- Transaction occurred from an unusual location.
- Transaction occurred outside the account's normal activity hours.
- Account experienced unusually high transaction velocity.
- Multiple unusual signals occurred together.

The system should expose structured evidence behind the risk score wherever possible.

#### G7. AI-Assisted Investigation

FinSignal may use an LLM to summarize structured investigation evidence.

The AI assistant should:

- Summarize the observed activity
- Explain the important risk factors
- Highlight relevant historical comparisons
- Describe relationships between signals
- Produce an investigation-oriented narrative

The AI assistant must **not**:

- Invent evidence
- Modify transaction facts
- Independently determine fraud
- Override the investigator
- Treat a model score as proof of fraud
- Create unsupported conclusions

The AI layer is an **investigation assistant**, not the final decision-maker.

#### G8. Human-in-the-Loop Decisions

The final investigation outcome must remain under human control.

Possible resolutions include:

- Legitimate
- Suspicious
- Confirmed Fraud
- Inconclusive

The investigator should be able to record the final resolution and investigation status.

---

## 5. Product Non-Goals

The following capabilities are explicitly outside the initial product scope.

### 5.1 Real-Time Transaction Processing

FinSignal will initially operate on imported datasets rather than processing live banking transactions.

Real-time streaming infrastructure such as Kafka is deferred.

### 5.2 Automated Fraud Decisions

FinSignal will not automatically declare a transaction fraudulent solely because a model flags it.

Model output is a risk signal.

Human investigation determines the final outcome.

### 5.3 Banking Integration

The initial version will not directly connect to:

- Banks
- Payment processors
- Credit-card networks
- Core banking systems
- External financial institutions

### 5.4 Production Financial Compliance

The project is not intended to serve as a production regulatory compliance system.

Capabilities such as:

- KYC
- AML regulatory reporting
- SAR generation
- Regulatory filing
- Sanctions screening

are outside the initial scope.

### 5.5 Autonomous AI Investigation

The LLM will not autonomously investigate accounts or make financial decisions.

AI output must be grounded in structured system-generated evidence.

### 5.6 Advanced Graph Fraud Detection

Graph-based fraud detection and network analysis may be supported in future versions.

The initial version will preserve sufficient transaction relationships to make future graph analysis possible, but graph ML is not an MVP requirement.

---

## 6. Target Users

FinSignal has two primary user personas.

### 6.1 Data / Platform Analyst

The analyst is responsible for importing and understanding transaction datasets.

**Responsibilities**

- Import transaction datasets
- Validate data
- Review data-quality reports
- Inspect transaction distributions
- Analyze financial trends
- Review account behavior
- Run risk analysis
- Monitor flagged activity

**Primary Questions**

- Is the dataset valid?
- What does the transaction population look like?
- What patterns exist?
- Which accounts exhibit unusual behavior?
- How many transactions were flagged?
- What are the major risk patterns?

### 6.2 Fraud Investigator

The investigator focuses on suspicious activity.

**Responsibilities**

- Review flagged transactions
- Examine account history
- Review risk factors
- Examine related transactions
- Evaluate behavioral deviations
- Review AI-generated investigation summaries
- Record investigation decisions

**Primary Questions**

- Why was this transaction flagged?
- Is this behavior unusual for the account?
- Are there additional suspicious transactions?
- What evidence supports the alert?
- Could this be a legitimate unusual event?
- What should the final resolution be?

---

## 7. Core Product Workflow

The primary FinSignal workflow is:

```text
Transaction Dataset
        |
        v
Data Import
        |
        v
Validation
        |
        v
Cleaning & Normalization
        |
        v
Enrichment
        |
        v
Behavioral Feature Generation
        |
        v
Financial Analytics
        |
        v
Risk / Anomaly Analysis
        |
        +--------------------+
        |                    |
        v                    v
Normal Activity       Suspicious Activity
                             |
                             v
                       Investigation
                             |
                             v
                      Evidence Assembly
                             |
                             v
                     AI Investigation Summary
                             |
                             v
                       Human Review
                             |
                             v
                         Resolution
```

---

## 8. Transaction Lifecycle

Each transaction should conceptually progress through the following lifecycle:

```text
RECEIVED
   |
   v
VALIDATED
   |
   v
CLEANED
   |
   v
ENRICHED
   |
   v
FEATURES_GENERATED
   |
   v
RISK_ANALYZED
   |
   +---- NORMAL
   |
   +---- SUSPICIOUS
             |
             v
       INVESTIGATION_CREATED
             |
             v
       EVIDENCE_ASSEMBLED
             |
             v
       AI_SUMMARY_GENERATED
             |
             v
         HUMAN_REVIEW
             |
             v
          RESOLVED
```

This lifecycle represents the conceptual product flow and does not require every state to be physically persisted as a transaction status.

---

## 9. Core Product Capabilities

### 9.1 Dataset Import

Users should be able to upload transaction data, initially through CSV.

The system should:

1. Accept the uploaded dataset.
2. Validate the expected schema.
3. Report validation failures.
4. Process valid records.
5. Generate a data-quality report.
6. Make cleaned records available for analysis.

### 9.2 Data Validation

Validation should include:

**Structural Validation**

- Required columns exist.
- Column types are compatible.
- Required identifiers are present.

**Record Validation**

- Transaction IDs are valid.
- Account references exist.
- Amounts are valid.
- Timestamps are valid.
- Enumerated fields contain supported values.

**Integrity Validation**

- Duplicate transaction IDs are detected.
- Foreign-key relationships are valid.
- Impossible values are rejected or reported.

---

## 10. Data Cleaning and Normalization

FinSignal should normalize incoming transaction data before analysis.

Potential operations include:

- Standardizing timestamps
- Normalizing categorical values
- Handling missing values
- Removing or isolating duplicates
- Normalizing currency representation
- Standardizing transaction types
- Standardizing merchant/category values

Cleaning operations should be traceable.

The system should avoid silently modifying important financial facts.

---

## 11. Financial Analytics

FinSignal provides deterministic financial intelligence and aggregation capabilities directly over persisted transaction data. Financial analytics operate independently of machine-learning models, providing immediate operational visibility to investigators and analysts.

### 11.1 Implemented Phase 5 Capabilities

#### 1. Financial Overview Aggregates
- **Scope:** Namespace-partitioned, single-currency macro-metrics over half-open reporting windows `[from_time, to_time)`.
- **Metrics:** Total transaction count, directional debit/credit counts, total volume amount, total debit/credit amounts, net cash flow (`credit - debit`), min and max transaction amounts.
- **Statistical Central Tendency:** Overall average and continuous median, alongside distinct directional debit-only average/median and credit-only average/median. Continuous medians use PostgreSQL `percentile_cont(0.5)` with two-decimal `ROUND_HALF_UP` quantization.

#### 2. Periodic Trend Buckets
- **Aggregation Intervals:** Contiguous `day` or `month` buckets.
- **Zero-Filled Continuity:** Complete time series without calendar gaps; empty intervals are preserved with zero counts and `"0.00"` amounts.
- **Timezone Awareness:** Buckets are generated according to the caller's requested IANA timezone (or UTC), correctly handling daylight saving transitions (e.g., 23-hour spring-forward days) and midnight boundaries without session-timezone coupling.
- **Safety Limits:** Enforces hard limits before query execution: maximum 366 daily buckets and maximum 120 monthly buckets.

#### 3. Category Spending Distributions
- **Directional Grouping:** Breakdown of transaction spend by category for a chosen direction (`DEBIT` or `CREDIT`).
- **Distribution Metrics:** Category transaction count, total volume, average transaction amount, and percentage share of directional total rounded to two decimal places.
- **Uncategorized Activity:** Transactions with null categories are explicitly grouped under `"UNCATEGORIZED"`.

#### 4. Merchant Spending and Ranking
- **Ranking Criteria:** Top merchants ranked by debit spend (`amount`) or frequency (`count`) with deterministic pagination (`limit`, `offset`).
- **Dual Denominator Metrics:**
  - `percentage_of_total_debit`: Merchant debit spend divided by total debit spend across all transactions in the window.
  - `percentage_of_merchant_spend`: Merchant debit spend divided by total debit spend specifically directed to identified merchants.
- **Non-Merchant Debit Isolation:** Unattributed debit spend (peer-to-peer transfers, withdrawals, untracked counterparties) is isolated and reported as `non_merchant_debit_amount`.

#### 5. Account Activity Summaries
- **Authoritative Namespace Scoping:** Account queries derive and enforce the namespace from the persisted `Account.source_namespace`, ignoring caller namespace overrides to prevent cross-partition leakage.
- **Temporal Footprint:** First transaction timestamp, last transaction timestamp, and count of distinct active calendar days in the requested reporting timezone.
- **Top Entities:** Top 5 spending categories and top 5 merchants for the account.
- **Multi-Currency Behavior:** When an existing account has no transactions in the requested currency, the endpoint returns HTTP 200 with zeroed financial metrics and a list of `available_currencies` transacted by that account.

#### 6. Deterministic Unusual Spending Detection
- **Statistical Outlier Heuristic:** Identifies unusual debit activity by comparing individual debit transactions against the account's historical debit median ($M_{\text{debit}}$) within the requested reporting window.
- **Threshold Rule:** Flags transactions where $\text{amount} \ge \text{ROUND}(M_{\text{debit}} \times \text{multiplier}, 2)$ using an inclusive threshold and `ROUND_HALF_UP` arithmetic. Multiplier is configurable between 1.5 and 10.0 (default 3.0).
- **Outlier Metrics:** Reports account debit median, applied threshold, deviation ratio ($\text{amount} / M_{\text{debit}}$), total outlier count before pagination, and paginated outlier records sorted by amount descending.

### 11.2 Role-Based Access Policy
- Protected financial analytics endpoints are accessible by authenticated users with roles: `ADMIN`, `ANALYST`, and `INVESTIGATOR`.
- Nonexistent source namespaces return HTTP 404 (`NAMESPACE_NOT_FOUND`).
- Invalid parameters (malformed namespaces, non-ISO currencies, inverted date intervals, unsupported intervals/timezones, pagination overflows) return HTTP 422 with structured validation error codes.

### 11.3 Phase Boundary Distinctions
- **Phase 5 (Implemented):** Deterministic SQL aggregates, exact monetary calculations, calendar trend bucketing, and statistical median-based outlier filtering.
- **Phase 6 (Implemented):** Sliding-window behavioral feature engineering producing the validated 34-feature `FeatureVector` under `FEATURE_VERSION = "v1.0"`.
- **Phase 7 (Implemented):** Machine learning anomaly detection via `IsolationForestModel`, chronological partitioning with equal-timestamp grouping, validation-only threshold tuning under an operational alert-rate cap ($\le 5\%$), pre-deserialization SHA-256 integrity verification, and active model promotion.
- **Phase 8 (Implemented):** Hybrid risk scoring combining normalized unsupervised ML anomaly scores with deterministic financial heuristics into a 0–100 composite risk score, risk-tier mapping (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), structured explainable risk factors, and protected API endpoints with atomic PostgreSQL persistence and audit logging.
- **Phase 9 (Deferred):** Case management, alert triage, evidence attachment, and investigator resolution workflows.

---

## 12. Behavioral Intelligence

FinSignal should create behavioral features that describe how an account normally behaves.

Potential features include:

**Amount-Based**

- Historical mean amount
- Historical median amount
- Amount deviation
- Amount z-score
- Amount percentile

**Velocity-Based**

- Transactions in the last 5 minutes
- Transactions in the last hour
- Transactions in the last 24 hours

**Merchant-Based**

- Merchant frequency
- New merchant indicator
- Merchant deviation from historical behavior

**Device-Based**

- Known device indicator
- New device indicator
- Device frequency

**Location-Based**

- Known location indicator
- New location indicator
- Location frequency
- Distance from normal location where appropriate

**Temporal**

- Hour of day
- Day of week
- Weekend indicator
- Unusual activity hour

**Category-Based**

- Category frequency
- Category spending deviation
- New category indicator

Behavioral features should be generated from historical information available before or at the transaction being evaluated.

---

## 13. Risk and Anomaly Detection

FinSignal should initially use a hybrid approach.

### 13.1 Rule-Based Signals

Simple deterministic signals may identify obvious deviations such as:

- Extremely high transaction velocity
- New device
- New location
- Unusual activity time
- Large deviation from account behavior

Rules provide interpretable evidence.

### 13.2 Machine Learning

An anomaly detection model identifies multivariate combinations and patterns that are difficult to capture through simple deterministic rules.

Phase 7 implements unsupervised anomaly detection via `IsolationForestModel` (`n_estimators=100`, `random_state=42`), producing continuous anomaly scores:

$$S(X) = - \text{score\_samples}(X)$$

Operating decision thresholds are tuned on validation data subject to an operational alert-rate budget ($\le 5\%$). Future supervised models may be evaluated against this anomaly-detection baseline.

### 13.3 Risk Score (Phase 8 Implemented)

The system produces an investigation prioritization risk score via a hybrid formula combining normalized machine learning anomaly scores and deterministic financial heuristics:

$$\text{raw} = (w_{\text{ml}} \cdot S_{\text{norm}}) + (w_{\text{rule}} \cdot S_{\text{rule}})$$

- **Default Weights:** $w_{\text{ml}} = 0.60$ (60% ML anomaly weight), $w_{\text{rule}} = 0.40$ (40% heuristic rule weight).
- **Score Bounds:** Clamped strictly to $[0.00, 100.00]$ and rounded to 2 decimal places.
- **Risk Severity Tiers:**
  - $0.00 \le \text{score} < 25.00 \implies \textbf{LOW}$
  - $25.00 \le \text{score} < 50.00 \implies \textbf{MEDIUM}$
  - $50.00 \le \text{score} < 75.00 \implies \textbf{HIGH}$
  - $75.00 \le \text{score} \le 100.00 \implies \textbf{CRITICAL}$

The score is an **investigation prioritization score**, not a probability of fraud:

```text
Risk Score: 68.50 / 100.00
Risk Level: HIGH
```

The score must never be described as "68.50% probability of fraud" because it reflects multidimensional anomalousness and policy indicators rather than posterior fraud probability.

---

## 14. Risk Factors (Phase 8 Implemented)

Every evaluated transaction produces structured, evidence-based explainability factors persisted in PostgreSQL (`risk_factors`).

Phase 8 implements 9 standardized factor codes:
1. `COLD_START_ACCOUNT` (`INFO`, 0 pts) — Account history $< 5$ transactions; prevents false amount penalties.
2. `HIGH_VELOCITY` (`MEDIUM`: 15, `HIGH`: 25, `CRITICAL`: 40 pts) — Velocity surges within 1h or 24h windows.
3. `LARGE_AMOUNT_DEVIATION` (`MEDIUM`: 15, `HIGH`: 25, `CRITICAL`: 40 pts) — Significant amount z-score deviation.
4. `NEW_DEVICE` (`MEDIUM`: 15, `HIGH`: 25 pts) — Unrecognized device; escalates if shared across accounts.
5. `NEW_LOCATION` (`MEDIUM`: 15, `HIGH`: 25 pts) — Unrecognized location; escalates on international transactions.
6. `UNUSUAL_TIME` (`LOW`: 5, `MEDIUM`: 15 pts) — Activity outside normal hours; escalates during late night (01:00–05:00).
7. `BEHAVIORAL_SHIFT` (`MEDIUM`: 15, `HIGH`: 25 pts) — Trailing spending surge vs 30-day baseline.
8. `NEW_MERCHANT` (`LOW`: 5 pts) — First transaction with merchant on account.
9. `NEW_CATEGORY` (`LOW`: 5 pts) — First transaction in category (suppressed if `BEHAVIORAL_SHIFT` active).

Risk factors are strictly derived from observable transaction and account feature data, guaranteeing traceable and unhallucinated explanations.

---

## 15. Investigation Workflow (Phase 9 Implemented)

FinSignal implements a manual-first investigation workflow for flagged or suspicious transactions.

Key workflow characteristics:
- **Manual-First Case Creation:** Analysts, Investigators, and Admins can create an investigation by specifying a primary transaction ID, priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and optional initial notes. Automated risk-triggered case creation is deferred to a future phase.
- **Shared Investigation Queue:** Newly created cases enter an unassigned shared triage queue (`assigned_to = NULL`, `status = OPEN`). All authenticated roles (`ADMIN`, `INVESTIGATOR`, `ANALYST`) can inspect the queue.
- **Role-Based Assignment:** Investigators can self-assign unassigned cases or unassign themselves. Admins have global assignment authority. Investigators cannot take a case assigned to a peer or reassign cases across peers.
- **Primary Transaction Association:** Every successfully committed investigation is atomically associated with exactly one `PRIMARY` transaction. A transaction may serve as the primary subject of multiple investigations.
- **1-Hop Related Transactions:** Investigators and Admins can link related transactions within the same `source_namespace` that satisfy a direct 1-hop shared-party relationship (matching primary account or counterparty account). Recursive graph traversal is out of scope.

Workflow progression:

```text
Flagged / Suspicious Transaction
        |
        v
Create Investigation (Manual-First: Analyst / Investigator / Admin)
        |
        v
Shared Queue (Unassigned, Status: OPEN)
        |
        v
Case Assignment (Self-Assign by Investigator or Admin Assignment)
        |
        v
Under Review (Status: UNDER_REVIEW)
        |
        +---> Review Workspace & Primary Transaction Context
        +---> Discover & Link 1-Hop Related Transactions
        +---> Attach Append-Only Evidence Snapshots
        |
        v
AI Summary Generation (Phase 10 Implemented)
        |
        v
Human Decision & Resolution (Admin / Assigned Investigator)
        |
        v
Resolved Case (Status: RESOLVED - Permanently Immutable)
```

---

## 16. Investigation Status (Phase 9 Implemented)

Investigations follow a strict, unidirectional 3-state lifecycle:

```text
OPEN ──> UNDER_REVIEW ──> RESOLVED
```

Lifecycle rules:
1. `OPEN`: Initial state upon creation. Indicates the case is awaiting triage or assignment.
2. `UNDER_REVIEW`: Active investigation state. Occurs upon investigator assignment or start of active review.
3. `RESOLVED`: Terminal state representing completed review. Once resolved, the investigation record, linked transactions, and attached evidence are permanently immutable across all roles, including Admins.

Backward transitions (e.g., `RESOLVED -> UNDER_REVIEW` or `UNDER_REVIEW -> OPEN`) are strictly prohibited.

---

## 17. Investigation Resolution (Phase 9 Implemented)

An investigation in `UNDER_REVIEW` status can be resolved by an Admin or the assigned Investigator into one of four standardized outcomes:

```text
LEGITIMATE
SUSPICIOUS
CONFIRMED_FRAUD
INCONCLUSIVE
```

Resolution rules:
- **Mandatory Notes:** Resolution requires meaningful, non-whitespace explanation notes (`chk_investigations_resolution_state`).
- **Decoupled from ML Scores:** The human resolution represents an authoritative operational decision and is strictly decoupled from automated ML anomaly scores and risk tiers.
- **Terminal Immutability:** Resolving a case locks the record against all further mutation, assignment changes, related transaction additions, and evidence attachments.

---

## 18. Investigation Evidence (Phase 9 Implemented)

FinSignal captures structured, append-only evidence snapshots attached to investigations.

Supported evidence types and their source entities:

| Evidence Type | Permitted Source Type | Scope & Description |
|---|---|---|
| `TRANSACTION_FACT` | `TRANSACTION` | Observable transaction record snapshot |
| `RISK_SCORE` | `RISK_ANALYSIS` | ML composite score, tier, and execution metadata |
| `RISK_FACTOR` | `RISK_FACTOR` | Rule-based explainability factor record |
| `ACCOUNT_PROFILE` | `ACCOUNT` | Account details, KYC status, and risk classification |
| `DEVICE_PROFILE` | `DEVICE` | Fingerprint, client type, and trust score |
| `USER_NOTE` | `USER_NOTE` | Freeform investigator note (source_id must be NULL) |

Evidence guarantees:
- **Append-Only & Immutable:** Evidence records lack `updated_at`. Modifying or deleting evidence is rejected by database trigger `trg_no_update_delete_evidence`.
- **Payload Bounded:** Evidence snapshots support arbitrary structured JSON up to 64 KB per item.
- **Scope Validated:** Referenced sources are strictly validated to belong to the investigation's account or linked transactions.

---

## 19. AI Investigation Assistant

The AI Investigation Assistant generates structured, evidence-grounded briefing summaries for human investigators based on the assembled investigation context.

The AI layer outputs structured JSON conforming strictly to the `AISummaryOutput` schema:

```json
{
  "executive_summary": "High-level summary of the investigation context, anomaly indicators, and transacting entities.",
  "observed_facts": [
    {
      "claim": "Primary transaction amount of $5,000.00 USD is significantly above the account's historical debit median of $120.00 USD.",
      "evidence_ids": ["7c9e6679-7425-40de-944b-e07fc1f90ae7"]
    }
  ],
  "derived_signals": [
    {
      "claim": "Rule risk factor high_velocity triggered due to 3 subsequent transfers within 5 minutes.",
      "evidence_ids": ["123e4567-e89b-12d3-a456-426614174000"]
    }
  ],
  "potential_interpretations": [
    "Possible account takeover (ATO) followed by rapid fund extraction.",
    "Potential legitimate emergency transfer pending cardholder verification."
  ],
  "uncertainties_and_limitations": [
    "No historical device footprint available prior to 24 hours ago.",
    "Counterparty account belongs to an external banking network without internal observation history."
  ]
}
```

The AI assistant enforces a strict separation between:
- **Observed Facts:** Concrete empirical facts directly corroborated by supplied transaction and evidence records, accompanied by explicit evidence UUID citations.
- **Derived Signals:** Inferred risk indicators, rule factor triggers, and model anomaly scores with citations.
- **Potential Interpretations:** Fraud typologies or behavioral hypotheses presented as possibilities, never definitive conclusions.
- **Uncertainties and Limitations:** Explicit documentation of evidentiary gaps, missing records, or ambiguous signals.

### Context Grounding and Dual Fingerprints
- **Authoritative Evidence Hash (`evidence_hash`):** SHA-256 digest over canonical JSON containing all case facts, primary transaction attributes, risk analysis, risk factors, related transactions, evidence items, and account `status` and `account_type`. Mutating account standing (e.g., freezing the account) changes the evidence hash.
- **Context Hash (`context_hash`):** Separate SHA-256 digest over the bounded prompt context payload after applying item limits (`ai_max_evidence_items`) and byte budgets (`ai_max_context_bytes`).
- **Dynamic Staleness Detection:** When retrieving an AI summary via `GET`, the backend recomputes the authoritative evidence hash against the current database state. If underlying case facts, evidence, or account attributes have changed, `is_stale: true` is returned, alerting investigators that the summary was generated against an older snapshot.

---

## 20. AI Safety Boundaries

The AI assistant operates under strict advisory and containment boundaries:

**It MUST:**
- Use only supplied investigation evidence.
- Clearly distinguish facts from interpretations.
- Avoid unsupported claims and cite specific evidence UUIDs.
- Preserve transaction amounts and currency values accurately.
- Highlight gaps, missing data, and uncertainties openly.

**It MUST NOT:**
- Make final fraud determinations or classify investigations as `CONFIRMED_FRAUD` or `LEGITIMATE`.
- Alter investigation status, reassign cases, or modify evidence.
- Overwrite existing summaries silently (all historical generations are preserved in `ai_summaries`).
- Execute generation on terminal investigations (`RESOLVED` or `CLOSED` cases reject generation with HTTP 409 Conflict).
- Invent transactions, counterparties, or risk factors.

### Delimiter Defense-in-Depth & Grounding Limitations
- **Prompt Injection Defense-in-Depth:** Context is wrapped in cryptographic nonce tags (`<case_context nonce="{uuid}">`) with embedded closing tags escaped (`</` -> `<\u002F`). Instructions explicitly direct the model to treat all transaction descriptions, notes, and merchant names as untrusted data. *Note: Delimiter escaping is a defensive containment measure, not an absolute mathematical security boundary.*
- **Reference Existence vs. Semantic Truth:** Automated grounding validation checks that every cited UUID exists in the supplied case context. However, validating citation existence confirms entity reference integrity, not semantic truth; human review remains mandatory.
- **Provider Limitation:** The current release operates on `MockAIProvider` with simulated latency and fault injection; live external LLM provider integrations remain deferred.

---

## 21. Authentication and Authorization

FinSignal should require authenticated access to protected functionality.

The initial authorization model should support role-based access.

Potential roles:

```text
ADMIN
ANALYST
INVESTIGATOR
```

Example conceptual permissions:

| Capability | Admin | Analyst | Investigator |
|---|:---:|:---:|:---:|
| Login | ✓ | ✓ | ✓ |
| Import Dataset | ✓ | ✓ | - |
| View Analytics | ✓ | ✓ | ✓ |
| Run Analysis | ✓ | ✓ | - |
| View Alerts | ✓ | ✓ | ✓ |
| Create Investigation | ✓ | ✓ | ✓ |
| Review Investigation | ✓ | - | ✓ |
| Resolve Investigation | ✓ | - | ✓ |
| Manage Users | ✓ | - | - |

Exact authorization rules will be finalized in `SECURITY.md` and `TRD.md`.

---

## 22. Dataset Strategy

FinSignal will initially use a synthetic transaction dataset designed specifically for behavioral analysis and fraud investigation.

The dataset should model realistic financial behavior rather than generating uniformly random transactions.

The initial target scale is approximately:

- 5,000 accounts
- 500 merchants
- 8,000 devices
- 100 locations
- 250,000 transactions
- Approximately 3% fraud/anomalous ground-truth activity

These values are targets rather than hard product limits.

Development should begin with smaller datasets before scaling.

---

## 23. Synthetic Behavioral Profiles

Accounts should have distinct behavioral profiles.

Examples include:

**Low-Spending Account**

- Low transaction amounts
- Moderate transaction frequency
- Food/grocery-heavy behavior

**Moderate-Spending Account**

- Moderate transaction values
- Shopping/food/travel activity
- Moderate transaction frequency

**High-Spending Account**

- Higher transaction values
- Travel/electronics/shopping
- Lower transaction frequency

**Subscription-Heavy Account**

- Recurring transactions
- Utilities/subscriptions
- Predictable spending patterns

**Business-Like Account**

- Higher transaction volume
- Larger amounts
- Broader merchant distribution
- More transfers

The purpose is to ensure that the system learns account-specific normal behavior.

---

## 24. Fraud / Anomaly Scenarios

The synthetic dataset should contain multiple behavioral scenarios.

Initial scenarios include:

```text
F001 - Large Amount Anomaly
F002 - New Device
F003 - New Location
F004 - Unusual Transaction Time
F005 - High Transaction Velocity
F006 - Account Takeover Pattern
F007 - Behavioral Spending Shift
```

Fraud scenarios should vary in complexity.

Some should involve:

- One unusual signal
- Multiple signals
- Sequential transactions
- Account-level behavioral changes

Not every fraudulent transaction should be trivially identifiable from a single feature.

---

## 25. Legitimate Unusual Activity

The dataset must contain legitimate transactions that appear unusual.

Examples:

- Salary credit
- Annual insurance payment
- Rent
- Flight or hotel purchase
- Hospital payment
- Large electronics purchase
- Legitimate travel
- Large business transaction

This is important because:

> **Unusual does not automatically mean fraudulent.**

These cases are necessary to evaluate false positives and prevent the model from learning simplistic rules such as:

```text
Large transaction = fraud
```

---

## 26. Ground Truth

Synthetic ground truth may contain fields such as:

```text
is_fraud
fraud_scenario
scenario_instance_id
```

These fields exist for:

- Model evaluation
- Dataset validation
- Scenario analysis
- Testing

They must never be exposed as production model features.

Ground-truth fields must not create direct or indirect data leakage into model training or inference.

---

## 27. Evaluation Philosophy

Because fraudulent activity is expected to represent a small minority of transactions, accuracy alone is not an appropriate primary metric.

FinSignal should evaluate:

- Precision
- Recall
- F1 score
- PR-AUC
- False-positive rate
- False-negative rate
- Alert volume
- Scenario-level detection
- Account-level detection
- Investigation workload

The system should consider whether the resulting alerts are useful to a human investigator, not merely whether a model achieves a high mathematical score.

---

## 28. Temporal Evaluation

Financial behavior is inherently time-dependent.

Where appropriate, datasets should use time-based splits instead of random row splitting.

Example:

```text
January - June   → Training
July - August    → Validation
September        → Test
```

This helps evaluate whether the system can generalize to future activity.

Random splits may be used for specific experiments, but temporal evaluation should be the primary evaluation strategy for production-oriented modeling.

---

## 29. Functional Requirements

| ID | Requirement | Description |
|---|---|---|
| **FR-001** | User Authentication | The system shall allow users to authenticate securely. |
| **FR-002** | Role-Based Access | The system shall restrict protected functionality based on user role. |
| **FR-003** | Dataset Import | The system shall allow authorized users to import transaction datasets. |
| **FR-004** | Data Validation | The system shall validate imported transaction data before analysis. |
| **FR-005** | Data Quality Reporting | The system shall report detected data-quality issues. |
| **FR-006** | Data Cleaning | The system shall normalize and clean valid transaction data. |
| **FR-007** | Transaction Analytics | The system shall provide financial analytics over processed transactions. |
| **FR-008** | Account Behavioral Analysis | The system shall calculate behavioral characteristics for accounts. |
| **FR-009** | Risk Analysis | The system shall calculate anomaly/risk scores for applicable transactions. |
| **FR-010** | Risk Factors | The system shall provide interpretable risk factors for flagged activity. |
| **FR-011** | Investigation Creation | The system shall allow suspicious activity to become an investigation. |
| **FR-012** | Investigation Evidence | The system shall assemble contextual evidence for investigations. |
| **FR-013** | AI Summary | The system shall support AI-generated investigation summaries based on structured evidence. |
| **FR-014** | Human Resolution | The system shall allow authorized investigators to record investigation resolutions. |
| **FR-015** | Auditability | Important investigation and analysis actions should be traceable. |

---

## 30. Non-Functional Requirements

### NFR-001 — Reliability

The system should produce deterministic results where deterministic processing is expected.

Synthetic dataset generation must support a configurable random seed.

### NFR-002 — Explainability

Risk outputs should expose interpretable contributing signals whenever possible.

### NFR-003 — Security

Authentication credentials, tokens, and sensitive application data must be handled securely.

### NFR-004 — Data Integrity

Financial transaction facts must not be silently modified in ways that compromise analysis.

### NFR-005 — Reproducibility

Dataset generation and ML experiments should be reproducible.

### NFR-006 — Testability

Core data processing, analytics, API, authentication, investigation, and ML components should be testable independently.

### NFR-007 — Scalability

The architecture should support increasing dataset sizes without requiring a fundamental redesign.

The initial system does not need to be optimized for massive-scale production workloads.

### NFR-008 — Observability

Important processing failures, analysis operations, and application errors should be observable through appropriate logging and diagnostics.

---

## 31. MVP Scope

The MVP should include:

**Platform**

- User authentication
- Role-based authorization
- REST API
- PostgreSQL persistence
- Dockerized development environment

**Data**

- CSV transaction import
- Schema validation
- Data cleaning
- Data-quality reporting
- Synthetic dataset generator

**Analytics**

- Transaction analytics
- Account analytics
- Merchant analytics
- Category analytics
- Temporal analytics

**Behavioral Intelligence**

- Account behavioral baselines
- Behavioral feature generation
- Historical comparisons

**Risk Detection**

- Rule-based risk signals
- Initial anomaly detection model
- Risk score
- Risk level
- Structured risk factors

**Investigation (Phase 9 Implemented)**

- Manual-first investigation creation and atomic PRIMARY transaction binding
- Shared triage queue with deterministic pagination and filtering
- Role-based assignment rules (Admin global, Investigator self-assign/self-unassign)
- Direct 1-hop related transaction discovery and linking (4-way shared-party predicate)
- Append-only immutable evidence snapshot storage (6 evidence types, 64 KB JSONB payload, DB trigger enforcement)
- Strict 3-state lifecycle (`OPEN` -> `UNDER_REVIEW` -> `RESOLVED`)
- Human resolution (4 outcomes, mandatory notes, terminal immutability)

**AI (Phase 10 Implemented)**

- Dedicated `src/finsignal/ai/` domain package
- Structured evidence-grounded investigation summary (`AISummaryOutput` schema)
- Two-transaction lifecycle with `REPEATABLE READ` snapshot isolation and CAS token fencing
- Expired pending generation lazy recovery with atomic audit logging
- Provider abstraction (`BaseAIProvider`) with deterministic `MockAIProvider`
- Dual cryptographic fingerprinting (`evidence_hash`, `context_hash`) including account `status` and `account_type`
- Dynamic staleness detection on `GET` and force refresh on `POST`
- Protected REST API endpoints (`POST`, `GET` latest, `GET` history)
- Strict advisory-only boundary and citation grounding validation

---

## 32. Deferred Features

The following features are intentionally deferred:

- Automatic risk-triggered investigation creation (manual-first creation implemented in Phase 9)
- Multi-hop / recursive transaction graph traversal
- Real-time transaction streaming
- Kafka
- Real-time alerting
- Advanced graph fraud detection
- Graph neural networks
- RAG
- Large-scale vector search
- Autonomous AI investigation
- Automated fraud decisions
- MLflow-based experiment management
- Advanced model serving infrastructure
- External banking integrations
- Production regulatory compliance
- Mobile application
- Multi-tenant SaaS architecture

These may be introduced only when justified by project requirements.

---

## 33. Success Criteria

FinSignal will be considered successful when a user can complete the following workflow:

```text
1. Authenticate
        ↓
2. Import a transaction dataset
        ↓
3. Validate and clean the data
        ↓
4. Inspect data-quality results
        ↓
5. View financial analytics
        ↓
6. Generate behavioral features
        ↓
7. Run anomaly/risk analysis
        ↓
8. Identify flagged activity
        ↓
9. Open a flagged transaction
        ↓
10. Understand why it was flagged
        ↓
11. Review account and transaction history
        ↓
12. Examine structured evidence
        ↓
13. Generate an AI investigation summary
        ↓
14. Make a human investigation decision
        ↓
15. Record the final resolution
```

The system should demonstrate that the model is not merely producing scores, but that those scores can be turned into useful investigation context.

---

## 34. Product Principles

FinSignal should follow these principles throughout development.

### Principle 1 — Context Over Scores

A risk score without context is not enough.

### Principle 2 — Unusual Does Not Mean Fraud

Anomaly detection identifies deviations, not guilt.

### Principle 3 — Account Behavior Matters

Normal behavior differs between accounts.

### Principle 4 — Evidence Before Explanation

AI explanations should be generated from structured evidence.

### Principle 5 — Human in the Loop

The final investigation decision belongs to the investigator.

### Principle 6 — Separate Facts from Intelligence

Raw transaction facts must remain distinguishable from:

- Derived features
- Risk scores
- Model outputs
- AI-generated interpretations
- Human decisions

### Principle 7 — Reproducibility

Data generation, feature engineering, and ML experiments should be reproducible.

### Principle 8 — Build for Extension, Not Premature Complexity

The architecture should leave room for future capabilities without introducing unnecessary infrastructure into the MVP.

---

## 35. High-Level Product Architecture

At the product level, FinSignal consists of the following logical areas:

```text
                    +----------------------+
                    |      FinSignal       |
                    +----------+-----------+
                               |
          +--------------------+--------------------+
          |                    |                    |
          v                    v                    v
   Data Management       Intelligence        Investigation
          |                    |                    |
          |                    |                    |
   Import / Validate     Analytics           Alerts
   Clean / Enrich        Features            Evidence
                         ML Risk             AI Summary
                         Detection           Resolution
          |                    |                    |
          +--------------------+--------------------+
                               |
                               v
                         PostgreSQL
```

This is a product-level view only.

Detailed technical architecture will be defined in `TRD.md` and `ARCHITECTURE.md`.

---

## 36. Traceability to Future Documentation

This PRD defines product behavior and scope.

Detailed decisions belong in the following documents:

| Concern | Document |
|---|---|
| Product requirements | `PRD.md` |
| Dataset structure | `DATASET_SPECIFICATION.md` |
| Technical requirements | `TRD.md` |
| System architecture | `ARCHITECTURE.md` |
| Database schema | `DATABASE_DESIGN.md` |
| ML design | `ML_DESIGN.md` |
| API contracts | `API_GUIDELINES.md` |
| Security | `SECURITY.md` |
| Coding conventions | `CODING_STANDARDS.md` |
| Testing | `TESTING_STRATEGY.md` |
| Development phases | `PROJECT_ROADMAP.md` |
| Architectural decisions | `DECISIONS.md` |
| Development history | `PROJECT_LOG.md` |

Frontend-specific documentation will be created later when frontend implementation begins.

---

## 37. Document Status

| Field | Value |
|---|---|
| **Current Version** | 1.0.0 |
| **Status** | Draft |
| **Next Document** | `DATASET_SPECIFICATION.md` |

The PRD should be reviewed before implementation-specific documentation is finalized.

Any major change to product scope should be reflected here first and then propagated to the relevant technical documents.