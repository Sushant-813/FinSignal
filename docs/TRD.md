# FinSignal
## Technical Requirements Document (TRD)

**Product:** FinSignal  
**Full Name:** Financial Transaction Intelligence & Investigation Platform  
**Document:** Technical Requirements Document  
**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-10-04

---

# 1. Purpose

This document defines the technical requirements and implementation direction for FinSignal.

The PRD defines **what FinSignal should accomplish**.

This document defines the technical constraints and engineering requirements for **how those capabilities should be implemented**.

The technical design must support:

- Financial transaction ingestion
- Data validation and cleaning
- Behavioral feature generation
- Financial analytics
- Machine-learning-based anomaly detection
- Risk scoring
- Investigation workflows
- Evidence generation
- AI-assisted investigation summaries
- JWT authentication
- Role-based authorization
- PostgreSQL persistence
- REST APIs
- Reproducible ML experiments
- Containerized development

The architecture should remain modular without introducing infrastructure that is not justified by the current product scope.

---

# 2. Technical Goals

The implementation should satisfy the following goals:

1. Use Python as the primary backend and data/ML language.
2. Provide a clean REST API through FastAPI.
3. Use PostgreSQL as the primary relational database.
4. Keep analytics and ML capabilities within the Python backend initially.
5. Separate raw financial facts from derived intelligence.
6. Prevent data leakage during feature generation and model evaluation.
7. Provide deterministic and reproducible data generation.
8. Keep ML components independently testable.
9. Provide secure JWT-based authentication.
10. Provide role-based authorization.
11. Support Docker-based local development.
12. Keep future expansion possible without premature distributed architecture.

---

# 3. Technology Stack

## 3.1 Backend

**Language:** Python

**Framework:** FastAPI

FastAPI is responsible for:

- HTTP APIs
- Request validation
- Authentication integration
- Authorization
- Service orchestration
- API documentation
- Error handling

---

## 3.2 Database

**Database:** PostgreSQL

PostgreSQL is the primary persistent datastore.

It will store:

- Users
- Accounts
- Merchants
- Devices
- Locations
- Transactions
- Risk analyses
- Risk factors
- Investigations
- Investigation evidence
- AI summaries
- Other application metadata

PostgreSQL is preferred because FinSignal combines relational data with time-oriented transaction analysis and may later benefit from PostgreSQL extensions such as `pgvector`.

---

## 3.3 Data Processing

Initial data-processing technologies:

- Pandas
- NumPy

Pandas should be used for:

- Dataset ingestion
- Cleaning
- Transformation
- Aggregation
- Exploratory analysis
- Feature preparation

NumPy should be used where numerical operations benefit from array-based computation.

---

## 3.4 Machine Learning

**Primary ML framework:** scikit-learn

Initial ML capabilities may include:

- Isolation Forest
- Standard preprocessing
- Feature scaling
- Model evaluation
- Classification metrics
- Model persistence where appropriate

The initial architecture should not require a dedicated ML serving platform.

---

## 3.5 Frontend

The frontend will use:

- React
- TypeScript
- Vite
- Tailwind CSS
- Apache ECharts

The frontend is intentionally not covered in detail by this document.

Frontend-specific technical documentation will be created during the frontend phase.

The backend must expose stable API contracts that allow the frontend to be developed independently.

---

## 3.6 Authentication

Authentication will use:

- JWT access tokens
- Secure password hashing
- Role-based authorization

Exact JWT and password-hashing libraries will be finalized during implementation based on current Python ecosystem support.

---

## 3.7 Testing

Backend testing:

- pytest
- pytest-asyncio where asynchronous behavior requires it
- FastAPI testing utilities
- Database integration tests where appropriate

ML/data testing:

- pytest
- deterministic test datasets
- metric-based evaluation
- feature validation tests

Frontend testing will be documented separately.

---

## 3.8 Containerization

Docker will be used for reproducible local development.

The initial environment should support:

```text
Frontend
Backend
PostgreSQL
```

A background worker should only be introduced if asynchronous processing becomes necessary.

---

# 4. Python Environment and Dependency Management

