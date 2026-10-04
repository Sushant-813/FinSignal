# FinSignal
## System Architecture

**Product:** FinSignal  
**Full Name:** Financial Transaction Intelligence & Investigation Platform  
**Document:** System Architecture  
**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2026-10-04

---

# 1. Purpose

This document defines the high-level and detailed architectural structure of FinSignal.

The architecture translates the requirements defined in:

- `PRD.md`
- `DATASET_SPECIFICATION.md`
- `TRD.md`

into a coherent system design.

The architecture must support:

- Secure user authentication
- Dataset ingestion
- Data validation and cleaning
- Financial analytics
- Behavioral feature generation
- Machine-learning-based risk detection
- Investigation workflows
- Evidence assembly
- AI-assisted investigation summaries
- Human investigation decisions
- PostgreSQL persistence
- Future extensibility

The initial architecture intentionally uses a **modular monolith** rather than a distributed microservice architecture.

---

# 2. Architectural Principles

FinSignal should follow these principles throughout implementation.

## 2.1 Domain Separation

Different business responsibilities should have clear boundaries.

Examples:

```text
Authentication
Transactions
Analytics
Risk Detection
Investigations
AI
```

---

## 2.2 Raw Facts vs Derived Intelligence

The architecture must clearly distinguish:

```text
Raw Financial Facts
        |
        v
Derived Features
        |
        v
Risk Intelligence
        |
        v
Investigation Evidence
        |
        v
Human Decision
```

Raw transaction facts must not be overwritten by derived intelligence.

---

## 2.3 Human-in-the-Loop

The architecture must preserve human control over investigation decisions.

The system may:

- Detect anomalies
- Assign risk
- Assemble evidence
- Generate explanations

But the investigator determines the final resolution.

---

## 2.4 Explainability

Risk outputs should be accompanied by structured signals and evidence wherever possible.

---

## 2.5 Temporal Correctness

Behavioral features and ML predictions must respect the temporal ordering of financial transactions.

Future information must never leak into historical features.

---

## 2.6 Reproducibility

Dataset generation, feature generation, and ML analysis should be reproducible.

---

## 2.7 Simplicity First

The MVP should use the simplest architecture capable of satisfying the product requirements.

Distributed infrastructure should only be introduced when justified.

---

## 2.8 Replaceable ML and AI Components

ML models and LLM providers should be replaceable without redesigning the rest of the system.

---

# 3. Architectural Style

FinSignal will initially use a:

> **Modular Monolithic Architecture**

The backend is deployed as one application while maintaining strong internal module boundaries.

Conceptually:

```text
                    +----------------------+
                    |      React UI        |
                    +----------+-----------+
                               |
                               | HTTPS / REST
                               v
                    +----------------------+
                    |      FastAPI         |
                    |   Modular Backend    |
                    +----------+-----------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
  Application              Intelligence          Investigation
    Modules                  Modules                 Modules
       |                       |                       |
       +-----------------------+-----------------------+
                               |
                               v
                        +--------------+
                        |  PostgreSQL  |
                        +--------------+
```

---

# 4. Why a Modular Monolith

A modular monolith is preferred for the initial version because:

- The project is still evolving.
- ML and analytics require rapid iteration.
- Deployment is simpler.
- Local development is easier.
- Transactions and investigations benefit from shared database transactions.
- Distributed infrastructure would add unnecessary complexity.
- Module boundaries can still be enforced internally.

The architecture should remain capable of extracting individual components later if scale requires it.

---

# 5. High-Level System

The system consists of the following major areas:

```text
+----------------------------------------------------------+
|                      FinSignal                           |
+----------------------------------------------------------+
|                                                          |
|  +----------------+       +---------------------------+  |
|  |   React UI     | <---> |      FastAPI Backend      |  |
|  +----------------+       +-------------+-------------+  |
|                                         |                |
|       +----------------+----------------+---------------+|
|       |                |                |                |
|       v                v                v                v
|   Auth & Users    Data Platform    Intelligence    Investigation
|                         |                |                |
|                         |                |                |
|                         +----------------+----------------+
|                                         |
|                                         v
|                                  +-------------+
|                                  | PostgreSQL  |
|                                  +-------------+
|                                                          |
+----------------------------------------------------------+
```

---

# 6. External Interfaces

FinSignal initially interacts with:

```text
User
  |
  v
React Frontend
  |
  v
FastAPI REST API
```

External AI providers may be integrated through an abstraction layer.

The initial system does not directly integrate with:

- Banks
- Payment processors
- Core banking systems
- Kafka streams
- External fraud databases

---

# 7. Logical Architecture

The backend is organized into logical layers.

```text
+------------------------------------------------------+
|                    API Layer                         |
| Routers / Request Validation / Authentication        |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|                  Application Layer                   |
| Services / Use Cases / Workflow Orchestration        |
+------------------------------------------------------+
                         |
                         v
+------------------------------------------------------+
|                    Domain Layer                      |
| Business Rules / Models / Policies / Calculations    |
+------------------------------------------------------+
                         |
              +----------+----------+
              |                     |
              v                     v
+-------------------------+  +-------------------------+
|    Data Access Layer    |  | Intelligence Layer      |
| Repositories / Queries  |  | Features / ML / AI      |
+------------+------------+  +------------+------------+
             |                           |
             +-------------+-------------+
                           |
                           v
                    +--------------+
                    | PostgreSQL   |
                    +--------------+
```

---

# 8. API Layer

The API layer is responsible for:

- HTTP routing
- Authentication dependency handling
- Authorization checks
- Request validation
- Response serialization
- Pagination
- API error mapping

API routes should not contain complex business logic.

Example:

```text
POST /api/v1/auth/login
POST /api/v1/datasets
GET  /api/v1/transactions
GET  /api/v1/risk-alerts
GET  /api/v1/investigations/{id}
POST /api/v1/investigations/{id}/resolve
```

Exact endpoint definitions belong in:

`API_GUIDELINES.md`

---

# 9. Application Layer

The application layer coordinates use cases.

Potential services:

```text
AuthService
DatasetService
TransactionService
AnalyticsService
FeatureService
RiskAnalysisService
InvestigationService
EvidenceService
AIService
```

Services should coordinate domain logic and repositories.

---

# 10. Domain Layer

The domain layer contains business concepts and rules.

Potential domain concepts:

```text
User
Account
Merchant
Device
Location
Transaction
RiskAnalysis
RiskFactor
Investigation
Evidence
AISummary
```

The domain layer should remain independent of HTTP concerns.

---

# 11. Data Access Layer

The data access layer is responsible for PostgreSQL interaction.

Responsibilities include:

- Queries
- Inserts
- Updates
- Filtering
- Pagination
- Aggregation
- Transaction management where appropriate

Repositories should not contain high-level business workflows.

---

# 12. Intelligence Layer

The intelligence layer contains:

```text
Data Processing
Feature Engineering
Analytics
Risk Detection
ML Models
```

The intelligence layer should remain independently testable.

---

# 13. Investigation Layer

The investigation layer connects:

```text
Risk Alert
    |
    v
Investigation
    |
    v
Evidence
    |
    v
AI Summary
    |
    v
Human Resolution
```

The investigation system should not directly modify raw transaction facts.

---

# 14. Core Modules

The initial backend may use the following modules:

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

Module names may evolve during implementation.

---

# 15. Authentication Module

Responsibilities:

- User registration
- Password hashing
- Login
- JWT generation
- JWT validation
- Current-user retrieval
- Role checks

Authentication should be isolated from domain-specific transaction logic.

---

# 16. User Module

Responsibilities:

- User persistence
- User retrieval
- Role management
- Account status
- Administrative operations

User records should not be confused with financial accounts.

---

# 17. Account Module

Responsibilities:

- Account metadata
- Account retrieval
- Account status
- Account behavioral context
- Account-level analytics

The account module should not store mutable ML risk scores directly.

---

# 18. Transaction Module

Responsibilities:

- Transaction persistence
- Transaction retrieval
- Filtering
- Historical queries
- Transaction details

Transaction data represents observed financial facts.

---

# 19. Merchant Module

Responsibilities:

- Merchant metadata
- Merchant retrieval
- Merchant statistics
- Merchant-related transaction analysis

---

# 20. Device Module

Responsibilities:

- Device metadata
- Device-account relationships
- Device history
- New-device detection support

---

# 21. Location Module

Responsibilities:

- Location metadata
- Account-location relationships
- Location history
- New-location detection support

---

# 22. Ingestion Module

Responsibilities:

- Dataset upload
- File validation
- Schema validation
- Record validation
- Data cleaning
- Normalization
- Enrichment
- Persistence

Conceptual pipeline:

```text
Upload
  |
  v
Validate File
  |
  v
Validate Schema
  |
  v
Validate Records
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
Persist
```

---

# 23. Analytics Module

Responsibilities:

- Transaction analytics
- Account analytics
- Category analytics
- Merchant analytics
- Temporal analytics
- Aggregations

Analytics should be available independently of the ML pipeline.

---

# 24. Feature Engineering Module

Responsibilities:

- Historical feature calculation
- Behavioral baselines
- Transaction velocity
- Amount deviation
- Merchant behavior
- Device behavior
- Location behavior
- Temporal features
- Category behavior

The module must enforce temporal correctness.

---

# 25. Risk Module

Responsibilities:

- Rule-based risk signals
- ML anomaly detection
- Risk score calculation
- Risk-level mapping
- Model version tracking
- Risk-factor generation

Conceptual flow:

```text
Features
   |
   +--------> Rule Signals
   |
   +--------> ML Model
                 |
                 v
          Anomaly Score
                 |
                 v
           Risk Analysis
                 |
                 v
           Risk Factors
```

---

# 26. Investigation Module

Responsibilities:

- Investigation creation
- Investigation retrieval
- Investigation status
- Investigation priority
- Investigation resolution
- Investigator notes where supported
- Investigation history

Possible states:

```text
OPEN
UNDER_REVIEW
RESOLVED
```

---

# 27. Evidence Module

Responsibilities:

- Evidence collection
- Evidence normalization
- Evidence persistence
- Evidence retrieval
- Evidence traceability

Evidence should be generated from trusted system data.

---

# 28. AI Module

Responsibilities:

- AI provider abstraction
- Investigation context construction
- Prompt/input construction
- AI invocation
- Output validation
- Summary persistence

The AI module must not independently query arbitrary database records.

---

# 29. Dataset Module

Responsibilities:

- Synthetic dataset generation
- Dataset configuration
- Dataset versioning
- Seed management
- Dataset validation
- Dataset statistics

The dataset generator should remain separate from production transaction ingestion logic.

---

# 30. Common Module

The common module may contain genuinely shared functionality such as:

- Error definitions
- Shared enums
- Common response structures
- Logging helpers
- Configuration
- Utility functions

The common module must not become a dumping ground for unrelated application logic.

---

# 31. Data Flow

The primary data flow is:

```text
CSV Dataset
    |
    v
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
PostgreSQL
    |
    +------------------+
    |                  |
    v                  v
Analytics         Feature Generation
                       |
                       v
                  Risk Analysis
                       |
              +--------+--------+
              |                 |
              v                 v
          Low Risk         High Risk
                                |
                                v
                          Investigation
                                |
                                v
                             Evidence
                                |
                                v
                           AI Summary
                                |
                                v
                         Human Resolution
```

---

# 32. Dataset Ingestion Flow

```text
User
 |
 | Upload CSV
 v
API
 |
 v
Dataset Service
 |
 v
Validation Pipeline
 |
 +---- Invalid ----> Data Quality Report
 |
 v
Cleaning
 |
 v
Normalization
 |
 v
Enrichment
 |
 v
Persistence
 |
 v
Dataset Ready
```

---

# 33. Analytics Flow

```text
PostgreSQL
    |
    v
Analytics Service
    |
    +---- Transaction Metrics
    |
    +---- Account Metrics
    |
    +---- Category Metrics
    |
    +---- Merchant Metrics
    |
    +---- Temporal Metrics
    |
    v
API Response
    |
    v
Frontend
```

---

# 34. Risk Analysis Flow

```text
Transaction History
        |
        v
Historical Feature Generation
        |
        v
Feature Vector
        |
        +------------------+
        |                  |
        v                  v
Rule Engine         Isolation Forest
        |                  |
        +--------+---------+
                 |
                 v
           Risk Calculation
                 |
                 v
           Risk Analysis
                 |
                 v
            Risk Factors
```

---

# 35. Investigation Flow

```text
Risk Analysis
     |
     | exceeds investigation threshold
     v
Investigation
     |
     v
Evidence Assembly
     |
     +---- Transaction
     +---- Account History
     +---- Behavioral Context
     +---- Device
     +---- Location
     +---- Merchant
     +---- Related Transactions
     +---- Risk Factors
     |
     v
Investigation Context
     |
     v
AI Summary
     |
     v
Investigator
     |
     v
Resolution
```

