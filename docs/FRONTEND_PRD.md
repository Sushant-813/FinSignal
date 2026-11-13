# FinSignal --- Frontend Product Requirements Document

**Document:** `FRONTEND_PRD.md`\
**Product:** FinSignal --- Financial Transaction Intelligence &
Investigation Platform\
**Status:** Draft for review\
**Version:** 1.0\
**Scope:** Frontend product requirements for the existing Backend + ML
v1.0.0 platform

------------------------------------------------------------------------

## 1. Purpose

This document defines the product requirements for the FinSignal web
frontend. It translates the existing product capabilities and backend
API contracts into user-facing workflows, screens, functional
requirements, and acceptance criteria.

The frontend is an operational interface for analysts, investigators,
and administrators. It is not a second implementation of the financial
intelligence platform. The backend remains authoritative for transaction
facts, monetary values, analytics, behavioral features, risk analysis,
evidence, investigation state, authorization, and audit records.

This document describes the intended frontend experience. It does not
claim that every screen already has a complete backend endpoint.
Endpoint readiness and unresolved contract gaps are called out
explicitly.

## 2. Product Context

FinSignal helps authorized users move from imported transaction data to
explainable risk context and human-led investigation.

The core product workflow is:

1.  Authenticate.
2.  Import a transaction dataset (authorized roles only).
3.  Review import status and data-quality results.
4.  Explore transactions and financial analytics.
5.  Inspect persisted risk results or request an authorized risk
    analysis.
6.  Create an investigation manually for suspicious activity.
7.  Review the investigation workspace, primary transaction, risk
    factors, and evidence.
8.  Link eligible related transactions and attach permitted evidence.
9.  Generate or inspect an evidence-grounded AI investigation summary
    where authorized.
10. Record a human investigation resolution.

Automatic risk-triggered investigation creation, real-time alerting,
autonomous fraud decisions, and recursive graph exploration are not part
of this frontend MVP.

## 3. Product Goals

The frontend shall:

-   Make the backend's existing financial and investigative capabilities
    understandable and usable.
-   Help users identify unusual activity without presenting anomaly or
    risk as proof of fraud.
-   Make the evidence and reasoning behind risk assessments inspectable.
-   Support the manual-first investigation lifecycle and its role
    restrictions.
-   Present financial and analytical data accurately, with clear
    currency, time, namespace, and status context.
-   Make the distinction between observed facts, derived signals, AI
    interpretations, and human decisions explicit.
-   Provide a consistent, accessible desktop-first interface that
    remains usable on smaller screens.
-   Avoid duplicating backend business logic or creating a frontend-only
    source of truth.

## 4. Non-Goals

The frontend MVP will not:

-   Make final fraud or legitimacy decisions automatically.
-   Automatically create investigations when a risk threshold is
    crossed.
-   Provide real-time transaction streaming, push alerts, or live
    monitoring.
-   Implement multi-hop or recursive transaction graph traversal.
-   Provide a mobile-native application.
-   Calculate risk scores, balances, financial aggregates, or behavioral
    features independently.
-   Edit or delete evidence after it has been attached.
-   Reopen or mutate resolved investigations.
-   Provide a generic conversational chatbot. The AI feature is a
    structured investigation briefing.
-   Implement external banking integrations, regulatory workflows, or
    multi-tenant SaaS administration unless separately approved.
-   Expose database tables or internal ML implementation details
    directly to the browser.

## 5. Users and Roles

The frontend supports the three backend roles (enforced authoritatively by backend authentication and the database `chk_users_role` constraint):

-   **ADMIN** --- platform administration and broad operational
    authority.
-   **ANALYST** --- transaction and analytics review, dataset import,
    investigation creation, and read-oriented investigation/AI-summary
    access.
-   **INVESTIGATOR** --- investigation ownership, evidence work, and
    human resolution within backend authorization rules.

No other roles (including hypothetical external roles such as `AUDITOR`) exist in the backend system; any unknown or missing role fails closed with zero workspace access.

The backend is the authorization authority. Hiding a button or route in
the frontend is not a security control. The frontend must handle `401`,
`403`, and object-level authorization failures even when the UI has
already hidden the corresponding action.

### 5.1 Role capability summary

  ------------------------------------------------------------------------
  Capability                   ADMIN            ANALYST       INVESTIGATOR
  --------------- ------------------ ------------------ ------------------
  Sign in and                    Yes                Yes                Yes
  view                                                  
  current-user                                          
  context                                               

  View                           Yes                Yes                Yes
  transactions                                          

  View analytics                 Yes                Yes                Yes

  View persisted                 Yes                Yes                Yes
  transaction                                           
  risk                                                  

  Request risk                   Yes                Yes                Yes
  analysis using                                        
  an Active model                                       

  Request risk                   Yes                 No                 No
  analysis using                                        
  a Validated                                           
  model                                                 

  Import datasets                Yes                Yes                 No

  View shared                    Yes                Yes                Yes
  investigation                                         
  queue and                                             
  workspace                                             

  Create an                      Yes                Yes                Yes
  investigation                                         

  Change                 Yes, global   No, according to         Restricted
  assignment /             authority  implemented PATCH    self-assignment
  investigation                                contract and permitted case
  status                                                           changes

  Link related                   Yes                 No Assigned case only
  transactions                                          

  Attach evidence                Yes                 No Assigned case only

  View AI summary                Yes     Yes, read-only Assigned case only
  and history                                           

  Generate AI                    Yes                 No Assigned case only
  summary                                               

  Resolve an                     Yes                 No Assigned case only
  investigation                                         

  Manage users              Intended                 No                 No
                          admin-only                    
                         capability;                    
                        frontend/API                    
                    contract must be                    
                           confirmed                    
  ------------------------------------------------------------------------

