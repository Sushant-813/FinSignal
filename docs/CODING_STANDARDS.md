# CODING_STANDARDS.md

# FinSignal — Coding Standards

## 1. Document Purpose

This document defines the coding standards for **FinSignal — Financial Transaction Intelligence & Investigation Platform**.

The purpose is to keep the codebase:

- readable
- predictable
- testable
- maintainable
- secure
- consistent
- easy to review
- suitable for future extension

The project combines:

```text
FastAPI
Python
PostgreSQL
Pandas
NumPy
scikit-learn
React (Frontend — DEFERRED)
TypeScript (Frontend — DEFERRED)
```

> [!NOTE]
> **Scope Boundary Notice:**
> Frontend implementation is intentionally **DEFERRED** until Backend + ML v1.0 is complete. Active implementation scope is strictly Backend + ML. All React and TypeScript guidelines in this document are preserved for future client implementation and must not be initiated during current development.

Therefore, these standards cover both backend/application code and the intelligence layer.

---

# 2. Core Engineering Principles

FinSignal follows these principles:

1. Prefer clarity over cleverness.
2. Keep business rules explicit.
3. Keep modules focused.
4. Separate concerns.
5. Prefer composition over unnecessary inheritance.
6. Make important behavior testable.
7. Do not duplicate domain rules.
8. Validate external input early.
9. Keep financial calculations server-authoritative.
10. Preserve temporal correctness in ML code.
11. Avoid premature abstraction.
12. Do not introduce infrastructure without measured need.

---

# 3. Python Version

The project should use a single explicitly supported Python version.

The selected version must be pinned/documented in project configuration.

All developers and CI environments should use the same supported version.

Avoid relying on implementation behavior specific to an unpinned local Python version.

---

# 4. Python Environment and Dependency Management

The preferred environment/tooling is:

```text
uv
```

Dependencies should be declared in the project's standard Python dependency configuration.

Do not install project dependencies manually into the global Python environment.

Development environments should be reproducible from the repository configuration.

---

# 5. Formatting

Python formatting should use:

```text
Black
```

or an equivalent formatter if the project later standardizes on another tool.

Formatting should be automated rather than manually negotiated.

The repository should use a consistent line length.

Recommended default:

```text
88 characters
```

unless project tooling establishes another standard.

---

# 6. Import Organization

Imports should be grouped as:

```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import APIRouter
from pydantic import BaseModel

# Local
from app.accounts.service import AccountService
```

Avoid wildcard imports:

```python
from module import *
```

Imports should be deterministic and automatically sortable where possible.

---

# 7. Naming Conventions

## Variables and functions

Use:

```text
snake_case
```

Example:

```python
risk_score
calculate_behavior_features()
```

## Classes

Use:

```text
PascalCase
```

Example:

```python
RiskAnalysisService
TransactionRepository
```

## Constants

Use:

```text
UPPER_SNAKE_CASE
```

Example:

```python
DEFAULT_PAGE_SIZE = 25
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
```

---

# 8. Boolean Naming

Boolean variables should read naturally.

Preferred:

```python
is_active
is_new_device
has_risk_factors
can_resolve
```

Avoid:

```python
active_flag
new_device_value
```

unless the domain specifically requires those names.

---

# 9. Type Hints

Type hints are required for public functions and important internal functions.

Preferred:

```python
def calculate_risk_score(
    anomaly_score: float,
    behavioral_score: float,
) -> float:
    ...
```

Avoid untyped public functions:

```python
def calculate_risk_score(a, b):
    ...
```

Type hints should communicate intent rather than simply satisfy a linter.

---

# 10. Avoid `Any`

Avoid unrestricted:

```python
Any
```

unless there is a justified dynamic boundary.

Prefer:

```python
TypedDict
Protocol
dataclass
Pydantic model
Union / |
```

for structured data.

If `Any` is necessary, the reason should be clear from surrounding code.

---

# 11. Optional Values

Use explicit optional typing.

Preferred:

```python
device_id: UUID | None
```

Avoid ambiguous sentinel values such as:

```python
device_id = ""
```

when the absence of a device is represented naturally by `None`.

---

# 12. Constants and Configuration

Do not hard-code environment-specific configuration.