The project should use a modern Python environment and dependency-management workflow.

`uv` is the preferred package and environment management tool unless implementation constraints require another approach.

The project should define:

- Python version
- Runtime dependencies
- Development dependencies
- Test dependencies
- Linting/formatting dependencies
- Dependency lock information

The Python version should be pinned to a supported version selected during implementation.

---

# 5. High-Level Architecture

The initial system should use a modular monolithic backend.

```text
                        +----------------------+
                        |      React UI        |
                        +----------+-----------+
                                   |
                                   | HTTPS / REST
                                   v
                        +----------------------+
                        |      FastAPI         |
                        +----------+-----------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
       Authentication        Application         Data / ML
       & Authorization         Services            Services
              |                    |                    |
              |            +-------+-------+            |
              |            |       |       |            |
              |            v       v       v            |
              |        Analytics Investigation  Feature/ML
              |                    |                    |
              +--------------------+--------------------+
                                   |
                                   v
                           +---------------+
                           |  PostgreSQL   |
                           +---------------+
```

The initial system should avoid splitting the backend into separate microservices.

---

# 6. Modular Monolith Requirement

FinSignal should be implemented as a modular monolith initially.

Logical modules should have clear responsibilities and boundaries.

Potential modules:

```text
auth
user
account
merchant
device
location
transaction
ingestion
analytics
feature
risk
investigation
evidence
ai
dataset
common
```

Modules may evolve as implementation progresses.

The purpose of modular boundaries is to make future extraction possible if genuinely required.

---

# 7. Backend Layering

The backend should use clear application layers.

Recommended conceptual structure:

```text
API / Router
    |
    v
Service
    |
    v
Domain / Business Logic
    |
    v
Repository / Data Access
    |
    v
PostgreSQL
```

Data-processing and ML workflows may have additional layers:

```text
Ingestion
    |
    v
Validation
    |
    v
Cleaning
    |
    v
Enrichment
    |
    v
Feature Engineering
    |
    v
Model / Risk Analysis
```

API routes should not directly contain complex ML or database logic.

---

# 8. API Requirements

FinSignal should expose RESTful APIs.

General API principles:

- Resource-oriented URLs
- JSON request/response bodies
- HTTP status codes used correctly
- Consistent error responses
- Request validation
- Authentication on protected endpoints
- Authorization where required
- Pagination for large collections
- Explicit API versioning strategy

The exact API contract will be documented in `API_GUIDELINES.md`.

---

# 9. API Versioning

The initial API should use a versioned base path.

Recommended:

```text
/api/v1
```

Example:

```text
/api/v1/auth/login
/api/v1/accounts
/api/v1/transactions
/api/v1/investigations
```

Breaking changes should require a new API version.

---

# 10. Authentication Requirements

FinSignal shall provide secure user authentication.

Required capabilities:

- User registration where enabled
- Login
- Password hashing
- JWT access-token generation
- Current-user retrieval
- Protected endpoints
- Role-based access control

Passwords must never be stored in plaintext.

---

# 11. JWT Requirements

JWTs should contain only information required for authentication and authorization.

Potential claims:

```text
sub
role
iat
exp
jti
```

The token should have an explicit expiration time.

Sensitive information must not be embedded in the JWT payload.

---

# 12. Token Lifecycle

The authentication design must define:

- Access-token lifetime
- Token signing algorithm
- Signing-key configuration
- Token validation
- Expiration handling
- Invalid-token handling
- Logout/invalidation strategy

The exact implementation will be finalized in `SECURITY.md`.

---

# 13. Password Security

Passwords must be hashed using a modern password-hashing algorithm supported by the Python ecosystem.

Requirements:

- Never store plaintext passwords.
- Never log passwords.
- Never return password hashes through APIs.
- Use appropriate password-hashing parameters.
- Validate password input securely.

---

# 14. Role-Based Authorization

The initial role model is:

```text
ADMIN
ANALYST
INVESTIGATOR
```

Authorization should be enforced at the application layer.

Example:

```text
ADMIN
  |
  +-- User management
  +-- Dataset management
  +-- Analytics
  +-- Investigations

ANALYST
  |
  +-- Dataset import
  +-- Analytics
  +-- Risk analysis
  +-- Alert review

INVESTIGATOR
  |
  +-- Alert review
  +-- Investigation management
  +-- Evidence review
  +-- Investigation resolution
```

Exact permissions will be defined in `SECURITY.md`.

---

# 15. Database Requirements

PostgreSQL must be the authoritative persistent datastore for application state.

The database must preserve the distinction between:

### Source Facts

Examples:

- Transaction
- Account
- Merchant
- Device
- Location

### Derived Intelligence

Examples:

- Behavioral features
- Risk analysis
- Risk factors
- Investigation evidence
- AI summaries

### Human Decisions

Examples:

- Investigation status
- Investigation resolution
- Investigator notes

---

# 16. Database Migration

Database schema changes should be managed through version-controlled migrations.

Migrations must be:

- Ordered
- Reproducible
- Reviewable
- Applied consistently across environments

The specific migration framework will be selected during implementation.

---

# 17. Core Database Entities

The initial logical model includes:

```text
users
accounts
merchants
devices
locations
transactions
risk_analyses
risk_factors
investigations
investigation_evidence
ai_summaries
```

Additional tables may be introduced where justified.

Detailed schema definitions belong in:

`DATABASE_DESIGN.md`

---

# 18. Transaction Data Model

The transaction model should preserve raw financial facts.

Core fields include:

```text
transaction_id
account_id
timestamp
amount
currency
transaction_type
merchant_id
category
location_id
device_id
payment_method
channel
```

Risk scores must not be stored directly as mutable properties of the raw transaction entity.

Risk analysis belongs in a separate representation.

---

# 19. Risk Analysis Model

Risk analysis should be stored separately from transactions.

Conceptual fields:

```text
risk_analysis_id
transaction_id
model_version
score
risk_level
created_at
```

This separation allows:

- Multiple model versions
- Re-analysis
- Model comparison
- Historical risk results
- Auditable model output

---

# 20. Risk Factors

Structured risk factors should be represented separately where appropriate.

Example:

```text
risk_analysis
      |
      +---- amount_deviation
      +---- new_device
      +---- new_location
      +---- unusual_time
      +---- transaction_velocity
```

Each factor should be explainable and traceable to the underlying evidence.

---

# 21. Investigation Model

An investigation should be associated with suspicious activity.

Conceptual fields:

```text
investigation_id
transaction_id
status
priority
created_at
updated_at
resolution
```

An investigation may later support relationships to multiple transactions if the investigation concerns a broader behavioral pattern.

---

# 22. Investigation Evidence

Evidence should represent structured information used by investigators and the AI assistant.

Possible evidence types:

```text
TRANSACTION
ACCOUNT_HISTORY
BEHAVIORAL_DEVIATION
DEVICE
LOCATION
MERCHANT
VELOCITY
RELATED_TRANSACTION
RISK_FACTOR
MODEL_OUTPUT
```

Evidence should preserve its source where practical.

---

# 23. AI Summary Storage

AI-generated investigation summaries should be stored separately from the evidence.

Conceptual fields:

```text
ai_summary_id
investigation_id
provider
model
summary
generated_at
```

The system should retain enough metadata to understand which model/provider generated a summary.

---

# 24. Data Ingestion Architecture

The ingestion pipeline should follow:

```text
CSV Upload
    |
    v
File Validation
    |
    v
Schema Validation
    |
    v
Record Validation
    |
    v
Data Quality Report
    |
    v
Cleaning / Normalization
    |
    v
Enrichment
    |
    v
Persistence
```

Invalid records should be handled according to documented ingestion policy.

---

# 25. Ingestion Requirements

The ingestion system must:

1. Validate file format.
2. Validate required columns.
3. Validate data types.
4. Validate required values.
5. Validate identifiers.
6. Validate foreign-key references.
7. Detect duplicate transaction IDs.
8. Validate timestamps.
9. Validate monetary values.
10. Produce data-quality results.
11. Prevent invalid data from silently entering the production dataset.