---

# 36. AI Data Flow

The AI system should receive structured evidence.

```text
Database
    |
    v
Evidence Service
    |
    v
Investigation Context
    |
    v
AI Provider Interface
    |
    v
LLM
    |
    v
Structured / Validated Summary
    |
    v
AI Summary Storage
```

The LLM should not receive unrestricted database access.

---

# 37. AI Provider Abstraction

The application should use a provider interface.

Conceptually:

```text
                +----------------------+
                |   AI Provider        |
                |     Interface        |
                +----------+-----------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
        Provider A    Provider B    Future Provider
```

This prevents the core application from being tightly coupled to one provider.

---

# 38. Database Architecture

PostgreSQL is the authoritative application datastore.

Conceptual structure:

```text
+----------------------------------------------------+
|                    PostgreSQL                      |
+----------------------------------------------------+
|                                                    |
|  Identity                                          |
|  ├── users                                         |
|                                                    |
|  Financial Facts                                   |
|  ├── accounts                                      |
|  ├── merchants                                     |
|  ├── devices                                       |
|  ├── locations                                     |
|  └── transactions                                  |
|                                                    |
|  Intelligence                                      |
|  ├── risk_analyses                                 |
|  └── risk_factors                                  |
|                                                    |
|  Investigation                                     |
|  ├── investigations                                |
|  ├── investigation_evidence                        |
|  └── ai_summaries                                  |
|                                                    |
+----------------------------------------------------+
```

Detailed schema design belongs in:

`DATABASE_DESIGN.md`

---

# 39. Raw Data Boundary

Raw financial facts should be immutable from the perspective of downstream intelligence.

For example:

```text
Transaction
    |
    +-- amount
    +-- timestamp
    +-- merchant
    +-- device
    +-- location
```

Derived properties should not overwrite these values.

---

# 40. Derived Intelligence Boundary

Derived information should be stored separately.

Examples:

```text
Risk Score
Risk Level
Risk Factors
Behavioral Features
AI Summary
```

This allows reprocessing without changing source facts.

---

# 41. Human Decision Boundary

Human decisions should be stored separately from model output.

```text
Model:
Risk = HIGH

Investigator:
Resolution = LEGITIMATE
```

Both values may be correct.

The architecture must not assume that:

```text
HIGH RISK == CONFIRMED FRAUD
```

---

# 42. Temporal Feature Architecture

Historical features should use time-aware queries.

Conceptually:

```text
Transaction T at time t
        |
        v
Historical Data <= t
        |
        v
Feature Calculation
        |
        v
Risk Analysis
```

Future records must not enter the feature calculation.

---

# 43. Deterministic Ordering

Historical transaction queries should use deterministic ordering.

Recommended:

```sql
ORDER BY timestamp ASC, transaction_id ASC
```

This ensures stable behavior when transactions share identical timestamps.

---

# 44. Transactional Boundaries

Operations that modify related records should use database transactions where atomicity is required.

Example:

```text
Create Investigation
       |
       +---- Investigation record
       +---- Initial evidence
       +---- Audit event
```

These should either succeed together or fail together where business requirements require atomicity.

---

# 45. Concurrency

The system must account for concurrent updates to mutable investigation state.

Example:

```text
Investigator A
       |
       v
Investigation OPEN
       |
       +----------------+
                        |
                        v
                 Investigator B
                        |
                        v
                  RESOLVED
```

The implementation should prevent stale updates from silently overwriting newer state.

The exact optimistic/pessimistic concurrency strategy will be defined in `DATABASE_DESIGN.md`.

---

# 46. API-to-Database Boundary

API handlers should not directly manipulate database entities.

Recommended:

```text
Router
  |
  v
Service
  |
  v
Repository
  |
  v
Database
```

This preserves testability and separation of concerns.

---

# 47. ML-to-Database Boundary

The ML pipeline should not directly manipulate API-layer objects.

Recommended:

```text
Risk Service
     |
     v
Feature Service
     |
     v
Model Adapter
     |
     v
Model
     |
     v
Risk Result
     |
     v
Risk Repository
```

---

# 48. Security Architecture

Conceptual security flow:

```text
User
 |
 v
Login
 |
 v
Password Verification
 |
 v
JWT Issued
 |
 v
Frontend
 |
 | Authorization: Bearer <token>
 v
FastAPI
 |
 v
JWT Validation
 |
 v
Role Authorization
 |
 v
Protected Service
```

Secrets must be managed through environment configuration or an appropriate secret-management system.

---

# 49. Authorization Boundary

Authorization should occur before business operations execute.

Example:

```text
Request
  |
  v
Authentication
  |
  v
Authorization
  |
  +---- Denied
  |
  v
Service
```

Business services should not assume that any authenticated user has unrestricted access.

---

# 50. File Processing Security

Dataset uploads must be treated as untrusted input.

The ingestion system should:

- Validate file type
- Enforce size limits
- Validate schema
- Avoid unsafe file execution
- Use temporary storage
- Clean up temporary files
- Prevent path traversal
- Reject malformed input safely

---

# 51. Deployment Architecture

Initial deployment target:

```text
                Internet
                    |
                    v
             React Frontend
                    |
                    | HTTPS
                    v
             FastAPI Backend
                    |
                    | PostgreSQL
                    v
               PostgreSQL
```

The exact cloud providers are intentionally not locked in at this stage.

---

# 52. Local Development Architecture

Docker Compose may provide:

```text
+-------------------+
| frontend          |
+-------------------+

+-------------------+
| backend           |
+-------------------+

+-------------------+
| postgres          |
+-------------------+
```

All services should communicate through the Docker network.

---

# 53. Environment Configuration

Environment configuration should distinguish:

```text
Development
Testing
Production
```

Configuration should include:

```text
DATABASE_URL
JWT_SECRET
JWT_EXPIRATION
APP_ENV
LOG_LEVEL
AI_PROVIDER
AI_MODEL
```

Actual values must not be committed to source control.

---

# 54. Observability Architecture

Initial observability should include:

- Structured application logs
- Request logging
- Error logging
- Dataset-processing logs
- ML-processing logs
- Investigation operation logs

Future enhancements may include:

- Metrics
- Distributed tracing
- Centralized log aggregation

These are not required for MVP.

---

# 55. Failure Handling

Failures should be isolated by processing stage.

Example:

```text
Validation Failure
        |
        v
Data Quality Report

ML Failure
        |
        v
Risk Analysis Error

AI Failure
        |
        v
Investigation remains available
without AI summary
```

AI failure must not make the core investigation system unusable.

---

# 56. AI Failure Isolation

The AI layer is an enhancement to the investigation workflow, not a hard dependency for investigation integrity.

If the AI provider is unavailable:

```text
Investigation
     |
     +---- Evidence available
     |
     +---- AI Summary unavailable
```

The investigator must still be able to review evidence and resolve the investigation.

---

# 57. ML Failure Isolation

If ML analysis fails:

- Raw transactions remain intact.
- Analytics remain available where possible.
- Existing risk analyses remain intact.
- The system should report the analysis failure.
- The failure should not corrupt source transaction data.

---

# 58. Scalability Strategy

The initial architecture should scale vertically before introducing distributed services.

Potential progression:

```text
Phase 1
Modular Monolith
       |
       v
Phase 2
Background Processing
       |
       v
Phase 3
Dedicated ML Worker
       |
       v
Phase 4
Streaming / Distributed Processing
```

These phases are conditional rather than mandatory.

---

# 59. Future Service Extraction

Potential future services could include:

```text
Ingestion Service
Analytics Service
ML/Risk Service
Investigation Service
AI Service
```

However, these should only be extracted when justified by:

- Scale
- Deployment independence
- Resource isolation
- Team boundaries
- Reliability requirements

---

# 60. Future Real-Time Architecture

If real-time monitoring is introduced later:

```text
Transaction Source
       |
       v
Kafka
       |
       v
Stream Processing
       |
       v
Feature Generation
       |
       v
Risk Engine
       |
       v
Alert Service
       |
       v
Investigation
```

This is explicitly outside the initial MVP.

---

# 61. Future Graph Architecture

If network fraud analysis is introduced:

```text
Accounts
   |
   +---- Transfers
   |
   +---- Shared Devices
   |
   +---- Shared Locations
   |
   +---- Shared Merchants
   |
   v
Graph Representation
   |
   v
Network Analysis
```