**Authorization source of truth:** the implemented endpoint-level rules
in `API_GUIDELINES.md` and `SECURITY.md` take precedence over this
summary. In particular, investigator assignment and AI-summary access
are object-scoped, not merely role-scoped.

### 5.2 Role-aware interface behavior

-   Navigation and actions should reflect the current user's role and,
    where applicable, case assignment.
-   Read-only users should still be able to inspect information they are
    authorized to view.
-   A disabled action should explain the restriction when doing so is
    useful and does not disclose sensitive information.
-   The frontend must not infer that a user can act on a case solely
    because their role is `INVESTIGATOR`; the case may be unassigned or
    assigned to another investigator.
-   The frontend must not assume the analyst can update an investigation
    merely because the analyst can create and view one.
-   The API response and server authorization result always win over
    cached or locally inferred permissions.

## 6. Primary User Workflows

### 6.1 Authentication

1.  User opens the application.
2.  Unauthenticated user is directed to the sign-in screen.
3.  User submits credentials.
4.  Frontend sends credentials to the backend authentication endpoint.
5.  On success, frontend establishes the approved client session and
    loads the current-user profile.
6.  User is routed to the default authorized landing page.
7.  On invalid/expired credentials, the user receives a clear error and
    can retry.
8.  On logout, the frontend clears its local authenticated state and
    returns to sign-in.

The exact token storage/session design is a security decision and must
be finalized in `FRONTEND_SECURITY.md` before implementation. The
frontend must not assume that `localStorage` is approved.

### 6.2 Dataset import

1.  An Admin or Analyst opens Dataset Management.
2.  User selects a CSV file and supplies or confirms the source
    namespace and source type where the API requires them.
3.  Frontend performs basic client-side checks for usability, without
    replacing backend validation.
4.  Frontend submits the multipart upload.
5.  Frontend displays the returned import status, row counts,
    timestamps, and duplicate-import outcome.
6.  If the API reports an import already in progress, duplicate
    completion, validation failure, or size/format error, the UI
    presents the backend result clearly.
7.  User can inspect import details and validation errors if the
    corresponding detail endpoint provides them.

The documented upload contract accepts CSV up to 50 MB and supports
UTF-8 / UTF-8 BOM. The backend remains responsible for authoritative
validation, parsing, deduplication, and persistence.

### 6.3 Transaction exploration

1.  User opens Transactions.
2.  User browses a paginated transaction list.
3.  User applies supported filters such as account, merchant, device,
    location, transaction type, direction, category, risk level, time
    range, and amount range.
4.  User opens a transaction detail view.
5.  User inspects transaction facts and available
    account/merchant/device context.
6.  User inspects an existing risk assessment, if present.
7.  If authorized and supported by the selected model lifecycle, user
    requests an on-demand risk analysis.
8.  User may create an investigation manually if the activity warrants
    review.

The UI must distinguish "no risk analysis exists" from "low risk." A
missing assessment is not a zero score.

### 6.4 Analytics exploration

1.  User opens Dashboard or Analytics.
2.  Frontend requests backend-computed overview metrics and supported
    trend/category/merchant/account analytics.
3.  User selects supported filters such as namespace, currency, date
    range, and reporting timezone.
4.  Frontend updates the relevant views from API responses.
5.  User drills into accounts, merchants, or transactions only where a
    corresponding detail endpoint exists.

Analytics are descriptive and deterministic. The frontend must not
derive replacement totals from the currently visible page of
transactions.

### 6.5 Investigation triage and creation

1.  User opens the shared investigation queue.
2.  User filters by status, priority, assignee, or unassigned state.
3.  User opens a transaction and chooses to create an investigation, or
    creates one from the investigation workflow using a primary
    transaction ID.
4.  User selects triage priority (defaults to `MEDIUM`). Note: the authoritative backend `InvestigationCreateRequest` schema accepts only `transaction_id` and `priority`; initial creation notes are forbidden (`extra="forbid"`).
5.  Backend creates an `OPEN`, unassigned investigation and binds
    exactly one `PRIMARY` transaction.
6.  Frontend displays the newly created workspace and its current state.

The frontend must not imply that a risk threshold automatically created
a case. Investigation creation is manual-first.