Bad:

```python
JWT_SECRET = "my-secret"
```

Preferred:

```python
settings.jwt_secret
```

Configuration should be centralized.

Examples:

```text
database URL
JWT settings
CORS origins
upload limits
LLM provider
LLM model
```

---

# 13. Environment Variables

Environment variables should be loaded through a configuration layer.

Do not access:

```python
os.getenv(...)
```

throughout arbitrary business logic.

Prefer:

```text
configuration module
        ↓
service/application code
```

This makes configuration testable and centralized.

---

# 14. Exception Handling

Do not use broad exception handling unnecessarily.

Avoid:

```python
try:
    ...
except Exception:
    pass
```

This hides defects.

Catch the narrowest meaningful exception.

---

# 15. Exception Translation

Infrastructure exceptions should be translated at appropriate application boundaries.

For example:

```text
database exception
      ↓
repository/application layer
      ↓
domain/application exception
      ↓
API error response
```

Do not expose raw database errors to API clients.

---

# 16. Custom Exceptions

Use domain/application exceptions when they improve clarity.

Examples:

```python
TransactionNotFoundError
InvestigationNotFoundError
InvalidInvestigationStateError
DatasetImportError
RiskAnalysisError
AISummaryError
```

Exceptions should represent meaningful failure categories.

Do not create a unique exception class for every trivial condition.

---

# 17. FastAPI Router Standards

Routers should remain thin.

A router should primarily handle:

```text
request parsing
authentication/authorization dependencies
service invocation
response serialization
HTTP-specific errors
```

Avoid placing substantial business logic inside route functions.

Bad:

```python
@router.post("/investigations")
def create_investigation(...):
    # dozens of lines of business rules
```

Preferred:

```text
Router
   ↓
Service
   ↓
Repository / Domain
```

---

# 18. Service Layer

Services contain application/business orchestration.

Examples:

```text
TransactionService
DatasetImportService
RiskAnalysisService
InvestigationService
AnalyticsService
AISummaryService
```

Services should:

- coordinate domain operations
- enforce application rules
- manage transactions where appropriate
- call repositories
- return domain/application results

---

# 19. Repository Layer

Repositories handle persistence concerns.

Examples:

```text
TransactionRepository
InvestigationRepository
RiskAnalysisRepository
UserRepository
```

Repositories should not contain major business decisions.

Avoid:

```text
repository calculates fraud score
repository decides investigation priority
```

Those belong to the appropriate application/intelligence layer.

---

# 20. Domain Logic

Domain rules should live in domain-oriented components rather than being duplicated across routers.

Examples:

```text
valid investigation transitions
transaction invariants
risk-level mapping
allowed resolution states
```

A rule such as:

```text
RESOLVED investigation requires resolution
```

should exist in one authoritative place.

---

# 21. Dependency Injection

FastAPI dependency injection should be used for:

- authenticated user
- database session
- service dependencies
- authorization checks
- configuration where appropriate

Avoid global mutable service state.

---

# 22. Database Session Management

Database sessions should have clearly defined lifecycle boundaries.

A request should not accidentally reuse a session across unrelated requests.

Transactions should be explicit around multi-record operations.

---

# 23. ORM Standards

If SQLAlchemy is used:

- keep models focused on persistence
- define relationships clearly
- avoid hidden lazy-loading surprises in high-volume endpoints
- use explicit loading strategies when required
- avoid exposing ORM objects directly as API contracts

Database model naming should align with `DATABASE_DESIGN.md`.

---

# 24. Migration Standards

Database schema changes must use versioned migrations.

Never rely on manually changing production schemas.

Migration files should be:

```text
ordered
descriptive
reviewable
repeatable
```

Do not modify an already-applied migration unless the migration system explicitly supports and the environment is safely controlled.

Prefer a new migration.

---

# 25. Monetary Values

Never use floating-point types for financial amounts.

Avoid:

```python
amount: float
```

for authoritative monetary representation.

Use a decimal-safe representation.

Python:

```python
Decimal
```

Database:

```text
NUMERIC(18,2)
```

API representation should preserve precision.

---

# 26. Decimal Arithmetic

Use:

```python
Decimal
```

for financial calculations.

Avoid:

```python
0.1 + 0.2
```

style floating-point financial arithmetic.

If conversion from external numeric data is required, convert carefully and validate the source representation.

---

# 27. Currency Handling

Currency should always accompany monetary values.

Do not pass:

```text
amount = 1000
```

without knowing whether it represents:

```text
INR
USD
EUR
```

Use:

```text
amount + currency
```

as the financial value boundary.

---

# 28. Date and Time Standards

Use timezone-aware timestamps.

Preferred:

```python
datetime
```

with timezone information.

Avoid naive timestamps for transaction/business events.

The database uses:

```text
TIMESTAMPTZ
```

---

# 29. UTC Convention

Backend persistence should use UTC.

Example:

```text
2026-09-15T14:30:00Z
```

Conversion to local timezone belongs at the presentation boundary.

---

# 30. Transaction Ordering

When chronological ordering is required, use:

```text
occurred_at ASC, id ASC
```

rather than only:

```text
occurred_at ASC
```

This is necessary because multiple transactions may have identical timestamps.

### Feature Boundary Inclusion Semantics

When assembling historical feature context for a transaction `T` occurring at time `t`:
- The historical window strictly excludes the transaction being evaluated (`T` itself).
- Canonical selection predicate:
  ```sql
  WHERE occurred_at < t OR (occurred_at == t AND id < T.id)
  ```
- Any transaction occurring at `occurred_at > t` or `(occurred_at == t AND id >= T.id)` must be excluded to prevent temporal data leakage.

---

# 31. API Schema Standards

Pydantic models should define:

- request validation
- response structure
- field constraints
- serialization rules

Example:

```python
class TransactionResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    occurred_at: datetime
```

API schemas should not simply mirror every database column.

---

# 32. Pydantic Model Naming

Use clear suffixes where helpful:

```text
TransactionCreate
TransactionResponse
TransactionListResponse
InvestigationUpdate
InvestigationResponse
```

Avoid vague names such as:

```text
TransactionModel
DataObject
GenericResponse
```

---

# 33. API Validation

Validate at the API boundary:

```text
types
ranges
required fields
enum values
format
length
```

Then perform domain/business validation separately.

Example:

```text
API:
amount must be decimal and > 0

Domain:
TRANSFER requires counterparty account
```

---

# 34. Error Handling

All API errors should follow the conventions in:

```text
API_GUIDELINES.md
```

Use stable machine-readable error codes.

Do not return arbitrary error strings from individual routes.

---

# 35. Logging Standards

Use structured logging.

Logs should include useful context such as:

```text
timestamp
request_id
event
user_id where appropriate
resource_id
duration
status
```

Do not log:

```text
passwords
JWTs
API keys
database credentials
full sensitive payloads
```

---

# 36. Logging Levels

Use appropriate levels:

### DEBUG

Detailed development diagnostics.

### INFO

Normal application events.

### WARNING

Unexpected but recoverable conditions.

### ERROR

Operation failures requiring attention.

### CRITICAL

Severe system failures.

Avoid logging everything as `ERROR`.

---

# 37. Audit vs Application Logs

Do not treat application logs and audit events as the same thing.

Application logs:

```text
technical diagnostics
```

Audit events:

```text
security/workflow history
```

Important business actions should create explicit audit records.

---

# 38. Comments

Comments should explain:

```text
why
```

rather than:

```text
what
```

Bad:

```python
# Increment count
count += 1
```

Good:

```python
# Include the current transaction because the velocity window
# is defined as inclusive at the event timestamp.
count += 1
```

---

# 39. Documentation Strings

Public classes, services, and non-obvious functions should have docstrings where useful.

Docstrings should describe:

- purpose
- important inputs
- output
- important invariants
- exceptions where relevant

Avoid writing documentation that merely repeats the function name.

---

# 40. Function Size

Functions should have one clear responsibility.

If a function contains:

```text
validation
database queries
feature engineering
ML inference
audit creation
```

it is likely too large.

Extract focused components.

---

# 41. Class Size

Classes should represent a coherent responsibility.

Avoid giant service classes containing unrelated capabilities.

For example:

Bad:

```text
FinancialPlatformService
```

containing every operation.

Preferred:

```text
TransactionService
RiskAnalysisService
InvestigationService
DatasetImportService
```

---

# 42. Abstraction Rule

Do not introduce an abstraction simply because two pieces of code look similar.

Introduce abstractions when:

- a stable concept exists
- behavior is genuinely shared
- future substitution is likely
- testing benefits materially
- duplication creates maintenance risk

Avoid speculative frameworks.

---

# 43. Interfaces and Protocols

Use interfaces/Protocols when substitution is meaningful.

Good example:

```text
InvestigationSummaryProvider
```

because the LLM provider may change.

Bad example:

```text
IStringFormatter
```

when there is only one implementation and no meaningful substitution.

---

# 44. Dependency Direction

The preferred dependency direction is:

```text
API
 ↓
Application Services
 ↓
Domain / Intelligence
 ↓
Repositories
 ↓
Database
```

Infrastructure-specific details should not leak upward unnecessarily.

---

# 45. Circular Dependencies

Avoid circular module dependencies.

If:

```text
module A -> module B
module B -> module A
```

appears, reconsider ownership.

Possible solutions:

- extract shared domain concept
- invert dependency
- introduce interface
- move orchestration to service layer

---

# 46. Module Boundaries

Recommended backend modules:

```text
auth
users
accounts
transactions
merchants
devices
locations
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

Each module should have a clear responsibility.

---

# 47. Shared/Common Module

The common module should contain only genuinely shared infrastructure.

Examples:

```text
configuration
database utilities
errors
logging
security utilities
pagination
```

Do not turn `common` into a dumping ground for unrelated business logic.

---

# 48. ML Code Standards

ML code requires additional discipline.

Every feature/model component should make clear:

```text
input data
historical boundary
output features
version
assumptions
```

ML code must be deterministic where practical.

---

# 49. Feature Function Standards

Feature functions should be:

- pure where possible
- deterministic
- testable
- explicit about time windows
- explicit about historical boundaries

Example conceptual interface:

```python
def calculate_amount_zscore(
    transaction: Transaction,
    history: DataFrame,
) -> float:
    ...
```

Avoid hidden database queries inside feature functions unless the architecture explicitly requires them.

---

# 50. Temporal Leakage Prevention

ML code must never use future information.

For a transaction at time `T`:

```text
history <= T
```

is allowed.

```text
history > T
```

is forbidden.

This rule must be tested explicitly.

---

# 51. Feature Versioning

Changing feature semantics requires a new feature version.

Example:

```text
v1.0
v1.1
v2.0
```

A feature version should define:

- feature names
- transformations
- windows
- missing-value behavior
- ordering
- encoding

---

# 52. ML Model Interfaces

Models should expose a predictable interface.

Conceptually:

```python
class AnomalyModel(Protocol):
    def fit(self, features: DataFrame) -> None:
        ...

    def predict(self, features: DataFrame) -> ...:
        ...
```

The exact interface should reflect actual model needs.

Do not force every model into an unnecessarily large abstraction.

---

# 53. Model Versioning

Every persisted risk result must identify the model version that produced it.

Do not use ambiguous identifiers such as:

```text
latest
current_model
model1
```

Prefer:

```text
transaction-anomaly-1.0.0
```

or an immutable model-version identifier.

---

# 54. Risk Scoring

Risk scoring should be implemented separately from raw model inference.

Conceptual flow:

```text
features
   ↓
model
   ↓
anomaly signal
   ↓
hybrid scoring
   ↓
risk score
   ↓
