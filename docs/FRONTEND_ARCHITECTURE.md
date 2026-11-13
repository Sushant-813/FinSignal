# FinSignal — Frontend Architecture Document

**Document:** `FRONTEND_ARCHITECTURE.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.1  
**Status:** Synchronized with Phase F2 Implementation Baseline (F2 Auth & Shell Implemented and Locally Verified; Feature Modules Pending Phase F3+)
**Scope:** Browser frontend architecture  
**Prerequisites:** `FRONTEND_PRD.md`, `FRONTEND_TRD.md`, and `FRONTEND_DESIGN.md`

---

## 1. Purpose

This document defines the structural architecture of the FinSignal frontend: its application boundaries, feature modules, dependency direction, routing, state ownership, API integration, and principal data flows.

The frontend is a separate client of the existing FastAPI backend. It presents and orchestrates user interactions with backend capabilities. It does not become a second implementation of the financial intelligence domain.

The backend remains authoritative for:

- Transaction and account facts.
- Monetary values and financial aggregates.
- Behavioral features and analytics.
- ML model execution and risk assessments.
- Risk factors and explainability data.
- Investigation lifecycle and assignment.
- Evidence validation, persistence, and immutability.
- AI summary generation, grounding, and staleness.
- Authentication and authorization.
- Audit records.

This document describes a target architecture. It does not claim that the frontend codebase or proposed modules have already been implemented.

## 2. Architecture Goals

The frontend architecture must:

1. Separate application shell, feature workflows, shared UI, and API infrastructure.
2. Keep API access centralized and typed.
3. Keep server state distinct from local interaction state.
4. Make feature ownership and dependency direction clear.
5. Make role- and assignment-aware presentation consistent.
6. Preserve the backend's financial and investigative semantics.
7. Handle asynchronous operations and partial failures without misleading the user.
8. Keep test seams at the API and feature boundaries.
9. Support independent frontend/backend development through the OpenAPI contract.
10. Avoid premature abstractions, duplicated domain logic, and unnecessary global state.

## 3. System Context and Trust Boundaries

### 3.1 Context diagram

```text
+----------------------------------------------------------+
|                       User Browser                       |
|                                                          |
|  +-------------------- FinSignal UI -------------------+ |
|  | App Shell | Routes | Feature Pages | Shared UI      | |
|  |           |        |               |                | |
|  | Auth UI   | Query Hooks | Forms | Tables | Charts   | |
|  +--------------------------+---------------------------+ |
|                             |                             |
|                             v                             |
|  +----------------------------------------------------+  |
|  | Frontend Infrastructure                            |  |
|  | API Client | Generated Types | Error Mapping       |  |
|  | Session Adapter | Formatting | Permission Helpers  |  |
|  +--------------------------+-------------------------+  |
+-----------------------------|----------------------------+
                              |
                      HTTPS / REST / JSON
                       /api/v1 + Bearer auth
                              |
                              v