### 6.6 Investigation workspace

The workspace should help an authorized user understand the case without
conflating evidence and interpretation.

The workspace includes, when returned by the API:

-   Investigation status, priority, assignment, creation/update
    timestamps, and resolution state.
-   Primary transaction facts.
-   Latest persisted risk analysis and risk factors.
-   Associated transactions, clearly distinguishing `PRIMARY` from
    `RELATED`.
-   Evidence list with type, source, title, description, payload
    details, and creation time.
-   AI summary status and structured output, if available and
    authorized.
-   Permitted actions based on role, assignment, and lifecycle state.

Related-transaction discovery is limited to the backend's direct 1-hop
shared-party rule and same-source-namespace constraint. The frontend
must not implement its own graph expansion.

### 6.7 Assignment and case progression

1.  An Investigator may self-assign an unassigned case.
2.  An Investigator may self-unassign a case assigned to themselves,
    subject to backend rules.
3.  An Admin may assign or reassign cases according to the backend
    contract.
4.  An authorized user transitions a case from `OPEN` to `UNDER_REVIEW`.
5.  The frontend refreshes the authoritative workspace after a mutation.
6.  Concurrent assignment conflicts and invalid transitions are
    presented as actionable errors.

The supported lifecycle is `OPEN` → `UNDER_REVIEW` → `RESOLVED`.
Resolved investigations are terminal and immutable.

### 6.8 Evidence management

1.  An authorized Admin or assigned Investigator opens the evidence
    section.
2.  User selects a supported evidence type/source and supplies the
    required metadata or note.
3.  Frontend submits the evidence attachment request.
4.  Backend validates source existence, scope, type compatibility,
    payload size, and investigation mutability.
5.  Frontend displays the created evidence item in the append-only
    timeline/list.
6.  Existing evidence is read-only; no edit or delete controls are
    shown.

The frontend must communicate that an evidence item is a persisted
snapshot, not a live editable reference.

### 6.9 AI investigation summary

1.  An authorized Admin or assigned Investigator requests summary
    generation.
2.  Frontend displays the backend-returned generation status and handles
    pending, completed, stale, or failed states as represented by the
    API.
3.  On completion, the UI renders the structured sections:
    -   Executive summary
    -   Observed facts
    -   Derived signals
    -   Potential interpretations
    -   Uncertainties and limitations
4.  Evidence references are displayed so the investigator can inspect
    their supporting records where the API provides those IDs.
5.  Analysts may view summaries and history where authorized, but cannot
    generate them.
6.  The UI clearly labels the output as AI-generated and advisory.

The AI output must never be presented as a fraud verdict or as a
replacement for the human resolution workflow.

### 6.10 Human resolution

1.  An Admin or the assigned Investigator reviews the investigation.
2.  User selects one supported outcome: `LEGITIMATE`, `SUSPICIOUS`,
    `CONFIRMED_FRAUD`, or `INCONCLUSIVE`.
3.  User supplies mandatory non-empty resolution notes.
4.  Frontend requests explicit resolution through the dedicated resolve
    endpoint.
5.  On success, the case is displayed as `RESOLVED` and all mutation
    controls are removed.
6.  If the request fails because the case changed concurrently or is no
    longer resolvable, the frontend reloads authoritative state and
    explains the conflict.

The resolution is a human decision recorded by the backend. AI output
and risk level must not preselect or silently determine the resolution.

## 7. Information Architecture and Screen Inventory

The following is the proposed MVP screen inventory. A screen is included
only where the current product/API surface supports a meaningful user
task; items marked **contract-dependent** require backend contract
confirmation before implementation.

  ---------------------------------------------------------------------------------------
  Screen / area     Primary purpose     Main user actions         Backend dependency
  ----------------- ------------------- ------------------------- -----------------------
  Sign In           Authenticate users  Submit credentials        Auth login,
                                                                  current-user

  Application Shell Global navigation   Navigate, logout          Current-user context
                    and identity                                  

  Dashboard         Operational and     Change supported          Analytics overview and
                    financial overview  reporting filters,        supported aggregates
                                        navigate to detail areas  

  Transactions      Search and inspect  Filter, sort/page, open   Transaction list/detail
                    transactions        detail                    

  Transaction       Inspect a           View facts/risk; request  Transaction detail,
  Detail            transaction and its analysis if authorized;   risk read/analyze,
                    intelligence        create case               investigation create

  Analytics         Explore trends and  Select                    Overview, trends,
                    distributions       time/currency/namespace   categories, merchants
                                        filters                   

  Accounts          Browse account      Filter and open account   Account list; detail
                    activity                                      contract confirmation

  Account Detail    Understand account  Inspect supported         Account detail/behavior
                    activity and        activity/behavior views   endpoints ---
                    behavior                                      contract-dependent

  Dataset           Import and inspect  Upload CSV, review import Dataset import/detail
  Management        datasets            outcome and errors        endpoints

  Investigation     Triage open and     Filter, paginate, open,   Investigation
  Queue             active cases        create                    list/create

  Investigation     Review and manage a Assign, progress, link    Investigation workspace
  Workspace         case                related transactions,     and mutation endpoints
                                        attach evidence, resolve  

  AI Summary Panel  Review              Generate, refresh, view   AI summary endpoints
                    evidence-grounded   latest/history            
                    briefing                                      

  User Management   Administer users    Manage users              **Contract-dependent;
                                                                  do not build until API
                                                                  contract is confirmed**

  Audit History     Inspect audit       Filter and view events    **Contract-dependent;
                    records                                       do not build until API
                                                                  contract is confirmed**
  ---------------------------------------------------------------------------------------