risk level
```

This makes scoring logic testable independently of the model.

---

# 55. Risk Score Semantics

The code must not describe a risk score as a probability unless it is actually calibrated as one.

Use terminology such as:

```text
risk_score
anomaly_score
risk_level
```

rather than:

```text
fraud_probability
```

unless a validated probabilistic model exists.

---

# 56. Risk Factors

Risk factors should use stable machine-readable codes.

Example:

```python
AMOUNT_ANOMALY
NEW_DEVICE
NEW_LOCATION
HIGH_VELOCITY
UNUSUAL_TIME
SPENDING_SHIFT
```

Do not rely only on free-form text.

---

# 57. DataFrame Standards

Pandas DataFrames should have explicit expected columns.

Avoid code that silently operates on arbitrary columns.

Example:

```python
REQUIRED_COLUMNS = {
    "account_id",
    "amount",
    "occurred_at",
}
```

Validate before processing.

---

# 58. Pandas Mutation

Avoid accidental chained assignment.

Prefer explicit operations.

Where mutation is required, make it obvious.

This reduces silent data corruption and warning-driven bugs.

---

# 59. DataFrame Copying

When a function intends to mutate a DataFrame locally, use an explicit copy where appropriate:

```python
df = df.copy()
```

This avoids surprising callers through shared mutable state.

---

# 60. NumPy Standards

NumPy should be used where it improves numerical operations.

Do not convert everything to NumPy simply because it is an ML project.

Prefer the simplest appropriate representation.

---

# 61. Model Training Data

Training functions must clearly distinguish:

```text
features
labels
metadata
```

Ground-truth labels should never accidentally enter feature matrices.

---

# 62. Test/Train Separation

Training code must not access the final test set during:

```text
feature selection
hyperparameter tuning
threshold selection
model selection
```

This must be enforced through code structure and tests where practical.

---

# 63. Random Seeds

When randomness exists, define the seed explicitly.

Example:

```python
RANDOM_STATE = 42
```

For project-level dataset generation, the seed should be configurable.

Experiment metadata should record the seed.

---

# 64. ML Reproducibility

A model experiment should be reproducible from:

```text
dataset version
feature version
model version
configuration
seed
evaluation period
```

Do not rely on undocumented notebook state.

---

# 65. Notebook Policy

Jupyter notebooks may be used for:

- exploration
- visualization
- experiments
- model investigation

But production logic must not exist only in notebooks.

Reusable logic must be moved into tested Python modules.

---

# 66. Data Visualization Code

Exploratory charts should not be coupled to production inference.

Keep:

```text
analysis notebooks
```

separate from:

```text
application ML pipeline
```

---

# 67. AI/LLM Code Standards

LLM integration should use a provider abstraction.

Example:

```text
InvestigationSummaryProvider
```

The application should not scatter direct provider SDK calls throughout services.

---

# 68. Prompt Versioning

Prompts that materially affect AI output should have explicit versions.

Example:

```text
investigation-summary-v1
```

A change to the prompt should be traceable.

---

# 69. LLM Input Boundaries

The AI service should receive structured, controlled context.

Do not pass arbitrary application state to the model.

Use explicit DTO/context objects.

Example:

```text
InvestigationContext
    ├── transaction facts
    ├── risk factors
    ├── behavioral evidence
    └── related transactions
```

---

# 70. LLM Output Handling

LLM output must be treated as untrusted generated content.

Validate:

- expected structure
- maximum size
- required fields
- provider response status

Never execute generated text as code or SQL.

---

# 71. Frontend TypeScript Standards

Use TypeScript strictly.

Recommended configuration:

```text
strict: true
```

Avoid:

```typescript
any
```

unless there is a documented reason.

---

> [!NOTE]
> **Scope Notice: DEFERRED**
> Sections 72 through 77 define future frontend standards. Frontend implementation remains deferred until Backend + ML is complete.

# 72. React Component Standards

Components should have one clear responsibility.

Prefer:

```text
TransactionTable
RiskBadge
InvestigationPanel
EvidenceList
```

over giant components containing the entire dashboard.

---

# 73. React State Management

Use server-state tools such as TanStack Query where appropriate.

Do not duplicate server state unnecessarily in global application state.

Separate:

```text
server state
UI state
authentication state
```

---

# 74. Frontend API Layer

API calls should be centralized.

Avoid:

```typescript
fetch(...)
```

scattered across arbitrary components.

Preferred:

```text
api/
  transactions.ts
  investigations.ts
  analytics.ts
  auth.ts
```

This creates a clear frontend/backend boundary.

---

# 75. Frontend Authorization

Frontend role checks are for UX only.

Example:

```typescript
if (user.role === "ADMIN") {
    // show admin control
}
```

The backend must still enforce the permission.

---

# 76. Type-Safe API Contracts

Where practical, frontend TypeScript types should correspond to API schemas.

Avoid manually redefining the same domain concept inconsistently in multiple components.

Future OpenAPI-generated types may be considered if beneficial.

---

# 77. Testing Standards

Backend tests use:

```text
pytest
pytest-asyncio
```

where appropriate.

Tests should be:

- deterministic
- isolated
- readable
- fast where possible
- focused on behavior

---

# 78. Test Naming

Test names should describe behavior.

Preferred:

```python
def test_resolve_investigation_requires_resolution():
    ...