---

# 26. Data Quality Reporting

The ingestion process should report:

- Total records received
- Valid records
- Invalid records
- Duplicate records
- Missing fields
- Invalid values
- Invalid references
- Cleaning operations performed
- Records rejected

The system should make the difference between:

```text
Rejected
Cleaned
Accepted
```

clear to the user.

---

# 27. Data Processing Pipeline

The processing pipeline should conceptually be:

```text
Raw
 |
 v
Validate
 |
 v
Clean
 |
 v
Normalize
 |
 v
Enrich
 |
 v
Feature Engineering
 |
 v
Analytics / ML
```

Each stage should have a defined contract.

---

# 28. Feature Engineering Requirements

Feature engineering must respect temporal ordering.

For transaction `T` at time `t`:

```text
Features(T) = f(history <= t)
```

Future information must not be used.

Where a feature is explicitly historical, it should use only information available before the prediction/evaluation point.

---

# 29. Behavioral Feature Categories

The initial feature pipeline should support:

### Amount Features

- Historical mean
- Historical median
- Amount deviation
- Z-score
- Percentile

### Velocity Features

- Transactions in 5 minutes
- Transactions in 1 hour
- Transactions in 24 hours

### Merchant Features

- Merchant frequency
- New merchant indicator
- Merchant spending deviation

### Device Features

- Known device indicator
- New device indicator
- Device frequency

### Location Features

- Known location indicator
- New location indicator
- Location frequency

### Temporal Features

- Hour
- Day of week
- Weekend
- Unusual hour

### Category Features

- Category frequency
- Category spending deviation
- New category

---

# 30. Financial Analytics Requirements

Analytics should be implemented independently from risk scoring where possible.

Supported analytics include:

- Transaction volume
- Debit volume
- Credit volume
- Average transaction value
- Median transaction value
- Category distribution
- Merchant distribution
- Temporal trends
- Account-level spending
- Transaction frequency

Analytics should not depend on the ML model being available.

---

# 31. ML Architecture

The initial ML architecture should remain inside the Python backend.

Conceptually:

```text
Transaction Data
      |
      v
Feature Engineering
      |
      v
Feature Matrix
      |
      v
Anomaly Model
      |
      v
Anomaly Score
      |
      v
Risk Mapping
      |
      v
Risk Analysis
```

A separate ML microservice is not required for the initial version.

---

# 32. Initial ML Model

Isolation Forest is the preferred initial anomaly-detection baseline.

Reasons:

- Suitable for anomaly detection
- Available in scikit-learn
- Does not require fully labeled training data
- Can work with multidimensional behavioral features
- Provides a strong baseline for experimentation

The model should not be treated as the final fraud classifier.

---

# 33. Hybrid Detection

The initial risk system should combine:

```text
Deterministic Signals
        +
ML Anomaly Detection
        |
        v
Risk Analysis
```

Rules provide interpretable evidence.

ML provides detection of less-obvious behavioral combinations.

The exact score-combination strategy belongs in `ML_DESIGN.md`.

---

# 34. Model Versioning

Every stored risk analysis should identify the model version.

Example:

```text
model_version = isolation_forest_v1
```

A future analysis may use:

```text
isolation_forest_v2
```

This enables model comparison and historical reproducibility.

---

# 35. ML Training Requirements

Training pipelines must:

- Use approved feature sets.
- Exclude ground-truth leakage.
- Respect temporal splits.
- Record configuration.
- Record model version.
- Record feature definitions.
- Produce evaluation metrics.
- Support reproducibility.

---

# 36. ML Evaluation

Primary evaluation metrics should include:

- Precision
- Recall
- F1
- PR-AUC
- False-positive rate
- False-negative rate
- Alert volume
- Scenario-level detection
- Account-level detection

Accuracy must not be treated as the primary success metric because fraud is intentionally imbalanced.

---

# 37. Model Evaluation Dataset

The evaluation process should use time-aware data splits.

Example:

```text
Training:
January - June

Validation:
July - August

Testing:
September
```

The exact period will be determined by the generated dataset.

---

# 38. Investigation Trigger