### 7.1 Navigation groups

Proposed navigation:

-   Overview
    -   Dashboard
-   Data
    -   Transactions
    -   Accounts
    -   Dataset Management (Admin, Analyst)
-   Intelligence
    -   Analytics
    -   Risk Monitoring (may initially be a filtered transaction view,
        not a separate backend resource)
-   Investigations
    -   Investigation Queue
-   Administration
    -   User Management (only after API support is confirmed)
    -   Audit History (only after API support is confirmed)

Do not create a separate Risk Monitoring module if it merely duplicates
Transactions with a risk filter and no distinct workflow. The final
navigation should be validated against usability and actual API
capabilities.

## 8. Functional Requirements

Priority definitions:

-   **P0 --- MVP critical:** required for the core end-to-end workflow.
-   **P1 --- Important:** useful for a complete operational experience,
    but may follow the first usable slice.
-   **P2 --- Deferred / contract-dependent:** do not block core MVP
    until explicitly approved.

  ------------------------------------------------------------------------
  ID                      Priority                Requirement
  ----------------------- ----------------------- ------------------------
  FPR-001                 P0                      The application shall
                                                  authenticate users
                                                  through the backend and
                                                  load the authenticated
                                                  user's role/context.

  FPR-002                 P0                      The application shall
                                                  protect authenticated
                                                  routes and handle
                                                  expired/invalid
                                                  sessions.

  FPR-003                 P0                      The application shall
                                                  present navigation and
                                                  actions according to the
                                                  user's role and
                                                  applicable case
                                                  assignment.

  FPR-004                 P0                      The application shall
                                                  display paginated
                                                  transactions and expose
                                                  supported backend
                                                  filters.

  FPR-005                 P0                      The application shall
                                                  display transaction
                                                  details without
                                                  inventing missing values
                                                  or substituting defaults
                                                  for absent data.

  FPR-006                 P0                      The application shall
                                                  display backend-computed
                                                  analytics and preserve
                                                  the selected namespace,
                                                  currency, and
                                                  time-window context.

  FPR-007                 P0                      Authorized Admins and
                                                  Analysts shall be able
                                                  to upload supported CSV
                                                  datasets and inspect the
                                                  returned import outcome.

  FPR-008                 P0                      The application shall
                                                  display import status,
                                                  row counts, duplicate
                                                  outcome, and backend
                                                  validation/error
                                                  information when
                                                  available.

  FPR-009                 P0                      The application shall
                                                  display persisted
                                                  transaction risk
                                                  assessments and
                                                  distinguish missing
                                                  assessments from
                                                  low-risk assessments.

  FPR-010                 P0                      The application shall
                                                  expose on-demand risk
                                                  analysis only when the
                                                  backend permits the
                                                  user's role and selected
                                                  model lifecycle.

  FPR-011                 P0                      The application shall
                                                  support manual
                                                  investigation creation
                                                  linked to a primary
                                                  transaction.

  FPR-012                 P0                      The application shall
                                                  provide a filterable,
                                                  paginated shared
                                                  investigation queue.

  FPR-013                 P0                      The application shall
                                                  display the
                                                  investigation workspace,
                                                  including primary
                                                  transaction context,
                                                  risk information,
                                                  associated transactions,
                                                  and evidence returned by
                                                  the API.

  FPR-014                 P0                      The application shall
                                                  enforce role- and
                                                  assignment-aware
                                                  presentation of
                                                  investigation actions
                                                  while relying on backend
                                                  authorization.

  FPR-015                 P0                      Authorized users shall
                                                  be able to perform
                                                  permitted assignment and
                                                  lifecycle transitions
                                                  and receive clear
                                                  conflict feedback.

  FPR-016                 P0                      Authorized users shall
                                                  be able to link eligible
                                                  1-hop related
                                                  transactions.

  FPR-017                 P0                      Authorized users shall
                                                  be able to attach
                                                  supported append-only
                                                  evidence.

  FPR-018                 P0                      The application shall
                                                  render existing evidence
                                                  as immutable records and
                                                  provide no edit/delete
                                                  affordance.

  FPR-019                 P0                      Authorized users shall
                                                  be able to generate or
                                                  view AI investigation
                                                  summaries according to
                                                  endpoint-level
                                                  permissions.

  FPR-020                 P0                      AI summaries shall be
                                                  displayed in separate
                                                  structured sections and
                                                  labeled
                                                  advisory/AI-generated.

  FPR-021                 P0                      Authorized users shall
                                                  be able to resolve an
                                                  investigation using an
                                                  allowed outcome and
                                                  mandatory notes.

  FPR-022                 P0                      Resolved investigations
                                                  shall be presented as
                                                  read-only and terminal.

  FPR-023                 P0                      The application shall
                                                  display loading, empty,
                                                  partial, validation,
                                                  authorization, conflict,
                                                  and server-error states.

  FPR-024                 P0                      The application shall
                                                  preserve financial value
                                                  precision and display
                                                  currency explicitly.

  FPR-025                 P0                      The application shall
                                                  not calculate
                                                  authoritative balances,
                                                  risk scores, financial
                                                  aggregates, or
                                                  behavioral features in
                                                  the browser.

  FPR-026                 P1                      The application shall
                                                  support account and
                                                  merchant drill-down
                                                  where stable detail
                                                  contracts are available.

  FPR-027                 P1                      The application shall
                                                  provide useful
                                                  request/error context,
                                                  including request IDs
                                                  where returned by the
                                                  API.

  FPR-028                 P1                      The application shall
                                                  support responsive
                                                  layouts for tablet and
                                                  mobile-sized viewports
                                                  without hiding critical
                                                  case status or financial
                                                  context.

  FPR-029                 P2                      The application may
                                                  provide user management
                                                  after the
                                                  user-administration API
                                                  and exact permissions
                                                  are documented.

  FPR-030                 P2                      The application may
                                                  provide audit-history
                                                  browsing after the audit
                                                  read API and
                                                  filtering/pagination
                                                  contract are documented.
  ------------------------------------------------------------------------