The current schema should preserve enough relationships to support this later.

---

# 62. Future RAG Architecture

If investigation knowledge retrieval is introduced later:

```text
Investigation
      |
      v
Evidence
      |
      v
Retriever
      |
      v
Relevant Knowledge
      |
      v
LLM
      |
      v
Investigation Summary
```

RAG is deferred from MVP.

---

# 63. Frontend Boundary

The frontend should be treated as a separate client.

```text
React
   |
   | REST / JSON
   v
FastAPI
```

The frontend should not directly access PostgreSQL.

All application data should flow through backend APIs.

---

# 64. Frontend State Responsibilities

The frontend is responsible for:

- UI state
- Authentication state
- Request state
- Presentation
- User interactions

The backend remains authoritative for:

- Financial calculations
- Risk scores
- Behavioral features
- Investigation evidence
- Investigation resolution state

The frontend must not independently recalculate authoritative financial or risk values.

---

# 65. Data Ownership

The backend owns:

```text
Transactions
Accounts
Analytics
Risk Analyses
Investigations
Evidence
AI Summaries
```

The frontend consumes these through APIs.

---

# 66. API Contract Stability

The backend should provide stable response schemas.

Breaking changes should be controlled through:

- API versioning
- Explicit schema changes
- Documentation
- Tests

---

# 67. Architectural Constraints

The following constraints are mandatory for the initial architecture:

1. PostgreSQL is the authoritative database.
2. FastAPI is the backend API framework.
3. ML runs within the Python backend initially.
4. Raw transactions remain distinct from risk outputs.
5. Risk analysis remains distinct from investigation resolution.
6. AI cannot independently determine fraud.
7. Future information must not leak into historical features.
8. Ground-truth fraud labels must not enter production features.
9. Frontend cannot directly access the database.
10. Distributed infrastructure is not required for MVP.

---

# 68. Architecture Decision Summary

| Decision | Choice |
|---|---|
| Architecture | Modular Monolith |
| Backend | FastAPI |
| Language | Python |
| Database | PostgreSQL |
| Data Processing | Pandas / NumPy |
| ML | scikit-learn |
| Authentication | JWT |
| Authorization | RBAC |
| Frontend | React + TypeScript |
| API | REST |
| Containerization | Docker |
| Initial ML Deployment | Same backend |
| Streaming | Deferred |
| Kafka | Deferred |
| Celery | Deferred |
| Redis | Deferred |
| MLflow | Deferred |
| Graph ML | Deferred |
| RAG | Deferred |

---

# 69. Architecture Acceptance Criteria

The architecture will be considered successfully implemented when:

### AC-001

The backend is organized as a modular monolith.

### AC-002

API, service, domain, and data-access responsibilities are separated.

### AC-003

PostgreSQL is the authoritative datastore.

### AC-004

Authentication and authorization are isolated from transaction processing.

### AC-005

Dataset ingestion follows validation and cleaning stages.

### AC-006

Feature generation respects temporal boundaries.

### AC-007

ML outputs are separated from raw transaction data.

### AC-008

Investigation state is separated from model output.

### AC-009

AI receives structured evidence rather than unrestricted database access.

### AC-010

AI failure does not prevent investigation workflows from functioning.

### AC-011

The architecture supports the target dataset scale.

### AC-012

The architecture leaves clear extension points for future streaming and graph capabilities.

---

# 70. Relationship to Other Documents

| Concern | Document |
|---|---|
| Product requirements | `PRD.md` |
| Dataset specification | `DATASET_SPECIFICATION.md` |
| Technical requirements | `TRD.md` |
| System architecture | `ARCHITECTURE.md` |
| Database schema | `DATABASE_DESIGN.md` |
| ML design | `ML_DESIGN.md` |
| API contracts | `API_GUIDELINES.md` |
| Security | `SECURITY.md` |
| Coding standards | `CODING_STANDARDS.md` |
| Testing | `TESTING_STRATEGY.md` |
| Roadmap | `PROJECT_ROADMAP.md` |
| Architectural decisions | `DECISIONS.md` |
| Development history | `PROJECT_LOG.md` |

---

# 71. Document Status

**Version:** 1.0.0  
**Status:** Draft  
**Previous Document:** `TRD.md`  
**Next Document:** `DATABASE_DESIGN.md`

This document defines the architectural structure that the FinSignal implementation must follow.