A transaction may become investigation-worthy when its calculated risk exceeds a configured threshold.

Conceptually:

```text
Risk Score
    |
    +---- Low -----> No Investigation
    |
    +---- Medium --> Review / Optional Investigation
    |
    +---- High ----> Investigation Candidate
```

Thresholds must be configurable.

Risk score alone must not be treated as proof of fraud.

---

# 39. Evidence Assembly

When an investigation is created, the system should assemble relevant evidence.

Potential sources:

- Transaction details
- Account history
- Behavioral statistics
- Similar transactions
- Merchant history
- Device history
- Location history
- Velocity
- Risk factors
- Model output

Evidence generation should be deterministic where possible.

---

# 40. AI Integration

The AI layer should be provider-agnostic.

The application should use an abstraction similar to:

```text
Investigation Evidence
        |
        v
AI Provider Interface
        |
        +---- Provider A
        |
        +---- Provider B
        |
        +---- Future Provider
```

The core investigation system should not be tightly coupled to one LLM vendor.

---

# 41. AI Input Contract

The LLM should receive structured investigation context rather than unrestricted database access.

Conceptually:

```json
{
  "transaction": {},
  "account_context": {},
  "risk_analysis": {},
  "risk_factors": [],
  "related_transactions": [],
  "behavioral_summary": {}
}
```

The exact schema will be defined later.

---

# 42. AI Output Requirements

AI output should:

- Summarize evidence
- Explain important signals
- Mention relevant historical comparisons
- Identify uncertainty
- Avoid unsupported claims
- Preserve numerical facts

The output should not modify source evidence.

---

# 43. AI Guardrails

The AI integration must prevent:

- Unsupported factual claims
- Fabricated transactions
- Fabricated evidence
- Risk-score modification
- Autonomous fraud decisions
- Hidden access to unrelated user data

The final investigation decision remains human-controlled.

---

# 44. Background Processing

The initial system should prefer synchronous processing for operations that can reasonably complete within normal API request limits.

Background processing should be introduced only for tasks that are:

- Long-running
- Resource-intensive
- Failure-prone
- Not appropriate for request/response execution

Potential future infrastructure:

```text
Celery + Redis
```

This is not required for the initial MVP.

---

# 45. Real-Time Processing

Real-time streaming is explicitly deferred.

The initial architecture will not require Kafka.

Future real-time architecture may become:

```text
Transaction Stream
       |
       v
Kafka
       |
       v
Feature Processing
       |
       v
Risk Detection
       |
       v
Alerting
```

This should only be introduced if the product scope later requires real-time transaction monitoring.

---

# 46. Caching

Caching should not be introduced prematurely.

PostgreSQL should remain the authoritative source.

A cache such as Redis may be introduced later for:

- Frequently accessed analytics
- Session-related workloads if required
- Background job infrastructure
- Expensive repeated computations

---

# 47. API Documentation

FastAPI's generated OpenAPI documentation should be enabled for development.

The project should provide:

```text
/docs
/redoc
```

in development environments.

Production exposure should be controlled according to security requirements.

---

# 48. Error Handling

The API should provide consistent error responses.

Conceptual format:

```json
{
  "error": {
    "code": "INVALID_TRANSACTION_DATA",
    "message": "Transaction amount must be positive.",
    "details": {}
  }
}
```

Errors should:

- Use appropriate HTTP status codes.
- Avoid leaking internal implementation details.
- Provide actionable messages where appropriate.
- Use stable application error codes.

---

# 49. Logging

The application should use structured logging where practical.

Logs should capture:

- Request context
- Important processing events
- Authentication failures
- Dataset processing failures
- ML processing failures
- Investigation operations
- Unexpected exceptions

Sensitive information must not be logged.

---

# 50. Configuration Management

Configuration must be environment-based.

Potential configuration categories:

```text
DATABASE_URL
JWT_SECRET
JWT_EXPIRATION
APPLICATION_ENV
LOG_LEVEL
AI_PROVIDER
AI_MODEL
MODEL_STORAGE_PATH
```

Secrets must not be committed to Git.