## 9. Data Presentation Requirements

### 9.1 Financial values

-   Preserve backend monetary values and their precision. Do not parse a
    decimal string into a JavaScript floating-point number for
    arithmetic.
-   Display the currency code alongside monetary values, especially
    where multiple currencies or namespaces may appear.
-   Do not aggregate values across currencies unless the backend
    explicitly returns a normalized aggregate with its currency
    semantics.
-   Do not display a missing amount as `0.00`.
-   Use consistent formatting for negative values, decimal places, and
    large numbers.

### 9.2 Risk and anomaly semantics

-   Display the exact backend risk level and score with clear labels.
-   Risk is an indicator for prioritization, not a fraud verdict.
-   Do not equate `HIGH` risk with `CONFIRMED_FRAUD`.
-   Do not equate low risk or absence of a risk result with legitimate
    activity.
-   Show risk factors and their descriptions when provided.
-   Identify stale, unavailable, or missing risk data distinctly where
    the API exposes those states.

### 9.3 Time and ordering

-   Display timestamps with an unambiguous date/time and an understood
    timezone.
-   Preserve the backend's event/creation timestamps; do not fabricate
    local timestamps.
-   If the user changes display timezone, make the selected timezone
    visible.
-   Preserve backend ordering and pagination semantics. Do not reorder
    evidence or investigation history in ways that obscure the server's
    deterministic order.

### 9.4 Facts, signals, interpretations, and decisions

The UI must visually distinguish:

1.  **Observed facts** --- records and values directly represented by
    source data/evidence.
2.  **Derived signals** --- backend-calculated analytics, rules, model
    scores, and risk factors.
3.  **Potential interpretations** --- hypotheses supplied by the AI
    assistant.
4.  **Human decisions** --- investigation status, resolution, and
    investigator notes.

No visual treatment should make an AI interpretation appear equivalent
to a verified fact or human decision.

## 10. Interaction and State Requirements

Every data-driven screen must define:

-   Initial loading state.
-   Refreshing or background-fetch state where relevant.
-   Empty state that explains whether no records match the current
    filters or no records exist.
-   Validation state for invalid user input.
-   `401` handling for missing/expired authentication.
-   `403` handling for role or object-level authorization denial.
-   `404` handling for missing resources.
-   `409` handling for concurrent changes, duplicate operations, or
    immutable resources.
-   `413` handling for oversized uploads.
-   `422` handling for validation failures.
-   `5xx` and network failure states.
-   Partial-data state when one panel succeeds and another fails,
    without implying that the failed panel contains no data.

Mutations must provide clear pending and success/failure feedback. After
a successful mutation, the frontend should refresh or update from the
authoritative API response rather than relying on optimistic assumptions
for sensitive lifecycle changes.

## 11. Accessibility and Responsive Requirements

-   Target WCAG 2.2 AA for core workflows.
-   All controls must be keyboard accessible with visible focus.
-   Form fields must have programmatic labels and useful validation
    messages.
-   Status and risk must not be communicated by color alone.
-   Tables must have accessible headers and usable keyboard interaction.
-   Charts must have text alternatives or an equivalent data view.
-   Dialogs must manage focus correctly and support Escape where
    appropriate.
-   Layouts should be desktop-first because the product is an
    investigation workspace, while remaining usable on tablet and
    mobile.