```

Avoid:

```python
def test_case_1():
    ...
```

---

# 79. Test Structure

Use a clear structure:

```text
Arrange
Act
Assert
```

Example:

```python
# Arrange
investigation = ...

# Act
result = service.resolve(...)

# Assert
assert result.status == RESOLVED
```

---

# 80. Unit vs Integration Tests

Unit tests should isolate a component.

Integration tests should verify interactions such as:

```text
API
 ↓
service
 ↓
repository
 ↓
database
```

Do not turn every unit test into an integration test.

---

# 81. Database Tests

Important persistence behavior should be tested against a real PostgreSQL environment where practical.

SQLite should not automatically be treated as a drop-in replacement for PostgreSQL because SQL behavior and constraints may differ.

---

# 82. ML Tests

ML tests should verify:

- feature calculations
- temporal boundaries
- leakage prevention
- deterministic behavior
- score ranges
- risk levels
- model loading
- scenario metrics

A model with high metrics but incorrect feature construction is not acceptable.

---

# 83. Security Tests

Security-sensitive behavior must have tests.

Examples:

```text
unauthenticated endpoint access
wrong role
cross-investigation access
expired JWT
invalid JWT
malformed upload
prompt injection handling
```

---

# 84. Test Data

Prefer deterministic fixtures.

Synthetic datasets should use explicit seeds.

Avoid tests depending on:

```text
current date
random values
external APIs
```

unless the dependency is intentionally being tested.

---

# 85. External Services

LLM providers and other external services should be mocked in normal unit/integration tests.

Real provider calls should be isolated to dedicated integration tests.

This prevents:

- cost
- flaky tests
- network dependency
- nondeterministic AI output

---

# 86. Git Commit Standards

Commits should be:

- focused
- descriptive
- logically grouped

Recommended format:

```text
feat: add transaction risk analysis
fix: prevent future data leakage in velocity features
test: add investigation state transition tests
docs: update ML design
refactor: extract risk scoring service
```

Avoid vague commits:

```text
changes
updates
stuff
final
```

---

# 87. Pull Request Standards

A pull request should explain:

1. What changed?
2. Why was it changed?
3. What was tested?
4. Are there migration changes?
5. Are there security implications?
6. Are there ML/data implications?

Large unrelated changes should be separated.

---

# 88. Code Review Checklist

Reviewers should consider:

### Correctness

```text
Does the implementation satisfy the requirement?
```

### Security

```text
Can unauthorized users access this?
```

### Data Integrity

```text
Can financial facts become inconsistent?
```

### Temporal Correctness

```text
Does ML code accidentally use future information?
```

### Maintainability

```text
Is responsibility clearly separated?
```

### Testing

```text
Is important behavior covered?
```

---

# 89. Database Query Standards

Queries should:

- use parameterization
- select only needed columns where practical
- use indexes appropriately
- avoid N+1 patterns
- avoid unbounded result sets

Do not add indexes automatically for every filter.

Index based on actual access patterns.

---

# 90. API Performance Standards

Endpoints should avoid:

```text
unbounded database reads
repeated database queries
unnecessary serialization
expensive calculations on every request
```

Expensive analytics should be measured before optimization.

---

# 91. Caching

Caching is not the default.

Introduce caching only when:

```text
measured bottleneck exists
data is safe to cache
invalidation semantics are clear
```

Never cache mutable investigation state without a clear consistency strategy.

---

# 92. Background Jobs

Background processing should be introduced only where synchronous processing becomes problematic.

Potential candidates:

```text
large dataset import
batch ML analysis
AI summary generation
```

Do not introduce Celery/Redis merely because they are common technologies.

---

# 93. Error Recovery

Operations should fail predictably.

For example:

```text
AI provider failure
    ↓
investigation remains available
    ↓