A `.env.example` file should document required configuration without exposing real secrets.

---

# 51. Environment Separation

At minimum, the system should distinguish:

```text
development
testing
production
```

Environment-specific configuration should not be hard-coded into application logic.

---

# 52. Docker Requirements

The project should provide Docker configuration suitable for local development.

Initial services:

```text
postgres
backend
frontend
```

The exact Compose configuration will be defined during implementation.

---

# 53. Database Persistence

Database data should survive container restarts through Docker volumes during local development.

The application should not depend on container-local database state.

---

# 54. Data Import Storage

Uploaded datasets should not be treated as permanent raw files by default.

The ingestion design should define:

- Temporary upload storage
- Validation
- Processing
- Persistence
- Cleanup

The exact storage mechanism will be finalized during architecture design.

---

# 55. File Size and Upload Limits

Dataset uploads should have configurable limits.

The system should reject files that exceed configured limits.

Limits should be selected based on the MVP dataset scale rather than assuming unrestricted uploads.

---

# 56. Pagination

Large API collections must use pagination.

Potential resources requiring pagination:

- Transactions
- Accounts
- Merchants
- Risk analyses
- Investigations
- Evidence
- Audit records

The exact pagination strategy will be documented in `API_GUIDELINES.md`.

---

# 57. Sorting and Filtering

Collection endpoints should support controlled filtering and sorting where appropriate.

Examples:

```text
transaction date range
account
merchant
category
risk level
investigation status
investigation resolution
```

Filtering should use indexed database fields where appropriate.

---

# 58. Database Indexing

Indexes should be created based on access patterns.

Likely indexed fields include:

- Transaction account ID
- Transaction timestamp
- Transaction ID
- Merchant ID
- Device ID
- Location ID
- Risk analysis transaction ID
- Investigation transaction ID
- Investigation status

Composite indexes may be used where query patterns justify them.

Indexes should not be added indiscriminately.

---

# 59. Transaction Ordering

Financial transaction queries that are used for historical behavior should have deterministic ordering.

Where timestamps can be equal, a stable secondary key such as transaction ID should be used.

Conceptually:

```text
ORDER BY timestamp ASC, transaction_id ASC
```

This is important for reproducibility and temporal feature generation.

---

# 60. Concurrency Requirements

The system should protect against inconsistent concurrent updates to investigations and other mutable application state.

Potential concurrency-sensitive operations include:

- Investigation resolution
- Investigation status updates
- Dataset processing state
- Model analysis jobs

The exact transaction/isolation strategy will be defined in `DATABASE_DESIGN.md`.

---

# 61. Auditability

Important user actions should be auditable.

Potential events:

- Login
- Dataset import
- Risk analysis execution
- Investigation creation
- Investigation update
- Investigation resolution
- AI summary generation

The audit implementation will be finalized in the architecture and security documentation.

---

# 62. Security Requirements

The implementation must:

- Hash passwords securely.
- Protect JWT signing secrets.
- Validate authorization on protected endpoints.
- Validate all user input.
- Prevent SQL injection through parameterized data access.
- Prevent unsafe file processing.
- Restrict access to investigations based on authorization.
- Avoid exposing ground truth.
- Avoid leaking secrets through logs.
- Protect AI provider credentials.

Detailed security requirements belong in `SECURITY.md`.

---

# 63. Testing Requirements

The project must use multiple testing layers.

## Unit Tests

Test:

- Domain logic
- Validators
- Feature calculations
- Risk-factor calculations
- Utility functions

## Integration Tests

Test:

- Database repositories
- Service/database interaction
- Authentication flows
- API endpoints

## ML Tests

Test:

- Feature consistency
- Leakage prevention
- Deterministic preprocessing
- Model training
- Metric calculations

## End-to-End Tests

Validate important product workflows.

Example:

```text
Login
  |
  v
Upload Dataset
  |
  v
Validate
  |
  v
Analyze
  |
  v
Flag Transaction
  |
  v
Create Investigation
  |
  v
Generate Summary
  |
  v
Resolve Investigation
```

---

# 64. Test Data