-   On narrow screens, dense tables may use a deliberate alternate
    layout or horizontal scrolling; critical identifiers, status, and
    actions must remain discoverable.

Detailed visual rules are defined in `FRONTEND_DESIGN.md`.

## 12. Security and Privacy Requirements

-   The browser must communicate with the backend over HTTPS outside
    local development.
-   Authentication/session handling must follow the approved
    `FRONTEND_SECURITY.md` decision; do not select token storage by
    convenience.
-   Never embed API secrets, LLM keys, database credentials, or
    privileged configuration in frontend bundles.
-   Never rely on client-side route guards or hidden buttons as
    authorization.
-   Do not log access tokens, passwords, full sensitive evidence
    payloads, or unnecessary personal/financial data.
-   Avoid exposing sensitive data in URLs, browser storage, analytics
    events, or error messages.
-   Upload UI must enforce a usability limit consistent with the API,
    while the backend remains authoritative.
-   Render user-supplied notes and evidence text safely; do not inject
    untrusted HTML.
-   The frontend must not permit editing or deletion of immutable
    evidence or resolved investigations.

## 13. Non-Functional Requirements

  -----------------------------------------------------------------------
  ID                      Requirement             Target / expectation
  ----------------------- ----------------------- -----------------------
  FNFR-001                Usability               Core workflows should
                                                  be understandable
                                                  without requiring users
                                                  to know backend
                                                  internals.

  FNFR-002                Correctness             All authoritative
                                                  financial and
                                                  intelligence values
                                                  come from backend
                                                  responses.

  FNFR-003                Security                All protected API calls
                                                  use the approved
                                                  authentication
                                                  mechanism; server
                                                  authorization remains
                                                  authoritative.

  FNFR-004                Accessibility           WCAG 2.2 AA target for
                                                  core workflows.

  FNFR-005                Responsiveness          Desktop-first, usable
                                                  on tablet and mobile
                                                  viewports.

  FNFR-006                Reliability             Network, API, and
                                                  partial failures must
                                                  be represented
                                                  accurately and
                                                  recoverably.

  FNFR-007                Performance             Paginated and filtered
                                                  server queries should
                                                  be used instead of
                                                  loading unbounded
                                                  datasets.

  FNFR-008                Maintainability         UI features should map
                                                  to product domains and
                                                  consume a centralized
                                                  API client/contract
                                                  layer.

  FNFR-009                Traceability            Important user actions
                                                  should be reflected by
                                                  backend audit events
                                                  where the backend
                                                  records them.

  FNFR-010                Consistency             Shared interaction,
                                                  status, table, form,
                                                  and error patterns
                                                  should be used across
                                                  screens.
  -----------------------------------------------------------------------

Specific numerical performance budgets should be set in
`FRONTEND_TRD.md` and validated against the deployment environment
rather than invented here.

## 14. MVP Release Scope

### 14.1 Required for first usable frontend release

-   Authentication and current-user context.
-   Application shell and role-aware navigation.
-   Dashboard / analytics overview using implemented analytics
    endpoints.
-   Transaction list, filters, and transaction detail.
-   Risk result viewing and authorized on-demand analysis.
-   Dataset CSV import and import-result presentation.
-   Investigation queue and manual case creation.
-   Investigation workspace with assignment/status actions.
-   Related transaction association and evidence list/attachment.
-   AI summary generation/view/history with structured presentation.
-   Human resolution and terminal resolved-case view.
-   Core loading, error, empty, conflict, and authorization states.
-   Responsive behavior and accessibility for core workflows.

### 14.2 Not a first-release blocker unless separately prioritized

-   Dedicated User Management screen, pending confirmed user-management
    API.
-   Dedicated Audit History screen, pending confirmed audit read API.
-   Rich account behavior drill-down, pending stable endpoint/response
    contracts.
-   Advanced merchant/device/location detail pages where only list or
    summary references exist.
-   Export workflows unless the backend API and security policy are
    documented.
-   Real-time alerts, streaming, graph visualization, or autonomous
    workflows.

## 15. Acceptance Criteria

The frontend MVP is acceptable when the following end-to-end scenarios
pass against a real or contract-faithful backend environment.

### AC-001 --- Authentication and role context

-   A valid user can sign in and load their current-user context.
-   An invalid or expired session cannot access protected data.
-   The interface reflects the user's role without treating client-side
    checks as authorization.

### AC-002 --- Dataset import

-   An Admin and Analyst can upload a valid supported CSV.
-   The UI displays the backend's import ID/status, row counts,
    timestamps, and duplicate result.
-   Invalid or oversized uploads display the backend error meaningfully.
-   An Investigator cannot access the import action unless backend
    policy changes.

### AC-003 --- Transaction exploration

-   A user can browse transactions using server pagination.
-   Supported filters are sent to the API and reflected in the visible
    filter state.
-   Transaction detail values match the API response.
-   Missing risk analysis is not displayed as a zero score or low-risk
    result.