AI summary marked FAILED
```

Do not roll back authoritative transaction data because an optional AI operation failed.

---

# 94. Transaction Management

Use explicit database transactions around operations requiring atomicity.

Examples:

```text
investigation creation
investigation resolution + audit event
risk analysis + risk factors
dataset import metadata updates
```

---

# 95. Idempotency

Operations that may be retried should define idempotency behavior.

Examples:

```text
dataset import
risk analysis
AI summary generation
```

Do not blindly repeat side effects on retries.

---

# 96. Immutability

Treat these as append-oriented:

```text
transactions
risk analyses
risk factors
audit events
evidence snapshots
```

Avoid in-place mutation when historical correctness matters.

---

# 97. Domain Constants

Domain-controlled values should not be scattered as strings.

Bad:

```python
if status == "RESOLVED":
```

in dozens of files.

Prefer centralized enums/constants where appropriate:

```python
InvestigationStatus.RESOLVED
```

The exact representation must remain compatible with the database/API contracts.

---

# 98. Avoid Magic Numbers

Bad:

```python
if score >= 75:
```

Preferred:

```python
CRITICAL_RISK_THRESHOLD = 75
```

Configuration-driven thresholds should be externalized when they are operational settings.

---

# 99. Avoid Magic Strings

Bad:

```python
if transaction_type == "TRANSFER":
```

repeated throughout the application.

Prefer a shared domain representation where practical.

---

# 100. Data Validation Before Intelligence

The order should be:

```text
input validation
      ↓
data normalization
      ↓
data quality checks
      ↓
feature generation
      ↓
ML
```

Do not run ML over obviously invalid financial records.

---

# 101. Data Quality Standards

Imported datasets should be checked for:

```text
duplicate identifiers
missing required fields
invalid amounts
invalid timestamps
invalid account references
invalid categorical values
```

Validation failures should be recorded through the ingestion workflow.

---

# 102. No Silent Data Loss

The ingestion layer must not silently discard invalid records.

If a row is rejected:

```text
record rejection reason
```

and expose aggregate import statistics.

Example:

```text
total_rows = 250000
valid_rows = 249700
invalid_rows = 300
```

---

# 103. Reproducibility Standards

Dataset generation, ML training, and evaluation should be reproducible.

Record:

```text
seed
dataset version
feature version
model version
configuration
```

---

# 104. Dependency Pinning

Production dependencies should be version-pinned or constrained through a reproducible lockfile.

Security updates should be reviewed deliberately rather than allowing uncontrolled dependency drift.

---

# 105. Static Analysis

The project should use automated quality checks where practical.

Potential tools:

```text
Ruff
MyPy
Black
Pytest
```

The exact toolchain can be finalized during implementation.

---

# 106. Linting

Linting should run locally and in CI.

Lint rules should prioritize:

- correctness
- unused imports
- unreachable code
- unsafe patterns
- style consistency

Avoid enabling hundreds of rules without understanding their impact.

---

# 107. Type Checking

Static type checking should cover core application code.

Potential tool:

```text
mypy
```

or an equivalent Python type checker.

ML exploratory notebooks may have looser requirements, but reusable production ML modules should remain typed.

---

# 108. Formatting and Linting in CI

CI should verify:

```text
formatting
linting
type checks where configured
tests
```

A branch should not be considered ready if basic automated quality checks fail.

---

# 109. CI Pipeline

Recommended baseline:

```text
checkout
   ↓
install dependencies
   ↓
format check
   ↓
lint
   ↓
type check
   ↓
unit tests
   ↓
integration tests
   ↓
build
```

Security scanning can be added as the project matures.

---

# 110. Documentation Standards

Code changes that alter architecture or behavior should update the relevant documentation.

Examples:

```text
database change
    -> DATABASE_DESIGN.md

API change
    -> API_GUIDELINES.md

security change
    -> SECURITY.md

ML feature change
    -> ML_DESIGN.md

architectural decision
    -> DECISIONS.md