Tests should use small deterministic datasets.

Production-scale datasets should not be required for every test.

A dedicated test fixture strategy should exist for:

- Accounts
- Transactions
- Fraud scenarios
- Risk analyses
- Investigations

---

# 65. Code Quality

The project should enforce consistent Python code quality.

Recommended tooling may include:

- Ruff
- Formatting checks
- Type checking
- Import checks

The exact tool configuration will be finalized during implementation.

---

# 66. Type Safety

Python type hints should be used throughout application code where practical.

Public functions, service interfaces, data structures, and API schemas should have explicit types.

Type checking may be introduced using a tool such as:

```text
mypy
```

or an equivalent modern Python type checker.

---

# 67. API Schema Validation

Pydantic models should define API request and response schemas.

The application should avoid returning raw database models directly from API endpoints.

API schemas should explicitly define:

- Input fields
- Output fields
- Optional fields
- Validation rules
- Serialization behavior

---

# 68. Repository Requirements

Database access should be isolated from service logic.

Repositories should handle:

- Queries
- Persistence
- Retrieval
- Filtering
- Pagination

Business rules should remain in service/domain layers rather than repository implementations.

---

# 69. Service Requirements

Services should coordinate business workflows.

Examples:

```text
TransactionService
RiskAnalysisService
InvestigationService
DatasetService
AnalyticsService
AuthService
```

Services should not become uncontrolled collections of unrelated logic.

---

# 70. ML Service Boundary

ML-related logic should have a clear boundary from API routing.

Conceptually:

```text
Risk API
   |
   v
Risk Service
   |
   v
Feature Service
   |
   v
ML Model
```

This makes it possible to replace or compare models without rewriting API code.

---

# 71. Model Artifact Management

Initial model artifacts may be stored using a controlled local/object-storage-compatible mechanism.

The system should associate:

- Model version
- Training configuration
- Feature version
- Dataset version
- Training timestamp

Advanced experiment tracking such as MLflow is deferred until justified.

---

# 72. Performance Requirements

The MVP should prioritize correctness over premature optimization.

The system should nevertheless be designed to:

- Process the development dataset reliably.
- Handle approximately 250,000 transactions in the target dataset.
- Avoid loading unnecessarily large datasets into memory for every API request.
- Use database pagination.
- Use batch processing for large ingestion operations.
- Avoid repeated expensive calculations where persistence or caching is justified.

Exact performance targets will be established after profiling.

---

# 73. Batch Processing

Large dataset operations should use batch processing where appropriate.

Potential batch operations:

- Transaction ingestion
- Data cleaning
- Feature generation
- Risk analysis
- Dataset export

The batch size should be configurable.

---

# 74. Analytics Computation

Analytics may be computed using:

1. SQL aggregations for database-friendly operations.
2. Pandas for dataset-oriented processing.
3. Precomputed aggregates where repeated computation becomes expensive.

The implementation should choose the simplest approach that meets performance requirements.

---

# 75. ML Feature Storage

Feature storage strategy should be selected based on actual requirements.

The initial system may compute features during analysis rather than persisting every feature indefinitely.

If feature persistence is required, the feature schema must be versioned.

---

# 76. Data Lineage

Important derived outputs should be traceable to:

```text
Dataset
   |
   v
Processing Version
   |
   v
Feature Version
   |
   v
Model Version
   |
   v
Risk Analysis
   |
   v
Investigation
```

This allows results to be understood and reproduced.

---

# 77. Model and Dataset Compatibility

A model must not be used with incompatible feature definitions.

A risk-analysis execution should verify compatibility between:

- Dataset version
- Feature version
- Model version

where such metadata is available.

---

# 78. Frontend Integration Requirements

The backend must provide APIs sufficient for the future React frontend to implement:

- Authentication
- Dashboard analytics
- Transaction browsing
- Risk/alert browsing
- Investigation detail
- Evidence viewing
- AI summary viewing
- Investigation resolution

The backend should not depend on frontend-specific implementation details.

---

# 79. API Response Design

Responses should be designed for frontend consumption while preserving domain clarity.