### AC-004 --- Analytics

-   Dashboard/analytics values match backend responses.
-   Namespace, currency, date range, and timezone context are visible
    where applicable.
-   The browser does not compute replacement totals or risk values.
-   Account-level analytics (`/analytics/accounts/{account_id}` and `/unusual-spending`) are excluded from MVP Phase F3 and deferred to a dedicated account intelligence phase.

### AC-005 --- Risk analysis

-   Users can retrieve persisted risk results.
-   On-demand analysis controls are exposed only for permitted
    role/model combinations.
-   Risk factors are inspectable.
-   The UI never labels a risk result as a final fraud decision.

### AC-006 --- Investigation creation and queue

-   An authorized user can create an investigation for a primary
    transaction with priority (defaults to `MEDIUM`; no creation notes per backend contract).
-   The resulting case appears as `OPEN` and unassigned.
-   Queue filters and pagination match the API contract.
-   The UI does not claim automatic case creation.

### AC-007 --- Assignment and lifecycle

-   Investigators can self-assign eligible unassigned cases and cannot
    take peer-assigned cases.
-   Admins can exercise the assignment authority documented by the API.
-   Invalid transitions and concurrent assignment conflicts are
    displayed accurately.
-   Resolved cases cannot be mutated through the UI.

### AC-008 --- Related transactions and evidence

-   The UI can display primary and related transaction associations.
-   The UI only offers related-transaction actions within the backend's
    supported 1-hop behavior.
-   Authorized users can attach valid evidence.
-   Existing evidence is immutable in the interface.

### AC-009 --- AI summary

-   Authorized users can request a summary; Analysts can inspect
    summaries only where permitted.
-   Summary output is separated into the defined structured sections.
-   Evidence citations/IDs are visible and navigable where supported.
-   AI output is labeled advisory and never presented as a final
    decision.

### AC-010 --- Human resolution

-   Only an Admin or assigned Investigator can resolve a case, subject
    to backend authorization.
-   One of the four allowed outcomes and non-empty notes are required.
-   After successful resolution, the case is visibly terminal and
    read-only.

### AC-011 --- Failure handling

-   `401`, `403`, `404`, `409`, `413`, `422`, network, and server
    failures produce understandable UI states.
-   A failed request is never represented as an empty successful result.
-   After a conflict, the frontend refreshes authoritative state before
    offering another action.

### AC-012 --- Accessibility and data integrity

-   Core flows are keyboard operable and have visible focus.
-   Status/risk semantics are not conveyed by color alone.
-   Monetary values preserve backend precision and currency.
-   No authoritative balance, aggregate, behavioral feature, or risk
    score is calculated in the browser.

## 16. Backend Contract Dependencies and Gaps

The following are material integration dependencies. They must be
resolved or explicitly scoped out before the related frontend screens
are committed to implementation.

  ------------------------------------------------------------------------
  Area                    Current documentation   Frontend implication /
                          evidence                required action
  ----------------------- ----------------------- ------------------------
  Transaction browsing    `API_GUIDELINES.md`     `GET /transactions` and
  and detail              describes `/transactions` `GET /transactions/{id}`
                          and `/{id}`, but these  are not implemented in
                          routes are not in the   the backend. Must be
                          FastAPI router. Only    implemented in Phase F0
                          risk endpoints exist.   before building F3.

  Dataset import listing  `POST /imports` and     Users cannot browse past
                          `GET /imports/{id}` exist imports in the UI without
                          in backend, but no list a list endpoint. Must be
                          endpoint exists.        implemented in Phase F0
                                                  before building F4.

  Account detail and      `API_GUIDELINES.md`     Do not assume a stable
  behavior                describes account       account-detail contract.
                          detail/behavior         Confirm implemented
                          response sections as    routes and schemas
                          potential and labels    before building a rich
                          the behavior endpoint   Account Detail page.
                          as potential.           

  Merchant and device     Endpoint summary        Confirm exact
  detail                  references these        list/detail routes,
                          domains, but this PRD   filters, response
                          does not establish a    schemas, and
                          complete detail-screen  authorization before
                          contract.               adding drill-down
                                                  screens.

  User management         Admin-only user         Keep User Management out
                          management appears in   of the first release
                          the product/role        until routes, schemas,
                          requirements, but a     lifecycle, and
                          complete                authorization are
                          user-management API     confirmed.
                          contract is not         
                          established in the      
                          reviewed endpoint       
                          inventory.              

  Audit history           Auditability is a       Do not invent an audit
                          product requirement,    endpoint. Confirm
                          but a                   whether a read API
                          frontend-consumable     exists and its
                          audit read/list         filtering/pagination
                          contract is not         semantics.
                          established in the      
                          reviewed API sections.  

  Risk monitoring         Risk is exposed through Treat initial risk
                          transaction risk        monitoring as a filtered
                          read/analyze endpoints; transaction/risk
                          there is no basis here  experience, not a live
                          for a separate alert    alert center.
                          feed or real-time       
                          monitoring service.     

  Authentication          Login/current-user and  Finalize token/session
  lifecycle               bearer-token flow are   behavior in
                          documented; token       `FRONTEND_SECURITY.md`
                          expiration, revocation, before implementation.
                          and refresh decisions   
                          remain listed as open   
                          API decisions.          

  RBAC matrix             PRD conceptual          Use endpoint-level
                          permissions and API     API/security rules as
                          endpoint-specific rules current behavior;
                          differ in some places.  reconcile stale
                                                  conceptual tables in the
                                                  source docs.

  OpenAPI contract        API guidelines identify Generate frontend types
                          OpenAPI as the contract from the actual backend
                          source, but acceptance  OpenAPI schema only
                          items still include     after verifying it
                          verification of         matches implemented
                          generated schema and    routes and schemas.
                          contract completeness.  
  ------------------------------------------------------------------------