```

---

# 111. Architecture Decision Recording

Significant decisions should not remain buried in chat or commit messages.

Record them in:

```text
DECISIONS.md
```

Examples:

```text
Why PostgreSQL?
Why Isolation Forest?
Why modular monolith?
Why JWT?
Why feature store deferred?
```

---

# 112. Project Log

Implementation milestones and notable changes should be recorded in:

```text
PROJECT_LOG.md
```

The project log should capture:

- milestone
- date
- implementation summary
- tests
- decisions
- issues
- next step

---

# 113. Frontend Design Standards

Frontend implementation should follow the later frontend-specific documentation.

At minimum:

- consistent component structure
- type-safe API access
- accessible UI
- server-authoritative data
- reusable design primitives
- predictable state management

The detailed frontend standards will be finalized during the frontend phase.

---

# 114. Code Organization Example

Recommended backend structure:

```text
app/
├── main.py
├── config/
├── common/
├── auth/
├── users/
├── accounts/
├── transactions/
├── merchants/
├── devices/
├── locations/
├── ingestion/
├── analytics/
├── intelligence/
│   ├── features/
│   ├── models/
│   ├── scoring/
│   └── evaluation/
├── investigations/
├── evidence/
└── ai/
```

The exact layout may evolve as implementation progresses.

---

# 115. Anti-Patterns

Avoid:

- giant route handlers
- giant service classes
- global mutable state
- database queries inside frontend components
- business logic inside repositories
- business logic inside routers
- raw SQL string concatenation
- floating-point money
- untyped `Any` everywhere
- swallowing exceptions
- magic numbers
- magic strings
- hidden model behavior
- notebook-only production logic
- unnecessary microservices
- premature infrastructure
- copying entire datasets repeatedly in memory
- silently dropping invalid records

---

# 116. Coding Standards Acceptance Criteria

The coding standards are considered adopted when:

- [ ] Python formatting is standardized.
- [ ] Linting is configured.
- [ ] Type checking expectations are defined.
- [ ] Naming conventions are consistent.
- [ ] Type hints are used for important code.
- [ ] FastAPI routers remain thin.
- [ ] Business logic is placed in services/domain components.
- [ ] Repositories focus on persistence.
- [ ] Monetary values use Decimal-safe handling.
- [ ] Timestamps are timezone-aware.
- [ ] ML code protects against temporal leakage.
- [ ] Feature versions are tracked.
- [ ] Model versions are tracked.
- [ ] LLM calls use a provider abstraction.
- [ ] Secrets are externalized.
- [ ] Security-sensitive behavior is tested.
- [ ] Database migrations are versioned.
- [ ] CI runs quality checks.
- [ ] Important architectural decisions are documented.
- [ ] Invalid imported data is never silently discarded.

---

# 117. Open Coding Decisions

The following can be finalized during implementation:

1. Exact Ruff configuration.
2. Exact MyPy strictness level.
3. Black vs Ruff formatter configuration.
4. Pre-commit hooks.
5. CI provider and workflow structure.
6. Exact SQLAlchemy conventions.
7. Repository interface conventions.
8. Exact frontend linting/tooling.
9. API type-generation strategy.
10. Test fixture architecture.
11. Coverage thresholds.

Final decisions should be recorded in `DECISIONS.md`.

---

# 118. Relationship to Other Documents

| Document | Relationship |
|---|---|
| `PRD.md` | Defines product behavior implemented by the codebase |
| `TRD.md` | Defines technical stack and constraints |
| `ARCHITECTURE.md` | Defines module and dependency boundaries |
| `DATABASE_DESIGN.md` | Defines persistence model |
| `ML_DESIGN.md` | Defines intelligence implementation principles |
| `API_GUIDELINES.md` | Defines API implementation contracts |
| `SECURITY.md` | Defines secure coding requirements |
| `TESTING_STRATEGY.md` | Defines testing practices |
| `PROJECT_ROADMAP.md` | Defines implementation sequencing |
| `DECISIONS.md` | Records final technical decisions |
| `PROJECT_LOG.md` | Records implementation history |

---

# 119. Final Coding Principle

FinSignal should be built so that another developer can read a module and quickly answer:

```text
What does this do?
Why does it exist?
What data does it operate on?
What rules does it enforce?
How is it tested?
What depends on it?
```

The final principle is:

> **Write code that is explicit about financial rules, strict about data integrity, deterministic where intelligence is involved, secure at every boundary, and simple enough to change when evidence demands it.**