Large nested payloads should be avoided when they cause unnecessary data transfer.

Complex investigation views may use dedicated aggregation endpoints rather than forcing the frontend to make excessive requests.

---

# 80. Health and Readiness

The backend should expose appropriate operational endpoints.

Potential endpoints:

```text
/health
/ready
```

Health checks should distinguish between:

- Application process health
- Dependency readiness

The exact implementation will be finalized later.

---

# 81. Deployment Model

The initial deployment architecture should support:

```text
React Frontend
       |
       v
FastAPI Backend
       |
       v
PostgreSQL
```

Docker should be used for reproducible local development.

Cloud deployment details will be addressed after the core system is implemented and tested.

---

# 82. Deferred Infrastructure

The following infrastructure is intentionally not required for MVP:

- Kafka
- Celery
- Redis
- MLflow
- Kubernetes
- Dedicated ML serving service
- Dedicated vector database
- Dedicated graph database
- Microservice decomposition

These technologies should only be introduced when a concrete requirement justifies them.

---

# 83. Technology Decision Principles

Technology choices should follow these principles:

1. Prefer simplicity.
2. Prefer well-supported open-source tooling.
3. Avoid unnecessary distributed infrastructure.
4. Keep components replaceable.
5. Optimize for correctness before scale.
6. Keep ML experimentation easy.
7. Preserve clear domain boundaries.
8. Avoid vendor lock-in where practical.

---

# 84. Technical Acceptance Criteria

The technical implementation should eventually satisfy:

### TR-001

The backend runs as a FastAPI application.

### TR-002

PostgreSQL is used as the authoritative application database.

### TR-003

Protected APIs require authentication.

### TR-004

Role-based authorization is enforced.

### TR-005

Transaction ingestion validates incoming data.

### TR-006

Data processing prevents temporal leakage.

### TR-007

Behavioral features are generated from valid historical information.

### TR-008

Risk analysis supports model versioning.

### TR-009

Risk factors are available for flagged activity.

### TR-010

Investigations can be created and resolved.

### TR-011

AI summaries use structured investigation evidence.

### TR-012

Ground-truth fraud fields cannot leak into production model features.

### TR-013

The system supports deterministic test datasets.

### TR-014

The application can process the target development and full dataset sizes.

### TR-015

The project can run through Docker-based local development.

---

# 85. Open Technical Decisions

The following decisions will be finalized in subsequent technical documents or during implementation:

1. Exact Python version.
2. Exact JWT library.
3. Exact password hashing library.
4. Exact ORM/data-access approach.
5. Exact migration framework.
6. Exact project package structure.
7. Exact model serialization strategy.
8. Exact AI provider.
9. Exact AI model.
10. Exact background-processing strategy.
11. Exact file-upload storage mechanism.
12. Exact database indexing strategy.
13. Exact feature persistence strategy.
14. Exact deployment platform.

These decisions should be recorded in `DECISIONS.md` when finalized.

---

# 86. Relationship to Other Documents

This document depends on the product requirements defined in:

`PRD.md`

and dataset requirements defined in:

`DATASET_SPECIFICATION.md`

The following documents will provide deeper technical detail:

| Concern | Document |
|---|---|
| Product requirements | `PRD.md` |
| Dataset | `DATASET_SPECIFICATION.md` |
| System architecture | `ARCHITECTURE.md` |
| Database schema | `DATABASE_DESIGN.md` |
| ML design | `ML_DESIGN.md` |
| API contracts | `API_GUIDELINES.md` |
| Security | `SECURITY.md` |
| Coding standards | `CODING_STANDARDS.md` |
| Testing | `TESTING_STRATEGY.md` |
| Roadmap | `PROJECT_ROADMAP.md` |
| Decisions | `DECISIONS.md` |
| Development history | `PROJECT_LOG.md` |

---

# 87. Document Status

**Version:** 1.0.0  
**Status:** Draft  
**Previous Document:** `DATASET_SPECIFICATION.md`  
**Next Document:** `ARCHITECTURE.md`

This document defines the technical requirements and implementation constraints that the FinSignal architecture must satisfy.