### 16.1 Known documentation inconsistencies to review

1.  The high-level PRD role table suggests Analysts may have some
    investigation review/resolve capabilities, while the implemented API
    contract restricts investigation PATCH and resolution to
    Admin/Investigator and makes Analysts read-oriented for AI
    summaries. The frontend must follow the endpoint-level contract
    until the documents are reconciled.
2.  The PRD describes broad account behavioral analysis, but the API
    account behavior section is marked potential. A product requirement
    does not create an implemented endpoint.
3.  Auditability is required, but audit-event creation and audit-event
    browsing are separate capabilities. A frontend audit screen requires
    a read API, not merely the existence of backend audit writes.
4.  Risk monitoring must not be described as real-time alerting because
    real-time alerting is explicitly deferred.

These are documentation/API readiness issues, not reasons to invent
frontend-side workarounds.

## 17. Dependencies on Other Documents

  -----------------------------------------------------------------------
  Document                            Responsibility
  ----------------------------------- -----------------------------------
  `FRONTEND_DESIGN.md`                Visual language, component
                                      appearance, information hierarchy,
                                      responsive and accessibility design
                                      rules

  `FRONTEND_TRD.md`                   Approved frontend stack,
                                      dependencies, tooling, build,
                                      environment, and performance
                                      budgets

  `FRONTEND_ARCHITECTURE.md`          App structure, feature boundaries,
                                      state ownership, routing, API
                                      client, and data flow

  `FRONTEND_API_INTEGRATION.md`       Exact endpoint integration,
                                      generated types, request/response
                                      handling, pagination, errors, and
                                      uploads

  `FRONTEND_SECURITY.md`              Token/session storage, browser
                                      security, XSS/CSRF posture,
                                      sensitive-data handling, and
                                      authorization behavior

  `FRONTEND_TESTING_STRATEGY.md`      Unit, component, integration, E2E,
                                      accessibility, and contract testing

  `FRONTEND_ROADMAP.md`               Sequencing, milestones,
                                      dependencies, and phase exit
                                      criteria

  `PRD.md`                            Overall product scope and domain
                                      requirements

  `API_GUIDELINES.md`                 Backend API contract and
                                      endpoint-level authorization

  `SECURITY.md`                       Platform security requirements and
                                      threat model

  `ARCHITECTURE.md`                   System boundaries and
                                      backend/frontend responsibility
                                      split

  `PROJECT_ROADMAP.md`                Master project roadmap
  -----------------------------------------------------------------------

## 18. Open Product Decisions

The following decisions require explicit review; this document does not
silently decide them:

1.  What should the default landing page be for each role: Dashboard or
    Investigation Queue?
2.  Should the initial Risk Monitoring navigation item be a
    saved/filterable transaction view or omitted in favor of
    Transactions?
3.  Which namespace/currency/date filters should persist between
    sessions, if any?
4.  Should users be allowed to register from the frontend, or should
    accounts be provisioned administratively? The API documents
    registration, but the operational product policy is not settled
    here.
5.  Is account detail a first-release requirement, and if so, which
    implemented endpoint/schema supports it?
6.  Are user management and audit-history browsing required in the
    frontend MVP, and what exact API contracts support them?
7.  What frontend-visible statuses exist for AI summary generation in
    all failure/recovery cases, and how should retry be exposed?
8.  Which export/download actions, if any, are permitted for
    transaction, evidence, and investigation data?

## 19. Definition of Done

This document is ready to guide technical design when:

-   Product scope, user roles, and core workflows have been reviewed.
-   MVP screens are mapped to existing or explicitly planned API
    contracts.
-   Backend contract gaps are accepted, resolved, or excluded from MVP.
-   Role/assignment behavior is reconciled with the endpoint-level
    API/security rules.
-   Product and security open decisions that block architecture are
    assigned for resolution.
-   Acceptance criteria are agreed upon by the project owner.

## 20. Final Product Principle

FinSignal's frontend must make financial intelligence and investigation
evidence easier to understand without changing what the backend has
established as fact.

**The interface organizes and explains authoritative data; it does not
manufacture financial truth, convert risk into guilt, or replace human
investigation judgment.**