+----------------------------------------------------------+
|                    FastAPI Backend                       |
|                                                          |
| Auth / RBAC | Domain Services | Analytics | ML / Risk    |
| Ingestion   | Investigations  | Evidence  | AI Summary  |
|                         |                                |
|                         v                                |
|                    PostgreSQL                            |
+----------------------------------------------------------+
```

### 3.2 Trust boundaries

- The browser is an untrusted client.
- All client input is untrusted, including values that passed frontend validation.
- The backend validates requests and enforces authorization.
- The frontend may improve usability through client-side validation and permission-aware controls, but neither is a security boundary.
- The frontend must not connect directly to PostgreSQL or any internal backend repository.
- No privileged secrets or model-provider credentials may be included in the browser bundle.
- The frontend must not submit arbitrary prompts to the production investigation-summary capability; the backend controls the AI context.

### 3.3 Responsibility split

| Concern | Frontend responsibility | Backend responsibility |
|---|---|---|
| Authentication | Collect credentials, manage approved client session behavior, show session state | Verify credentials, issue/validate tokens, expose current-user context |
| Authorization | Present role/assignment-aware navigation and actions | Enforce role, object-level, and lifecycle permissions |
| Transactions | Search, filter, paginate, and present records | Validate, query, order, and return transaction facts |
| Monetary data | Format and display returned values | Persist and calculate authoritative monetary values |
| Analytics | Visualize returned aggregates and trends | Compute authoritative aggregates |
| Features | Present available feature/risk explanations | Generate and version behavioral features |
| Risk | Present scores, levels, and factors; request allowed analysis | Execute model/rule analysis and persist results |
| Investigations | Orchestrate user workflows and present case state | Enforce lifecycle, assignment, concurrency, and persistence |
| Evidence | Collect permitted metadata and display immutable records | Validate source/scope, snapshot, persist, and enforce immutability |
| AI summary | Request generation and render structured output | Construct context, generate, validate grounding, track lifecycle/staleness |
| Audit | Present audit records if a read API exists | Record audit events and expose authorized read API if implemented |

## 4. Architectural Style

Use a **feature-oriented React application with shared infrastructure**.

The application is not intended to be:

- A micro-frontend system.
- A collection of independently deployed frontend services.
- A frontend domain-driven design framework with a large abstraction layer.
- A generic low-code or dynamic form engine.

Features should align with user workflows and backend product domains. Shared infrastructure should be small and stable.

## 5. High-Level Application Layers

```text
┌─────────────────────────────────────────────┐
│ Presentation                                │
│ Pages, layouts, shared UI, tables, charts   │
├─────────────────────────────────────────────┤
│ Feature Workflow                            │
│ Feature hooks, mutations, forms, view state │
├─────────────────────────────────────────────┤
│ Application Infrastructure                  │
│ Router, providers, auth/session adapter     │
├─────────────────────────────────────────────┤
│ API Integration                             │
│ Domain API functions, API client, types     │
├─────────────────────────────────────────────┤
│ Backend REST API                             │
│ FastAPI /api/v1                              │
└─────────────────────────────────────────────┘
```

The layers are logical boundaries, not necessarily separate packages.

### 5.1 Presentation layer

Contains:

- Route-level pages.
- Feature-specific UI components.
- Shared controls and data-display components.
- Layouts and navigation.
- Empty, loading, and error presentation.

Presentation components should receive data and callbacks through props or feature hooks. Generic components should not know API route paths, role policy, or backend business rules.

### 5.2 Feature workflow layer

Contains:

- Feature query hooks.
- Feature mutation hooks.
- Form schemas and form orchestration.
- View-specific transformations that do not alter domain meaning.
- Workflow coordination across API operations.

A feature hook may combine multiple backend responses for display composition, but it must not recreate authoritative business calculations.

### 5.3 Application infrastructure layer

Contains:

- Router configuration.
- Application providers.
- Auth/session integration.
- Global error boundaries.
- Theme and application-shell state.
- Route-level lazy loading.

### 5.4 API integration layer

Contains:

- Centralized HTTP client.
- Generated OpenAPI types.
- Domain-specific API functions.
- Error normalization.
- Request cancellation support.
- API contract helpers.

No page should build API URLs independently.

## 6. Proposed Source Structure

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── providers/
│   │   │   ├── AppProviders.tsx
│   │   │   ├── QueryProvider.tsx
│   │   │   └── ThemeProvider.tsx
│   │   ├── router/
│   │   │   ├── routes.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── RoleGate.tsx
│   │   ├── layouts/
│   │   │   ├── AppLayout.tsx
│   │   │   └── AuthLayout.tsx
│   │   └── errors/
│   │       └── RootErrorBoundary.tsx
│   │
│   ├── features/
│   │   ├── auth/
│   │   │   ├── api/
│   │   │   ├── hooks/
│   │   │   ├── pages/
│   │   │   └── types/
│   │   ├── dashboard/
│   │   ├── transactions/
│   │   │   ├── api/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── pages/
│   │   │   └── types/
│   │   ├── analytics/
│   │   ├── accounts/
│   │   ├── datasets/
│   │   ├── risk/
│   │   └── investigations/
│   │       ├── api/
│   │       ├── queue/
│   │       ├── workspace/
│   │       ├── evidence/
│   │       └── ai-summary/
│   │
│   ├── components/
│   │   ├── ui/
│   │   ├── data-display/
│   │   ├── feedback/
│   │   └── forms/
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── errors.ts
│   │   │   ├── generated.ts
│   │   │   └── query-keys.ts
│   │   ├── auth/
│   │   │   └── session-adapter.ts
│   │   ├── permissions/
│   │   ├── formatting/
│   │   └── utils/
│   │
│   ├── hooks/
│   ├── styles/
│   ├── types/
│   └── main.tsx
│
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   └── mocks/
│
├── .env.example
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

This structure is intentionally illustrative for the full MVP; empty feature folders (`src/features/*`, `src/app/layouts/`, `ProtectedRoute.tsx`, `RoleGate.tsx`, `tests/e2e/`) are deferred until their respective Phase F2+ workflows begin.

### 6.1 Implemented Phase F1 Directory Baseline

As of Phase F1 remediation, the actual repository structure in `frontend/` is:

```text
frontend/
├── openapi.json
├── package.json
├── package-lock.json
├── playwright.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── .nvmrc                         # Pinned Node 24 for Vitest 5 compatibility (ADR-079)
├── .env.example
├── .prettierrc.json
├── eslint.config.js
├── scripts/
│   └── check-types-drift.mjs      # Zero-drift OpenAPI check (ADR-076)
├── src/
│   ├── App.tsx                    # Wraps RouterProvider(createAppRouter) inside AppProviders
│   ├── main.tsx
│   ├── index.css                  # Tailwind CSS v4 import, tokens.css, focus/motion base rules
│   ├── vite-env.d.ts
│   ├── api/generated/
│   │   └── schema.ts              # Generated OpenAPI types (read-only / never hand-edited)
│   ├── app/
│   │   ├── errors/
│   │   │   ├── RootErrorBoundary.tsx   # Non-leaky fallback UI + ErrorFallbackView
│   │   │   └── NotFoundPage.tsx        # Fallback route component (*)
│   │   ├── providers/
│   │   │   ├── AppProviders.tsx        # RootErrorBoundary -> QueryProvider composition
│   │   │   └── QueryProvider.tsx       # TanStack QueryClient (retry: false defaults)
│   │   └── router/
│   │       ├── FoundationPage.tsx      # Phase F1 baseline route (/)
│   │       └── routes.tsx              # createBrowserRouter (/ and *) with errorElement
│   ├── components/ui/             # 10 domain-agnostic design-system primitives + barrel index.ts
│   │   ├── Alert.tsx, Badge.tsx, Button.tsx, Card.tsx, Dialog.tsx,
│   │   ├── EmptyState.tsx, Input.tsx, Select.tsx, Skeleton.tsx, Table.tsx, index.ts
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts          # Typed Fetch wrapper, ApiClientError, Bearer injection
│   │   │   └── env.ts             # Public VITE_API_BASE_URL / VITE_APP_ENV loader
│   │   ├── auth/
│   │   │   └── token-store.ts     # Strictly in-memory token store (ADR-075)
│   │   └── utils/
│   │       └── cn.ts              # Plain class concatenation helper (no utility deduplication)
│   └── styles/
│       └── tokens.css             # --fs-* custom properties mapped to Tailwind @theme inline
└── tests/
    ├── setup.ts                   # DOM polyfills, PatchedRequest AbortSignal bridge, MSW hooks
    ├── smoke.test.tsx
    ├── components/                # 11 UI primitive & router resilience test suites
    ├── fixtures/api-errors.ts     # Standard HTTP 401/403/404/409/422/429/500 error builders
    ├── mocks/
    │   ├── handlers.ts            # Empty default handlers (fail fast on unexpected calls)
    │   └── server.ts              # msw/node setupServer
    └── unit/
        ├── api-client.test.ts     # Fetch, FormData, error envelope, in-flight abort tests
        ├── cn.test.ts
        └── zod-rhf.test.tsx       # Zod 4 + @hookform/resolvers compatibility suite
```

Implemented Phase F1 architectural boundaries:
- **Provider Composition (`src/app/providers/`):** `AppProviders` composes `RootErrorBoundary` around `QueryProvider` (`QueryClient` with `queries.retry: false`, `refetchOnWindowFocus: false`, `mutations.retry: false`), wrapping `RouterProvider` in `App.tsx`.
- **Minimal Routing & Error Resilience (`src/app/router/`, `src/app/errors/`):** `createAppRouter()` configures `createBrowserRouter` with `/` (`FoundationPage`) and `*` (`NotFoundPage`), each guarded by `errorElement: <ErrorFallbackView />`. `RootErrorBoundary` suppresses raw stack traces and internal payloads while allowing safe reload/return-home recovery.
- **UI Primitive Boundary (`src/components/ui/`):** All 10 primitives are domain-agnostic and import zero feature APIs, auth state, or domain labels; `cn()` performs pure concatenation, requiring components to emit mutually exclusive state utilities.
- **API, Env & Token Boundaries (`src/lib/`):** `frontendEnv` exposes only public `VITE_*` configuration; `token-store.ts` holds access tokens strictly in memory (`ADR-075`); `apiRequest()` handles JSON/multipart serialization, Bearer injection, and backend error-envelope normalization (`F1-AUD-005` edge-case hardening deferred to Phase F2).
- **Testing & MSW Boundary (`tests/`):** Global `beforeAll` starts `msw/node` with `onUnhandledRequest: "error"`; `afterEach` runs RTL `cleanup()`, `server.resetHandlers()`, and `clearAccessToken()`. Committed `tests/e2e/` Playwright tests remain deferred to Phase F2 (`F1-AUD-006`).

### 6.2 Implemented Phase F2 Directory Baseline (2026-11-11)

Following completion of Phase F2 (`F2.1`–`F2.6`), the actual implemented frontend structure adds authentication, protected routing, role capabilities, and the application shell while retiring `FoundationPage.tsx`:

```text
frontend/
├── playwright.config.ts                       # Fresh-build preview webServer (reuseExistingServer: false) & live mode
├── package.json                               # Includes "test:e2e": "playwright test"
├── src/
│   ├── app/
│   │   ├── errors/{RootErrorBoundary.tsx,NotFoundPage.tsx}
│   │   ├── layouts/{AuthLayout.tsx,AppLayout.tsx}
│   │   ├── providers/{AppProviders.tsx,QueryProvider.tsx}
│   │   ├── router/{ProtectedRoute.tsx,PublicOnlyRoute.tsx,RoleGate.tsx,SessionLoadingView.tsx,WorkspaceHomePage.tsx,PhasePlaceholderPage.tsx,routes.tsx}
│   │   └── shell/{Sidebar.tsx,TopBar.tsx,UserMenu.tsx,nav-config.ts}
│   ├── features/auth/
│   │   ├── api/auth-api.ts                    # login, getCurrentUser, logout (OpenAPI-typed)
│   │   ├── context/{AuthContext.ts,AuthProvider.tsx}
│   │   ├── hooks/useAuth.ts
│   │   ├── pages/LoginPage.tsx
│   │   ├── schemas/login-schema.ts            # Zod 4 LoginRequest schema (password 1..128)
│   │   └── types/auth.types.ts                # isUserRole, parseAuthUser, AuthUser, AuthStatus, SessionNotice
│   └── lib/
│       ├── api/{client.ts,env.ts,errors.ts}
│       ├── auth/{redirect.ts,session-events.ts,token-store.ts}
│       └── permissions/capabilities.ts        # F2 capabilities: canViewDatasetImports vs canManageDatasets
└── tests/
    ├── fixtures/{api-errors.ts,auth.ts}
    ├── smoke.test.tsx
    ├── components/{...,app-shell.test.tsx,login-page.test.tsx,protected-routes.test.tsx,resilience.test.tsx}
    ├── unit/{api-client.test.ts,auth-api.test.ts,capabilities.test.ts,cn.test.ts,redirect.test.ts,session-lifecycle.test.tsx,zod-rhf.test.tsx}
    └── e2e/{helpers/auth-mock.ts,auth.spec.ts,shell.spec.ts}
```

Implemented Phase F2 architectural boundaries:
- **Provider Composition (`src/app/providers/`):** `AppProviders` composes `RootErrorBoundary` -> `QueryProvider` -> `AuthProvider`, wrapping `RouterProvider` in `App.tsx`.
- **Auth State vs. Token Boundary (`src/lib/auth/`, `src/features/auth/`):** `token-store.ts` holds only module-scoped `accessToken` and monotonic `sessionEpoch`; `session-events.ts` bridges `401` detection in `client.ts` to `AuthProvider` without circular imports; `AuthContext.ts` stays separated from `AuthProvider.tsx` (`react-refresh/only-export-components`).
- **Routing & Navigation (`src/app/router/`, `src/app/shell/`):** `routes.tsx` serves `/login` inside `PublicOnlyRoute` -> `AuthLayout`, protected routes (`/`, `/transactions`, `/analytics`, `/investigations`, `/datasets`) inside `ProtectedRoute` -> `AppLayout`, and `*` -> `NotFoundPage`. Future F3–F5 modules render `PhasePlaceholderPage` with zero fabricated data; `/accounts`, `/audit`, and `/admin/users` are omitted.
- **API & Errors (`src/lib/api/`):** `env.ts` validates base URL schemes, query/fragment rejection, and production HTTPS; `client.ts` normalizes `NETWORK_ERROR`/`INVALID_RESPONSE`/FinSignal + FastAPI error envelopes and enforces `authMode`; `errors.ts` provides pure status guards and `422` field error extraction.
- **Testing & E2E (`tests/`):** `22` Vitest/MSW test files (`87` tests) plus mocked Chromium Playwright E2E (`5` tests against built `vite preview`).

## 7. Feature Boundaries and Responsibilities

### 6.3 Implemented Phase F3 Directory Baseline

```text
frontend/src/
├── app/
│   ├── layouts/
│   │   ├── AppLayout.tsx               # Main application shell with TopBar and Sidebar
│   │   └── AuthLayout.tsx              # Unauthenticated card container
│   ├── router/
│   │   ├── routes.tsx                  # Full router with /, /analytics, /transactions, /transactions/:id
│   │   ├── ProtectedRoute.tsx          # Session authentication & authorization boundary
│   │   └── PhasePlaceholderPage.tsx    # Honest placeholder for future phases (F4, F5)
│   └── shell/
│       ├── Sidebar.tsx                 # Navigation with active state & role visibility
│       ├── TopBar.tsx                  # Header with user menu & session status
│       └── nav-config.ts               # Primary navigation items
├── components/
│   ├── data-display/
│   │   ├── MoneyValue.tsx              # Exact string-safe MoneyStr decimal rendering
│   │   ├── TimestampDisplay.tsx        # Timezone-aware UTC timestamp presentation
│   │   └── RiskBadge.tsx               # Categorical tier badges (LOW, MEDIUM, HIGH, CRITICAL, NOT_ANALYZED)
│   └── ui/
│       └── Pagination.tsx              # Server-side pagination controls (first/prev/pages/next/last)
├── features/
│   ├── dashboard/
│   │   ├── pages/DashboardPage.tsx     # Operational overview landing page (/)
│   │   ├── components/OverviewKpiGrid.tsx
│   │   └── components/ReportingScopeBar.tsx
│   ├── analytics/
│   │   ├── api/analytics-api.ts        # Typed client for trends, categories, and merchants
│   │   ├── pages/AnalyticsPage.tsx     # Multi-tab analytics hub (/analytics)
│   │   ├── components/TrendsChartPanel.tsx
│   │   ├── components/TrendEChart.tsx  # Dynamically imported Apache ECharts wrapper
│   │   ├── components/CategoryDistributionPanel.tsx
│   │   └── components/MerchantAnalyticsPanel.tsx
│   ├── transactions/
│   │   ├── api/transactions-api.ts    # Typed client for transaction list and detail
│   │   ├── pages/TransactionsListPage.tsx # Explorer (/transactions) with URL param state
│   │   ├── pages/TransactionDetailPage.tsx # Detail (/transactions/:id)
│   │   ├── components/TransactionFiltersBar.tsx
│   │   ├── components/TransactionTable.tsx
│   │   ├── components/TransactionFactsCard.tsx
│   │   └── components/TransactionRelationsCard.tsx
│   └── risk/
│       ├── api/risk-api.ts             # Typed client for risk retrieval and analyze action
│       ├── components/RiskAnalysisPanel.tsx # Hybrid risk scores, breakdown, analyze trigger
│       └── components/RiskFactorList.tsx # Structured factor explainability list
└── lib/
    ├── api/
    │   └── query-keys.ts               # Centralized TanStack Query cache keys
    ├── formatting/
    │   ├── money.ts                    # formatMoney, formatMoneyParts
    │   └── datetime.ts                 # formatUtcDateTime, formatUtcDate, toUtcIsoString
    └── permissions/
        └── capabilities.ts             # canAnalyzeActiveRisk, canAnalyzeValidatedRisk

```

---

### 7.1 Authentication (`features/auth`)

Owns:

- Login page and credential form.
- Current-user query.
- Authentication lifecycle UI.
- Logout interaction.
- Session-expiration presentation.

Does not own:

- JWT signing or validation.
- Server-side token revocation.
- Backend role policy.
- Token persistence choice independent of `FRONTEND_SECURITY.md`.

Exports a small auth-facing interface to the application shell, such as current user, authentication status, and sign-out action. Avoid exposing token internals to ordinary feature components.

### 7.2 Dashboard (`features/dashboard`)

Owns:

- Overview page composition.
- Summary metric panels.
- Links into relevant feature screens.
- Dashboard filter state.

Consumes analytics API responses. It must not calculate dashboard totals from a transaction list.

### 7.3 Transactions (`features/transactions`)

Owns:

- Transaction list and filter controls.
- Server pagination and sorting state.
- Transaction detail page.
- Transaction fact presentation.
- Entry point to risk analysis and investigation creation.

Risk assessment may be displayed through a shared risk component or risk feature API, but transaction components must not implement risk scoring.

### 7.4 Analytics (`features/analytics`)

Owns:

- Analytics filter controls.
- Trend/category/merchant chart composition.
- Chart-to-table alternatives.
- Reporting-context display.

Consumes server-computed analytics responses. It may transform response shape into chart-library series, but must not recalculate the underlying aggregates.

### 7.5 Accounts (`features/accounts`)

Owns account list and any account detail UI supported by a confirmed API contract.

**Contract constraint:** the account behavior/detail API readiness must be verified. Do not build a rich account behavior page around a proposed or undocumented endpoint.

### 7.6 Datasets (`features/datasets`)

Owns dataset CSV selection, client-side preflight validation, multipart upload ingestion, import history ledger, status polling lifecycle, execution metrics, validation error inspection, and failed import recovery.

The browser does not parse and reimplement the complete backend ingestion pipeline. It sends the file through native `FormData` and presents backend-authoritative ingestion results.

#### Module Organization

The dataset feature follows the standardized domain layer structure:

```text
features/datasets/
├── api/              # OpenAPI-typed network fetchers (uploadDataset, listDatasetImports, getDatasetImportDetail, recoverDatasetImport)
├── components/       # Presentation & interaction: DatasetImportTable, DatasetFiltersBar, DatasetUploadCard, DatasetRecoveryDialog, DatasetImportErrorTable, DatasetImportStatusBadge
├── hooks/            # TanStack Query hooks and lifecycle tracker: useDatasetImportsListQuery, useDatasetImportDetailQuery, useUploadDatasetMutation, useRecoverDatasetMutation, useDatasetFilterParams, polling-tracker
├── pages/            # View composition: DatasetsPage (/datasets), DatasetImportDetailPage (/datasets/imports/:importId)
├── schemas/          # Zod validation: datasetUploadSchema (50 MB limit, .csv check) & datasetFilterSchema (UTC calendar day boundaries)
└── types/            # Domain interfaces: DatasetImportSummary, DatasetImportDetail, filter state, and status enums
```

#### Polling Architecture & Abandoned Import Safeguard

To track ingestion progress without overloading the backend or running runaway background timers, the polling lifecycle is managed by an in-memory session tracker (`polling-tracker.ts`):

- **Mechanism:** Maintains an in-memory `Map<string, number>` mapping active `import_id` strings to their first observed polling epoch timestamp (`Date.now()`).
- **Interval:** When any visible import row is in an active state (`PENDING` or `PROCESSING`), TanStack Query executes a `refetchInterval` of **5 seconds** (5,000 ms).
- **Cutoff:** Polling automatically ceases when `Date.now() - firstObserved >= 300,000 ms` (5 minutes). This safeguard prevents browser sessions from polling indefinitely if a backend worker is killed or an import remains permanently stalled in `PROCESSING`.
- **Terminal Cleanup:** When an import transitions to a terminal state (`COMPLETED` or `FAILED`), its entry is removed from the tracker and `refetchInterval` is automatically disabled.
- **Session Lifecycle:** The in-memory tracker survives React component remounts and client-side SPA route navigation within the active window tab. A hard browser reload (F5) resets the memory map, allowing a fresh 5-minute monitoring window.
- **Manual Control:** Once the cutoff threshold is reached, automatic polling stops cleanly, the last known status is preserved, and a prominent manual refresh button is surfaced. Automated recovery is never triggered as a side-effect of polling expiration.
- **Storage Independence:** The tracker strictly operates in transient JavaScript memory and does not write to `localStorage` or `sessionStorage`.

### 7.7 Risk (`features/risk`)

Owns reusable risk-result presentation and risk-analysis request orchestration.

Responsibilities:

- Display backend risk level and score.
- Display returned risk factors.
- Display missing/stale/failed states where represented by the API.
- Expose analysis actions only when role and model lifecycle allow them.

It does not own model internals, feature engineering, threshold logic, or fraud decisions.

If the first release has no distinct risk queue API, Risk should remain a reusable feature capability and a filtered transaction view—not a separate invented alert subsystem.

### 7.8 Investigations (`features/investigations`)

Phase F5 implements the core investigation queue, workspace, and lifecycle architecture:

- **Queue (`InvestigationsQueuePage` at `/investigations`):** Server-side paginated queue table displaying case ID, operational status badge, priority badge, primary transaction ID, assignee email/UUID, and deterministic UTC timestamps. Synchronized via `useInvestigationFilterParams` (`status`, `priority`, `page`, `page_size`, `assigned_to`, `unassigned`) with strict mutual exclusivity between `assigned_to` and `unassigned=true`. Server ordering is authoritative: `created_at DESC, id DESC`.
- **Case Creation (`InvestigationCreateDialog`):** Modal dialog accessible from the queue header and from `TransactionDetailPage` ("Investigate Transaction" button, pre-populating and locking the transaction UUID). Validates target transaction UUID and priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, default `MEDIUM`). In accordance with backend schema `InvestigationCreateRequest` (`extra="forbid"`), initial creation notes are not accepted.
- **Workspace (`InvestigationWorkspacePage` at `/investigations/:investigationId`):** Aggregate workspace loading the authoritative `InvestigationDetailResponse` envelope in a single query (`useInvestigationDetailQuery`) avoiding N+1 requests:
  - `InvestigationWorkspaceHeader`: Case metadata and role-gated lifecycle mutation triggers.
  - `InvestigationPrimaryTransactionCard`: Authoritative immutable transaction facts formatted with `<MoneyValue>` and `<TimestampDisplay>` with direct link to transaction explorer.
  - `InvestigationLatestRiskCard`: Static snapshot of risk score and level recorded at case creation.
  - `InvestigationRelatedTransactionsCard`: Displays linked transactions and triggers linking modal.
  - `InvestigationResolutionBanner`: Prominent read-only banner rendered when `status === "RESOLVED"`, showing resolution verdict, audit notes, resolver, and timestamp.
  - Phase F6 placeholders (`InvestigationEvidencePlaceholderCard`, `InvestigationAiSummaryPlaceholderCard`): Honest visual placeholders indicating deferred F6 functionality without broken interactions.
- **Lifecycle & Concurrency:** Lifecycle mutations (`usePatchInvestigationMutation`, `useResolveInvestigationMutation`, `useLinkTransactionMutation`) handle HTTP `409 Conflict` by alerting the user, dismissing modals, and invalidating `investigationKeys` to reload winning server state. Once resolved, investigations are permanently immutable.

### 7.9 Administration

User Management and Audit History should be added only when their frontend-consumable backend read/mutation contracts are confirmed. Do not create placeholder API modules that imply unavailable functionality.

## 8. Dependency Rules

Allowed dependency direction:

```text
app ───────────────> features
app ───────────────> shared components / lib

feature pages ─────> feature hooks
feature hooks ─────> feature API functions
feature API ───────> shared API client / generated types

feature UI ────────> shared components
shared components ─> design tokens / generic utilities
```

Prohibited dependency direction:

```text
shared UI ─────────> feature API
API client ────────> React page components
generic formatting > feature business rules
feature A ─────────> feature B internal files
```

Cross-feature interaction should use a public feature export, a route transition, or a shared application-level workflow. Do not import another feature's private component or internal hook.

## 9. Routing Architecture

Use a centralized route definition and layout nesting.

Conceptual route tree:

```text
Root
├── Public
│   └── /login
└── Protected Application
    ├── AppLayout
    │   ├── /
    │   ├── /dashboard
    │   ├── /transactions
    │   ├── /transactions/:transactionId
    │   ├── /analytics
    │   ├── /accounts
    │   ├── /accounts/:accountId       (contract-dependent)
    │   ├── /datasets                  (Admin / Analyst)
    │   ├── /investigations
    │   ├── /investigations/:id
    │   └── /admin/users               (contract-dependent)
    └── Not Found
```

Implemented Phase F2 route tree mounts `/login` (public-only under `AuthLayout`), `/` (`WorkspaceHomePage` default overview), `/transactions`, `/analytics`, `/investigations`, and `/datasets` (honest `PhasePlaceholderPage`s under `ProtectedRoute` + `AppLayout`), and `*` (`NotFoundPage`). `/accounts`, `/audit`, and `/admin/users` remain omitted until backend contracts exist.

### 9.1 Protected route behavior

A protected route should:

1. Wait for session initialization.
2. Load or validate current-user context.
3. Redirect unauthenticated users to login.
4. Render authorized route content.
5. Avoid flashing protected content while authentication is unresolved.

Route protection does not replace backend checks. In Phase F2, `ProtectedRoute` and `PublicOnlyRoute` render neutral `SessionLoadingView` while `status === "initializing"`; deliberate `signOut()` sets `preserveRedirectOnUnauthenticated = false` so signing out from nested routes lands cleanly on `/login` without stale `?redirect=` query strings.

### 9.2 Role and object gates

Centralized capability helpers in `src/lib/permissions/capabilities.ts` fail closed when user is missing, `is_active !== true`, or `isUserRole(user.role)` is `false`:

```text
// Core navigation capabilities (F2–F5)
canAccessWorkspace(user)         // ADMIN | ANALYST | INVESTIGATOR
canViewTransactions(user)        // ADMIN | ANALYST | INVESTIGATOR
canViewAnalytics(user)           // ADMIN | ANALYST | INVESTIGATOR
canViewInvestigations(user)      // ADMIN | ANALYST | INVESTIGATOR
canViewDatasetImports(user)      // ADMIN | ANALYST | INVESTIGATOR (read-only import history)
canManageDatasets(user)          // ADMIN | ANALYST (upload & recovery)

// Risk analysis capabilities (F3)
canAnalyzeActiveRisk(user)       // ADMIN | ANALYST | INVESTIGATOR
canAnalyzeValidatedRisk(user)    // ADMIN only

// Investigation lifecycle capabilities (F5)
canCreateInvestigation(user)                                  // ADMIN | ANALYST | INVESTIGATOR
canModifyInvestigation(user, investigation)                   // ADMIN, or INVESTIGATOR if assigned to self/unassigned; false if RESOLVED
canSelfAssignInvestigation(user, investigation)               // INVESTIGATOR if unassigned; ADMIN if not self; false if RESOLVED
canSelfUnassignInvestigation(user, investigation)             // ADMIN or INVESTIGATOR if assigned to self; false if RESOLVED
canAdminAssignInvestigation(user, investigation?)             // ADMIN only; false if investigation.status === "RESOLVED"
canUpdateInvestigationPriority(user, investigation)           // ADMIN, or INVESTIGATOR if assigned to self; false if RESOLVED
canTransitionInvestigation(user, investigation)               // OPEN -> UNDER_REVIEW: ADMIN, or INVESTIGATOR if assigned to self
canLinkInvestigationTransaction(user, investigation)          // ADMIN, or INVESTIGATOR if assigned to self; false if RESOLVED
canResolveInvestigation(user, investigation)                  // Case must be UNDER_REVIEW: ADMIN, or INVESTIGATOR if assigned to self

getDefaultAuthenticatedRoute(user)
```

*(Evidence attachment and AI-summary generation capabilities remain planned for Phase F6.)*

These helpers are UI policy adapters, not authorization engines. Backend `403` responses remain authoritative.

Do not duplicate the same role comparison in many page components.

### 9.3 Default route

The default landing page per role (`Dashboard` vs `Investigation Queue`) remains an open product decision. Phase F2 routes authenticated `/` to `WorkspaceHomePage` via `getDefaultAuthenticatedRoute(user)` so Phases F3–F5 can adjust role landing targets in one place.

## 10. State Ownership Architecture

The application uses three primary state categories.

### 10.1 Server state

Server state is data owned by the backend and retrieved through API requests.

Examples:

- Current-user profile.
- Transactions and accounts.
- Analytics.
- Dataset imports.
- Risk analyses.
- Investigations and assignments.
- Evidence.
- AI summaries.

If TanStack Query is approved, it owns server-state caching, request status, refetching, and invalidation. Do not mirror these entities in Zustand or a separate global store.

### 10.2 Local UI state

Local UI state is transient interaction state:

- Open/closed dialogs.
- Expanded table rows.
- Selected tab.
- Sidebar collapse state.
- Temporary form input before submission.
- Unsaved filter-panel visibility.

Prefer component state. Lift state only to the nearest common owner that needs it.

### 10.3 URL state

State that should survive refresh, be bookmarkable, or be shareable belongs in URL query parameters when safe:

- Search term.
- Supported filters.
- Sort field/order.
- Page/cursor.
- Selected date range.

Do not place tokens, sensitive evidence, private notes, or confidential payloads in URLs.

### 10.4 Query key design

Query keys must encode every parameter that changes the response.

Examples:

```ts
const transactionKeys = {
  all: ["transactions"] as const,
  lists: () => [...transactionKeys.all, "list"] as const,
  list: (filters: TransactionFilters) =>
    [...transactionKeys.lists(), filters] as const,
  detail: (id: string) =>
    [...transactionKeys.all, "detail", id] as const,
};

const analyticsKeys = {
  all: ["analytics"] as const,
  overview: (params: OverviewParams) =>
    [...analyticsKeys.all, "overview", params] as const,
};

const investigationKeys = {
  all: ["investigations"] as const,
  lists: () => [...investigationKeys.all, "list"] as const,
  list: (params: InvestigationListParams) =>
    [
      ...investigationKeys.lists(),
      {
        page: params.page,
        page_size: params.page_size,
        status: params.status ?? null,
        priority: params.priority ?? null,
        assigned_to: normalizeNullableString(params.assigned_to),
        unassigned: params.unassigned ?? null,
      },
    ] as const,
  details: () => [...investigationKeys.all, "detail"] as const,
  detail: (id: string) => [...investigationKeys.details(), id] as const,
};
```

These are naming examples. Actual query keys must use the verified request parameter types.

Include namespace, currency, date boundaries, timezone, page/cursor, and filters where they affect the response. Avoid putting access tokens or other secrets in query keys.

### 10.5 Mutation and cache policy

- After successful mutations, invalidate the smallest relevant query set.
- For assignment, status transition, evidence attachment, and resolution, prefer the authoritative server response or refetch.
- Avoid optimistic updates for terminal or concurrency-sensitive actions unless the rollback and conflict semantics are rigorously defined.
- Do not automatically retry non-idempotent requests without an explicit backend idempotency contract.
- When a `409` indicates stale/concurrent state, refetch the resource before allowing a retry.

## 11. API Integration Architecture

### 11.1 Centralized API client

All HTTP requests pass through a single API client abstraction.

Responsibilities:

- Resolve the configured API base URL.
- Add approved authentication context.
- Serialize JSON bodies.
- Handle multipart requests without manually setting the boundary.
- Parse JSON and empty responses.
- Normalize backend errors.
- Pass cancellation signals.
- Preserve safe request metadata such as correlation IDs.

The client must not contain domain workflows such as investigation resolution rules or risk calculations.

### 11.2 Domain API modules

Each feature owns its API functions:

```text
features/
  transactions/api/transactions-api.ts
  analytics/api/analytics-api.ts
  datasets/api/datasets-api.ts
  risk/api/risk-api.ts
  investigations/api/investigations-api.ts
```

Functions should be named by domain action, accept typed parameters, and return typed API data.

Example conceptual interface:

```ts
getTransactions(filters, signal)
getTransaction(transactionId, signal)
getTransactionRisk(transactionId, signal)
requestRiskAnalysis(transactionId, request)
createInvestigation(request)
getInvestigation(investigationId, signal)
attachEvidence(investigationId, request)
resolveInvestigation(investigationId, request)
```

These are illustrative operation names, not a substitute for verifying exact endpoint paths and payloads against OpenAPI.

### 11.3 Generated types

- Generate API types from the verified backend OpenAPI document.
- Keep generated code in a clearly marked location.
- Do not manually edit generated output.
- Keep domain UI types separate only when they represent a deliberate presentation model.
- Do not silently redefine API enums or response fields.
- Generated types do not validate runtime responses; use runtime validation selectively where justified.

### 11.4 Error normalization

Normalize backend failures into a stable application error shape, retaining status, code, safe message, field errors, retry timing, and request ID where available.

Do not convert all failures into a generic “Something went wrong” message. Preserve distinctions that guide the user:

- Authentication required.
- Permission denied.
- Resource missing.
- State conflict.
- Validation failed.
- Upload too large.
- Rate limited.
- Service unavailable.
- Network failure.

## 12. Authentication and Session Architecture

Implemented in `src/features/auth/` and `src/lib/auth/` per `ADR-075` (in-memory Bearer token only):

```ts
interface AuthContextValue {
  readonly status: "initializing" | "authenticated" | "unauthenticated";
  readonly user: AuthUser | null;
  readonly sessionNotice: SessionNotice | null;
  readonly preserveRedirectOnUnauthenticated: boolean;
  readonly signIn: (credentials: LoginRequest) => Promise<AuthUser>;
  readonly signOut: () => void;
  readonly clearSessionNotice: () => void;
}
```

Key implemented behaviors:

- Access token lives strictly in `token-store.ts` module memory alongside monotonic `sessionEpoch` (never persisted to `localStorage`, `sessionStorage`, cookies, query keys, props, or URLs; page reloads require re-authentication).
- `signIn()` executes the 8-step guarded sequence combining `authAttemptId` (`authAttemptRef` + `AbortController`) and post-`setAccessToken` `sessionEpoch` checks before committing `GET /api/v1/auth/me` (`parseAuthUser` runtime validation) into authenticated state.
- `TokenResponse.expires_in` schedules epoch-checked expiration timeout cleanup.
- Single-flight `401` handling via `session-events.ts` (`notifyUnauthorized(requestEpoch)`) clears token, auth state, timers, cancels queries (`void queryClient.cancelQueries()`), and clears cache synchronously (`queryClient.clear()`); `403` responses preserve the authenticated session.
- `signOut()` executes **local-only logout (Option B)**: synchronous local token/state/timer/cache cleanup without calling `/auth/logout` and without claiming server-side JWT revocation.

## 13. Critical Workflow Data Flows

### 13.1 Sign-in

```text
Login Page
    |
    v
Auth Feature
    |
    v
Central API Client
    |
    v
POST /auth/login
    |
    v
Approved Session Adapter
    |
    v
GET /auth/me
    |
    v
Current User Context
    |
    v
Protected Application Shell
```

Token/session handling between login and subsequent requests is deliberately abstracted until the security decision is approved.

### 13.2 Transaction exploration

```text
Transaction Page
    |
    v
Filter / Pagination State (URL)
    |
    v
Transaction Query Hook
    |
    v
Transaction API Function
    |
    v
API Client
    |
    v
GET /transactions
    |
    v
Query Cache
    |
    v
Transaction Table
    |
    v
Transaction Detail Route
```

The browser presents server pagination and filtering. It does not fetch every transaction and filter locally.

### 13.3 Analytics

```text
Analytics Filters
    |
    v
Analytics Query Hook
    |
    v
Analytics API
    |
    v
Backend Aggregation
    |
    v
Typed Analytics Response
    |
    +------> Metric Components
    |
    +------> ECharts Components
    |
    +------> Accessible Data Table
```

The chart layer maps API response values into visualization series only. It does not calculate the underlying financial aggregates.

### 13.4 Dataset import

```text
File Selection
    |
    v
Client Convenience Checks
    |
    v
Multipart Upload Mutation
    |
    v
POST /datasets/imports
    |
    v
Backend Validation / Deduplication / Ingestion
    |
    v
Import Response
    |
    +------> Import Summary
    |
    +------> Import Detail / Errors
    |
    +------> Recovery Action (if supported)
```

Do not display a successful import until the backend returns the corresponding success state.

### 13.5 Risk analysis

```text
Transaction Detail
    |
    v
Permission / Model-Lifecycle Presentation Check
    |
    v
User Requests Analysis
    |
    v
Risk Mutation
    |
    v
Backend Model + Rule Engine
    |
    v
Persisted Risk Response
    |
    v
Risk Result + Factors
```

The frontend does not calculate or approximate the score. The backend decides whether the user's role and selected model lifecycle permit the request.

### 13.6 Investigation workspace

```text
Investigation Route
    |
    v
Investigation Workspace Query
    |
    +------> Case Metadata / Assignment / Status
    |
    +------> Primary Transaction
    |
    +------> Risk Assessment
    |
    +------> Related Transactions
    |
    +------> Evidence
    |
    +------> AI Summary State / History
    |
    v
Role + Assignment-Aware Actions
    |
    +------> Assignment / Status Mutations
    +------> Related Transaction Mutation
    +------> Evidence Attachment
    +------> AI Summary Generation
    +------> Human Resolution
```

Whether the workspace is returned by one aggregate endpoint or multiple endpoints must follow the actual API. The frontend should not assume an aggregate response that the backend does not provide.

### 13.7 AI summary generation

```text
Authorized User Action
    |
    v
AI Summary Mutation
    |
    v
Backend Generation Lifecycle
    |
    +------> PENDING
    +------> COMPLETED
    +------> FAILED
    |
    v
Summary Query / History
    |
    v
Structured Sections
    ├── Executive Summary
    ├── Observed Facts
    ├── Derived Signals
    ├── Potential Interpretations
    └── Uncertainties and Limitations
```

The frontend displays the backend's actual lifecycle and staleness information. It must not invent polling states or assume a synchronous response. Polling/refetch intervals should be based on the verified API behavior.

## 14. Domain Integrity Rules in the UI

### 14.1 Financial authority

The frontend may format and display monetary values, but must not become the source of financial truth.

- Keep decimal strings intact.
- Do not use binary floating-point arithmetic for financial calculations.
- Do not derive account balances from the visible transaction page.
- Do not aggregate currencies without explicit backend semantics.
- Do not replace absent values with zero.

### 14.2 Risk authority

- Risk score and level are server outputs.
- The frontend must not reproduce the rule engine or ML scoring.
- Risk is not a final fraud determination.
- Missing, stale, and failed analysis must not be represented as low risk.

### 14.3 Investigation authority

- Investigation status, assignment, and resolution are server-owned.
- Frontend transitions are commands to the backend, not local state changes.
- Resolved investigations are terminal and read-only.
- Concurrency conflicts require authoritative refresh.

### 14.4 Evidence authority

- Evidence is append-only and immutable.
- Frontend has no evidence edit/delete workflow.
- Evidence references and payloads are displayed as returned and permitted by the API.
- The frontend must not imply that a stored snapshot automatically tracks future changes in its source entity.

### 14.5 AI authority

- AI output is advisory.
- Observed facts, derived signals, interpretations, and uncertainty must remain separate.
- The frontend must not allow AI output to resolve a case automatically.
- The backend owns grounding validation and stale-summary detection.

## 15. Shared Component Architecture

Shared components should represent reusable presentation patterns, not domain workflows.

### 15.1 UI primitives

Examples:

- Button
- Input
- Select
- Dialog
- Dropdown
- Tabs
- Tooltip
- Badge
- Card
- Skeleton

### 15.2 Data-display components

Examples:

- DataTable
- Pagination
- MonetaryValue
- Timestamp
- StatusBadge
- RiskIndicator
- EmptyState
- KeyValueList
- ChartContainer

Domain-specific semantics should be passed explicitly through props. For example, `RiskIndicator` may display a supplied risk level; it must not compute one.

### 15.3 Feedback components

Examples:

- InlineFieldError
- PageError
- PermissionDenied
- LoadingState
- EmptyState
- ConflictNotice
- Toast/notification

### 15.4 Avoid over-generalization

Do not build a universal table or form framework before multiple real screens demonstrate the same stable requirement. Prefer a simple reusable component with clear props over a configuration engine.

## 16. Error Boundaries and Recovery

Use a root error boundary for unexpected rendering failures and narrower boundaries only where a complex feature can fail independently.

Expected API failures should be handled in query/mutation state, not thrown into the root error boundary.

Recovery behavior:

- Query failure: show retry where safe.
- Mutation failure: preserve form state when possible and show actionable feedback.
- `401`: transition through the approved session-expiration flow.
- `403`: show permission-denied state.
- `404`: show missing-resource state.
- `409`: refetch authoritative state and explain the conflict.
- `413`: explain upload size restriction.
- `422`: map field errors where possible.
- `429`: respect `Retry-After`.
- `5xx` / network: distinguish service failure from empty data.

A failed subpanel should not erase successfully loaded panels unless the product workflow requires an all-or-nothing view.

## 17. Security Architecture Constraints

Detailed controls belong in `FRONTEND_SECURITY.md`. The architecture must preserve these boundaries:

- API communication uses HTTPS outside local development.
- No secrets in frontend source, build output, or `VITE_` environment variables.
- No raw HTML injection of user-provided notes/evidence.
- No sensitive tokens or private evidence in URLs.
- No client-side authorization as a security boundary.
- No direct database access.
- Session/query cache is cleared appropriately when identity changes.
- No production session-replay or analytics tool without security/privacy approval.
- CORS is configured by the backend; it is not a frontend bypass mechanism.

## 18. Testing Architecture

Testing should follow the same boundaries as the application.

| Layer | What to test | Suggested tools |
|---|---|---|
| Pure utilities | Formatting, query keys, permission presentation helpers, error mapping | Vitest |
| Shared components | Accessible behavior, validation display, status rendering | Testing Library |
| Feature components/hooks | Query/mutation behavior, loading/error/empty states | Testing Library, MSW |
| API integration | Request method/path/body/headers and response handling | MSW |
| Route integration | Authenticated routes, role-aware navigation, not-found behavior | Testing Library |
| End-to-end | Core user workflows against a test backend | Playwright |
| Accessibility | Keyboard/focus/semantic checks | Testing Library, axe integration, Playwright |

Test behavior at boundaries. Avoid coupling tests to internal component state or implementation details.

## 19. Performance Architecture

- Use server pagination and filtering for large data.
- Keep query cache bounded through appropriate stale times and garbage-collection settings.
- Lazy-load route bundles and chart modules where beneficial.
- Avoid rendering unbounded table rows.
- Avoid unnecessary global rerenders.
- Keep chart input bounded by API-supported windows and aggregations.
- Cancel obsolete requests where practical.
- Establish numerical budgets from a measured production build and representative data.

Do not add virtualization, a global state library, or complex caching layers until profiling demonstrates a need.

## 20. Architecture Decisions and Open Questions

The following must be resolved in the relevant documents or ADRs:

1. **Authentication session mechanism:** implement the accepted in-memory token strategy and logout/session behavior defined by ADR-075 in `DECISIONS.md` and `FRONTEND_SECURITY.md`.
2. **State/query library:** ratify TanStack Query or document a simpler alternative.
3. **Routing library:** ratify React Router or document the chosen routing approach.
4. **API type generation:** verify OpenAPI completeness and choose generation/CI workflow.
5. **Workspace response shape:** confirm whether investigation details are aggregated or require multiple API calls.
6. **AI summary lifecycle:** confirm status polling/refetch contract, stale behavior, and history response.
7. **Default landing page:** choose Dashboard or Investigation Queue per role, or one shared default.
8. **Feature contract readiness:** confirm account detail, user management, and audit read APIs before adding those features.
9. **Repository boundary:** decide whether frontend lives in `frontend/` within the existing repository or a separate repository.

### 20.1 Important architecture guardrail

Do not design the frontend around imagined endpoints or a hypothetical “ideal” backend response. The actual OpenAPI schema and implemented API behavior take precedence. If the current API requires several requests to assemble a workspace, the frontend can compose those responses; do not silently assume an aggregate endpoint.

## 21. Relationship to Other Documents

| Document | Responsibility |
|---|---|
| `FRONTEND_PRD.md` | Product goals, users, workflows, screens, requirements, acceptance criteria |
| `FRONTEND_TRD.md` | Frontend stack, tooling, runtime, build, and technical constraints |
| `FRONTEND_DESIGN.md` | Visual language and interaction presentation |
| `FRONTEND_API_INTEGRATION.md` | Exact endpoint integration and request/response behavior |
| `FRONTEND_SECURITY.md` | Token/session policy and browser security |
| `FRONTEND_TESTING_STRATEGY.md` | Detailed frontend test plan |
| `FRONTEND_ROADMAP.md` | Implementation phases and release gates |
| `ARCHITECTURE.md` | System-level and backend architecture |
| `API_GUIDELINES.md` | Backend REST API contract |
| `SECURITY.md` | Platform security policy |
| `DECISIONS.md` | Accepted architecture and technology decisions |

## 22. Definition of Done

This architecture is ready to guide implementation when:

- Feature boundaries and dependency direction are reviewed.
- Server, UI, and URL state ownership are agreed.
- Routing and auth/session integration align with the approved security decision.
- API integration follows the verified OpenAPI contract.
- Backend contract gaps affecting MVP are resolved or explicitly excluded.
- No frontend responsibility duplicates backend financial or investigative authority.
- The architecture is reflected in the actual repository structure and reviewed as implementation evolves.

## 23. Final Architecture Principle

FinSignal's frontend should be modular enough to evolve, but not more complex than its workflows require.

**The frontend coordinates user interaction and presents backend-authoritative intelligence. It must never become a parallel source of financial truth, risk decisions, evidence integrity, or investigation state.**
