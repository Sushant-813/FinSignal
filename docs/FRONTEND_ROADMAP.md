# FinSignal — Frontend Implementation Roadmap

**Document:** `FRONTEND_ROADMAP.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.2  
**Status:** Phase F0 & F1 Accepted; Phases F2 & F3 Implemented & Locally Verified (Remote CI & Live-Backend E2E Pending; Formal Acceptance Pending)
**Scope:** Frontend planning and implementation following Backend + ML v1.0.0

---

## 1. Purpose

This document defines the implementation sequence for the FinSignal frontend. It converts the approved frontend product scope, technical requirements, architecture, API integration, security, and testing strategy into incremental phases with deliverables and exit criteria.

The backend and ML platform is treated as the existing system of record. This roadmap does not reopen completed backend phases or authorize frontend-side financial calculations.

## 2. Starting Point and Scope

### 2.1 Existing platform

The Backend + ML v1.0.0 scope is recorded as completed and released in the master project documentation. The frontend is the next major development track.

The frontend is a separate React application that consumes the FastAPI REST API under `/api/v1`.

### 2.2 Frontend MVP scope

The first usable frontend release includes:

- Authentication and current-user context.
- Application shell and role-aware navigation.
- Dashboard and analytics overview.
- Transaction list, supported filters, and detail.
- Risk result viewing and authorized on-demand analysis.
- Dataset CSV import and import-result presentation.
- Investigation queue and manual case creation.
- Investigation workspace and supported assignment/status actions.
- Related transaction association.
- Evidence list and append-only evidence attachment.
- AI summary generation, view, and history.
- Human resolution and terminal resolved-case view.
- Core loading, empty, error, conflict, and authorization states.
- Responsive behavior and accessibility for core workflows.

The following are not MVP release blockers unless separately prioritized:

- Dedicated user-management screen, pending a confirmed API contract.
- Dedicated audit-history screen, pending a confirmed read API.
- Rich account behavior drill-down, pending stable endpoint/response contracts.
- Advanced merchant/device/location detail pages where contracts are incomplete.
- Export workflows unless backend API and security policy are documented.
- Real-time alerts, streaming, graph visualization, and autonomous workflows.

The product scope in `FRONTEND_PRD.md` is authoritative for MVP inclusion. This roadmap sequences that scope; it does not silently expand it.

## 3. Roadmap Principles

1. Verify the backend contract before building against it.
2. Resolve security and architectural decisions before scaffolding dependent behavior.
3. Deliver a usable vertical slice in every phase.
4. Keep backend financial and domain authority intact.
5. Build shared foundations before feature-specific abstractions.
6. Implement high-value core workflows before optional detail screens.
7. Treat AI as advisory and evidence-grounded.
8. Keep evidence append-only and investigation decisions human-owned.
9. Test failure states and authorization boundaries alongside happy paths.
10. Avoid adding dependencies or infrastructure without a concrete need.
11. Keep the repository buildable and testable after each phase.
12. Do not set calendar estimates until the scope and implementation capacity are known.

## 4. Dependencies and Entry Criteria

Frontend implementation should not begin until the following minimum prerequisites are reviewed:

| Prerequisite | Required outcome |
|---|---|
| `FRONTEND_PRD.md` | MVP workflows and acceptance criteria approved |
| `FRONTEND_DESIGN.md` | Visual direction and design tokens approved |
| `FRONTEND_TRD.md` | Core stack and proposed dependencies ratified |
| `FRONTEND_ARCHITECTURE.md` | Application boundaries and module structure approved |
| `FRONTEND_API_INTEGRATION.md` | MVP endpoint contracts verified against running OpenAPI |
| `FRONTEND_SECURITY.md` | Authentication/session and security decisions approved |
| `FRONTEND_TESTING_STRATEGY.md` | Test layers and CI gates agreed |
| Backend environment | Stable development/staging API and synthetic test accounts available |

### 4.1 Contract verification gate

Before implementing an endpoint-dependent feature:

1. Start the backend in the documented environment.
2. inspect `/openapi.json`.
3. Verify method, path, request/response schemas, query parameters, status codes, and security declarations.
4. Compare the runtime contract with `API_GUIDELINES.md`.
5. Reconcile discrepancies or explicitly defer the feature.
6. Generate or update frontend API types from the verified schema.

No frontend phase should invent missing backend endpoints or payload fields.

## 5. High-Level Frontend Roadmap

```text
F0 — Decisions, Contract Verification & Repository Readiness
  ↓
F1 — Application Foundation & Design System
  ↓
F2 — Authentication, Session & Application Shell
  ↓
F3 — Analytics, Transaction Exploration & Risk
  ↓
F4 — Dataset Import & Processing Visibility
  ↓
F5 — Investigation Queue, Workspace & Lifecycle
  ↓
F6 — Evidence & AI-Assisted Investigation
  ↓
F7 — Integration, Accessibility, Security & Hardening
  ↓
F8 — Deployment, Acceptance & Frontend Release
```

The phases are dependency-oriented, not calendar commitments. Some isolated tasks may proceed in parallel after their dependencies are satisfied, but phase exit criteria must remain explicit.

---

## 6. F0 — Decisions, Contract Verification & Repository Readiness

> [!NOTE]
> **Phase Status: COMPLETED (2026-11-10)**

### Objective

Remove the major unknowns that could force expensive rework during implementation. Coordinate and verify backend read API readiness (`BACKEND_API_READINESS.md`), ratify frontend architectural decisions, and prepare the repository foundation.

### Completed tasks

- [x] ADR governance: ADR-074, ADR-075, ADR-076, and ADR-077 are all `ACCEPTED` in `DECISIONS.md`. ADR-075 selects in-memory Bearer-token storage for the MVP.
- [x] Backend API readiness implementation and tests for read endpoints per `docs/BACKEND_API_READINESS.md`:
  - `GET /api/v1/transactions`
  - `GET /api/v1/transactions/{transaction_id}`
  - `GET /api/v1/datasets/imports`
  - Relocated shared `MoneyStr` types into `src/finsignal/common/types.py` with backward-compatible re-exports in `src/finsignal/analytics/schemas.py`.
- [x] Verified running FastAPI OpenAPI routes and schemas (`28` paths, `67` component schemas exported to `frontend/openapi.json`).
- [x] Executed build-time TypeScript type generation via `openapi-typescript` into `frontend/src/api/generated/schema.ts` and added `npm run check:types-drift` (`frontend/scripts/check-types-drift.mjs`, ADR-076).
- [x] Confirmed package manager (`npm`), `frontend/package-lock.json`, and Node.js `>=20.0.0` policy (`frontend/.nvmrc`).
- [x] Confirmed backend CORS defaults (`http://localhost:3000`, `http://localhost:5173`) and Vite `/api` development proxy (`frontend/vite.config.ts`).
- [x] Reconciled RBAC (`UNAUTHORIZED` 401 / `FORBIDDEN` 403) and documented opt-in `source_namespace` fencing on `GET /api/v1/transactions/{transaction_id}`.
- [x] Implemented in-memory access-token store (`frontend/src/lib/auth/token-store.ts`) and typed HTTP client (`frontend/src/lib/api/client.ts`, `frontend/src/lib/api/env.ts`).
- [x] Scaffolded `frontend/` workspace with strict TypeScript, ESLint, Prettier, Tailwind CSS, Vitest, and Playwright config.

### Deliverables

- Ratified frontend decisions in `DECISIONS.md` (ADR-074 through ADR-077 `ACCEPTED`).
- Backend API readiness endpoints implemented, tested (`593` backend tests passing), and verified against `frontend/openapi.json`.
- Generated TypeScript types (`frontend/src/api/generated/schema.ts`) and zero-drift check script (`npm run check:types-drift`).
- Scaffolded `frontend/` project with passing Vitest smoke tests (`4 passed`), ESLint, Prettier, TypeScript build, and Vite production build.
- Reconciled API, integration, roadmap, and project log documentation.

### Exit criteria (Met)

- [x] Backend API readiness endpoints (`/transactions`, `/transactions/{transaction_id}`, `/datasets/imports`) return HTTP 200 with verified Pydantic schemas.
- [x] No unresolved security decision blocks authentication implementation (`ADR-075` `ACCEPTED`; opt-in `source_namespace` detail behavior explicitly documented).
- [x] All MVP endpoint contracts verified in `frontend/openapi.json` with generated `schema.ts` committed and drift-checked.
- [x] Frontend builds cleanly, passes lint/format/typecheck, and runs unit tests without error.
- [x] Core dependency choices are approved and locked via `frontend/package-lock.json`.

---

## 7. F1 — Application Foundation & Design System

> [!NOTE]
> **Phase Status: COMPLETED & FORMALLY ACCEPTED (2026-11-11)** — Baseline pushed to `origin/main` (`ad02a4e`), remote GitHub Actions CI run `43036181121` passed both backend and frontend jobs, `ADR-080` was approved by the project owner, and formal Phase F1 acceptance was granted. (`F1-AUD-005` and `F1-AUD-006` were subsequently resolved in Phase F2; `F1-AUD-009` remains deferred.)

### Objective

Create a reproducible frontend project with a stable application foundation and shared visual primitives.

### Key tasks

- [x] Preserve React 19, TypeScript 5.8 (`^5.8.3`, locked `5.9.3`), Vite 6 (`6.4.6`), and Tailwind CSS 4 (`4.3.5`) foundation.
- [x] Maintain strict TypeScript configuration (`strict`, `noImplicitOverride`, `noFallthroughCasesInSwitch`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, zero `any`).
- [x] Establish feature-oriented / application structure (`src/app/{providers,router,errors}`, `src/components/ui/`, `src/lib/{api,auth,utils}`, `src/styles/`) and minimal `/` + `*` routing foundation (`AppProviders`, `QueryProvider`, `FoundationPage`).
- [x] Implement global design tokens (`--fs-*` mapped cleanly to `@theme inline` without circular references) and base accessibility/motion rules (`:focus-visible`, `.tabular-nums`, `prefers-reduced-motion`).
- [x] Implement 10 domain-agnostic foundational UI components in `src/components/ui/`: `Button`, `Badge`, `Card`, `Input`, `Select`, `Table`, `Dialog`, `Alert`, `Skeleton`/`TableSkeleton`, and `EmptyState`.
- [x] Establish accessible component patterns, `RootErrorBoundary` (non-leaky fallback), and `NotFoundPage` route.
- [x] Configure Vitest (`5.1.0`), React Testing Library, `user-event`, and MSW (`2.15.0`, `onUnhandledRequest: "error"`) test infrastructure plus shared API error fixtures.
- [x] Add frontend CI workflow job in `.github/workflows/ci.yml` (`npm ci`, `format:check`, `lint`, `typecheck`, `test`, `build`, `check:types-drift`).
- [x] **Audit Remediation Completed (2026-11-11):**
  - **Prettier (`F1-AUD-001`):** Formatted 17 affected F1 files; `npm run format:check` passes cleanly.
  - **CSS Cascade Remediation (`F1-AUD-003`):** Made state utilities mutually exclusive in `Input` (`text-text-disabled` vs `text-text-primary`) and added `Skeleton` `"text-sm"` (`h-3.5`) for `TableSkeleton` header cells to eliminate `.h-4` override.
  - **Dependency Upgrades & Alignment (`F1-AUD-002`):** Upgraded `zod` (`3.25.76` → `4.6.7`, `ADR-078`) and `vitest` (`3.2.7` → `5.1.0`, `ADR-079`), aligned `frontend/.nvmrc` to `24`, `engines.node` to `^22.12.0 || >=24.0.0`, and `vite` floor to `^6.4.0`.
  - **AbortSignal Test-Environment Remediation (`F1-AUD-004`):** Upgraded `PatchedRequest` in `tests/setup.ts` to bridge un-aborted cross-realm `AbortSignal` instances to a native `AbortController` with `{ once: true }` listener cleanup.
  - **Button `asChild` Hardening (`F1-AUD-008`):** Explicitly stripped `disabled` and `isLoading` before spreading props onto Radix `<Slot>` in non-dev builds.
  - **Regression Tests & Targeted Browser Verification:** Added unit/component regression suites (`zod-rhf.test.tsx`, `api-client.test.ts` in-flight abort, `input.test.tsx`, `skeleton.test.tsx`, `button.test.tsx`) and verified rendered/computed CSS, responsive viewports (`1440`/`1024`/`768`/`360`), and `Dialog` portal/focus trap using system Chrome.

### Deliverables

- Running frontend foundation (`FoundationPage`), `NotFoundPage`, and `RootErrorBoundary` (`AppProviders`, `QueryProvider`, `createAppRouter`).
- Centralized design tokens (`frontend/src/styles/tokens.css`) and 10 shared UI primitives (`frontend/src/components/ui/index.ts`).
- CI baseline in `.github/workflows/ci.yml`.
- Component, unit, MSW, and Zod 4 + React Hook Form integration tests (`15` files, `47` passing tests).

### Verification Summary (2026-11-11 Post-Remediation)

| Verification | Result |
|---|---|
| Prettier (`npm run format:check`) | **PASS** |
| ESLint (`npm run lint`) | **PASS** |
| TypeScript (`npm run typecheck`) | **PASS** |
| Vitest (`npm run test`, v5.1.0) | **47/47 PASS** (`15` test files) |
| Production build (`npm run build`) | **PASS** (`vite v6.4.6`) |
| OpenAPI drift check (`npm run check:types-drift`) | **PASS** |
| Production dependency audit (`npm audit --omit=dev`) | **0 vulnerabilities** |
| Full dependency audit (`npm audit`) | **7 moderate advisories remain** (`typescript-eslint@8.72.2` → `minimatch@10.2.6`, `GHSA-g3hv-75wg-m249`; dev-only) |
| Browser verification (system Chrome + Vite preview / built CSS harness) | **PASS** (ad-hoc Chrome harness; not a committed Playwright E2E suite) |
| Remote GitHub Actions (`.github/workflows/ci.yml`) | **PASS** (run `43036181121` on `ad02a4e`: backend & frontend jobs succeeded) |

### Explicitly Deferred Findings from Phase F1 Audit

| Finding | Description | Disposition |
|---|---|---|
| `F1-AUD-005` | API client and base URL edge-case hardening (`fetch` network `TypeError` normalization, non-JSON `2xx` guard, `/api/v1` dedup, scheme validation) | **Resolved in Phase F2 (`F2.1`)** |
| `F1-AUD-006` | Committed Playwright E2E suite (`frontend/tests/e2e/`) and `playwright.config.ts` `webServer` configuration | **Resolved in Phase F2 (`F2.6`)** |
| `F1-AUD-009` | `Button` `size="icon"` loading layout and `Alert` `data-*`/attribute passthrough ergonomics | **Deferred** (future UI refinement) |

### Exit criteria & Acceptance Resolution (Met)

- [x] Clean install compatibility, strict TypeScript, lint, formatting, build, and `47/47` automated tests pass locally.
- [x] Shared components conform to design tokens, CSS computed-style checks, and accessibility requirements.
- [x] No backend credentials, secrets, or browser-storage token persistence exist in frontend code (`npm audit --omit=dev` = `0` vulnerabilities).
- [x] **Owner security-exception approval (`ADR-080`):** Accepted by project owner on `2026-11-11` for the 7 moderate dev-only advisories (`typescript-eslint@8.72.2` → `minimatch@10.2.6`, `GHSA-g3hv-75wg-m249`).
- [x] **Remote CI verification:** Remote GitHub Actions CI run `43036181121` (`ad02a4e`) passed both backend and frontend jobs (`ubuntu-latest`, Node `24` via `.nvmrc`).

---

## 8. F2 — Authentication, Session & Application Shell

> [!IMPORTANT]
> **Phase Status: IMPLEMENTED & LOCALLY VERIFIED (2026-11-11)** — Milestones `F2.1` through `F2.6` are implemented and verified locally (`87/87` Vitest tests across `22` files; `5/5` mocked Playwright Chromium E2E tests against fresh production `vite preview`; `format:check`, `lint`, `typecheck`, `build`, `check:types-drift`, `npm audit --omit=dev` = `0` vulns). **Formal Phase F2 acceptance remains pending:** remote GitHub Actions CI for F2 commits has not yet been triggered, and live-backend E2E (`E2E_API_MODE=live`) has not been executed.

### Objective

Deliver a secure sign-in experience and the common application frame.

### Key tasks (`F2.1`–`F2.6` Implemented)

- [x] Harden centralized API client (`src/lib/api/{client,env,errors}.ts`, `F1-AUD-005` resolved), base URL scheme/query/fragment/HTTPS checks, `/api/v1` dedup, network & non-JSON `2xx` normalization, `429` `details.retry_after_seconds` fallback, explicit `authMode`, and `401` session-event bridge.
- [x] Implement OpenAPI-typed auth API functions (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` in `src/features/auth/api/auth-api.ts`).
- [x] Implement ADR-075 in-memory token store with `sessionEpoch` (`token-store.ts`), `AuthProvider` (`authAttemptId` + `sessionEpoch` race protection, 8-step login -> `/auth/me`, `expires_in` timer, single-flight `401` handling, `403` preservation), local-only logout (`Option B`), and `QueryClient` cancellation + synchronous cache clearing.
- [x] Add protected & public-only routing (`ProtectedRoute`, `PublicOnlyRoute`, `RoleGate`, `SessionLoadingView`, `sanitizeRedirectPath`) cleanly avoiding stale `?redirect=` after manual `signOut`.
- [x] Add runtime role validation (`isUserRole`, `parseAuthUser` fail-closed) and F2 capability helpers separating read-only dataset import history (`canViewDatasetImports`, all 3 roles) from dataset upload/recovery management (`canManageDatasets`, `ADMIN | ANALYST` only).
- [x] Implement application shell (`AuthLayout`, `AppLayout`, `Sidebar`, `TopBar`, `UserMenu`, `nav-config.ts`), authenticated `WorkspaceHomePage` at `/`, and honest F3–F5 `PhasePlaceholderPage` routes (omitting uncontracted `Accounts`, `Audit`, `Admin Users` and avoiding fabricated metrics).
- [x] Implement accessible React Hook Form + Zod 4 `LoginPage` (`1..128` password matching `LoginRequest`, no registration link).
- [x] Add Vitest + MSW unit/integration suites (`87/87` tests across `22` files) and Playwright Chromium E2E (`F1-AUD-006` resolved: fresh-build `vite preview` server with `reuseExistingServer: false`, `5/5` mocked E2E passing).

### Deliverables

- Login page (`LoginPage.tsx`, `login-schema.ts`).
- Authenticated application shell (`AppLayout`, `AuthLayout`, `Sidebar`, `TopBar`, `UserMenu`, `WorkspaceHomePage`, `PhasePlaceholderPage`).
- Current-user & session lifecycle provider (`AuthProvider`, `AuthContext`, `useAuth`, `auth.types.ts`).
- Protected & role-aware routing (`routes.tsx`, `ProtectedRoute`, `PublicOnlyRoute`, `RoleGate`, `redirect.ts`).
- Hardened API client, normalized error helpers, and F2 capability matrix (`client.ts`, `env.ts`, `errors.ts`, `session-events.ts`, `capabilities.ts`).
- Vitest/MSW test suites and Playwright E2E suite (`tests/e2e/{auth,shell}.spec.ts`).

### Exit criteria & Verification Status

- [x] Valid users authenticate via `/auth/login` and establish identity/role context via `/auth/me` (`87/87` Vitest + `5/5` mocked Chromium E2E).
- [x] Invalid/expired sessions cannot render protected content; full page reload clears in-memory state cleanly (`ADR-075`).
- [x] `401` (clears session/cache) and `403` (preserves session) are handled distinctly.
- [x] Local-only logout (`Option B`) clears in-memory token and `QueryClient` cache synchronously without claiming server-side JWT revocation.
- [x] `ADMIN`, `ANALYST`, and `INVESTIGATOR` navigation and dataset read-only vs management visibility match verified permissions and fail closed on unknown roles.
- [ ] **Remote CI execution:** Trigger and observe green remote GitHub Actions CI for F2 changes.
- [ ] **Live-backend verification:** Execute optional `E2E_API_MODE=live` or manual live-stack verification against FastAPI + PostgreSQL (`CORSMiddleware` / `X-Request-ID` / `429` / real Argon2id + HS256 JWT).
- [ ] **Formal Phase F2 owner acceptance:** Grant sign-off after outstanding CI / live verification items are reviewed.

---

## 9. F3 — Analytics, Transaction Exploration & Risk

> [!IMPORTANT]
> **Phase Status: IMPLEMENTED & LOCALLY VERIFIED (2026-11-12)** — Phase F3 milestones are implemented and verified locally (`121/121` Vitest tests across `36` files; `7/7` mocked Playwright Chromium E2E tests against fresh production `vite preview`; `format:check`, `lint`, `typecheck`, `build`, `check:types-drift`, `npm audit --omit=dev` = `0` vulns). **Formal Phase F3 acceptance remains pending:** remote GitHub Actions CI execution and live-backend E2E testing (`E2E_API_MODE=live`) against running FastAPI + PostgreSQL backend remain pending.

### Objective

Deliver the operational dashboard overview, financial analytics visualizations, transaction exploration table, transaction detail, and hybrid risk scoring with on-demand evaluation.

### Implemented Subphases & Key Tasks (Completed 2026-11-12)

- [x] **F3.1 Foundation & Shared Utilities:**
  - Implemented string-safe decimal formatters (`formatMoney`, `formatMoneyParts`) and `MoneyValue` component (`frontend/src/components/data-display/MoneyValue.tsx`) guaranteeing zero IEEE 754 precision loss.
  - Implemented timezone-aware datetime utilities (`formatUtcDateTime`, `formatUtcDate`, `toUtcIsoString`) and `TimestampDisplay` component with native title tooltip.
  - Implemented shared domain-agnostic `Pagination` component (`frontend/src/components/ui/Pagination.tsx`) supporting page selection, bounds checking, and accessible ARIA attributes.
  - Centralized TanStack Query keys (`frontend/src/lib/api/query-keys.ts`) for `analytics`, `transactions`, and `risk`.
- [x] **F3.2 Dashboard Overview (`/`):**
  - Replaced temporary landing placeholder with `DashboardPage` integrating `GET /api/v1/analytics/overview`.
  - Implemented `OverviewKpiGrid` rendering total transaction count, debit/credit transaction breakdown, total debit/credit volumes, and continuous median debit/credit amounts.
  - Implemented `ReportingScopeBar` providing client-side namespace filtering (default `"SYNTHETIC"`), currency indicator, and date range scoping (`[from_time, to_time)`).
- [x] **F3.3 Financial Analytics (`/analytics`):**
  - Implemented `AnalyticsPage` with tabbed view navigation (Volume Trends, Category Spending, Top Merchants).
  - Integrated `GET /api/v1/analytics/trends`, `GET /api/v1/analytics/categories`, and `GET /api/v1/analytics/merchants`.
  - Built `TrendsChartPanel` with dynamic `React.lazy` Apache ECharts import, rendering dual-axis debit/credit bar and line charts.
  - Built `CategoryDistributionPanel` with pie chart visualization and accessible tabular distribution breakdown.
  - Built `MerchantAnalyticsPanel` displaying top merchants ranked by debit volume or frequency with dual percentage calculations (percentage of total debit volume and percentage of merchant spend).
  - Enforced enterprise chart guidelines: restrained palette, HTML-escaped tooltip formatters, and `prefers-reduced-motion` handling.
- [x] **F3.4 Transaction Exploration (`/transactions`):**
  - Implemented `TransactionsListPage` with server-side pagination (`page_size=50`), column sorting (`occurred_at`, `amount`), and multi-field filtering.
  - Built `TransactionFiltersBar` supporting namespace, amount ranges (`min_amount`, `max_amount`), risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and time window bounds.
  - Synchronized filter and pagination state exclusively with URL search parameters (`useSearchParams`) following ADR-074.
- [x] **F3.5 Transaction Detail (`/transactions/:transactionId`):**
  - Implemented `TransactionDetailPage` consuming `GET /api/v1/transactions/{id}`.
  - Built `TransactionFactsCard` rendering immutable transaction facts (exact `MoneyStr` amounts, UTC timestamps, account external references, execution metadata).
  - Built `TransactionRelationsCard` displaying counterparty account and contextual references.
- [x] **F3.6 Risk Scoring & Explainability:**
  - Implemented `RiskAnalysisPanel` consuming `GET /api/v1/transactions/{id}/risk`.
  - Distinctly mapped HTTP 404 responses to an explicit `"not_analyzed"` state, ensuring unanalyzed transactions are never presented as low or zero risk.
  - Rendered hybrid risk score ([0.00, 100.00]), categorical risk badges (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), ML vs Rule score breakdown, and structured `RiskFactorList`.
  - Implemented on-demand risk analysis action (`POST /api/v1/transactions/{id}/risk/analyze`) using default `ACTIVE` model, protected by fail-closed `canAnalyzeActiveRisk` capability gate.
- [x] **F3.7 Testing & Verification:**
  - Added unit, component, and MSW integration test suites across all new modules (`36` test files, `121/121` passing).
  - Added dedicated Playwright Chromium E2E specs (`tests/e2e/analytics.spec.ts`, `tests/e2e/transactions.spec.ts`, `7/7` passing against fresh production build).

### Deliverables

- Dashboard Overview (`frontend/src/features/dashboard/`).
- Financial Analytics with dynamically loaded ECharts (`frontend/src/features/analytics/`).
- Transaction Exploration & Filtering (`frontend/src/features/transactions/pages/TransactionsListPage.tsx`).
- Transaction Detail & Facts Card (`frontend/src/features/transactions/pages/TransactionDetailPage.tsx`).
- Risk Scoring, Factor List & On-Demand Analysis Action (`frontend/src/features/risk/`).
- Shared `Pagination`, `MoneyValue`, `TimestampDisplay`, and `RiskBadge` components.
- Centralized query keys (`src/lib/api/query-keys.ts`).

### Exit Criteria & Verification Status

- [x] Dashboard and analytics values match backend responses with zero browser recalculation.
- [x] Transaction filters, sort, and pagination strictly adhere to OpenAPI contract.
- [x] Missing risk analysis is distinctly rendered as "Not Analyzed", never as low risk or zero risk.
- [x] Hybrid risk score is clearly presented as an investigation prioritization signal, not a fraud verdict.
- [x] Exact string-safe decimal rendering (`MoneyStr`) prevents floating-point corruption.
- [x] Core analytics, transaction, and risk tests pass (`121/121` Vitest + `7/7` mocked Playwright E2E).
- [ ] Remote CI execution for Phase F3 commits completed.
- [ ] Live-backend E2E verification (`E2E_API_MODE=live`) executed against running FastAPI + PostgreSQL backend.
- [ ] Formal Phase F3 owner acceptance granted.

---

## 10. F4 — Dataset Import & Processing Visibility

### Objective

Enable authorized users to import supported CSV datasets and understand backend processing outcomes.

### Key tasks

- Build dataset import form and file selection UX.
- Implement multipart upload using the exact backend contract.
- Validate file size client-side for user feedback.
- Display import ID, status, row counters, duplicate status, and timestamps.
- Build import detail and validation-error view.
- Handle `409 IMPORT_IN_PROGRESS`, `413`, `422`, and network failures.
- Implement recovery using the original file only if the verified contract supports it.
- Reconcile server import state after ambiguous upload timeouts.
- Restrict controls by approved role capabilities.

### Deliverables

- Dataset import screen.
- Import status/detail view.
- Validation error presentation.
- Recovery workflow if included in verified MVP contract.

### Exit criteria

- Admin and Analyst can upload supported files.
- Investigator cannot invoke import unless backend policy changes.
- Duplicate and in-progress outcomes are accurately distinguished.
- Backend validation errors are displayed safely.
- The frontend does not assume an import completed merely because the request timed out or the browser upload ended.
- Upload tests pass.

---

## 11. F5 — Investigation Queue, Workspace & Lifecycle

### Objective

Deliver the core human investigation workflow.

### Key tasks

- Build investigation queue with supported filters and pagination.
- Build manual investigation creation from a primary transaction.
- Build investigation workspace from verified response contracts.
- Display primary and related transaction context.
- Implement assignment and self-assignment actions allowed by the backend.
- Implement priority and status updates supported by the API.
- Implement related transaction linking within the documented one-hop rule.
- Implement human resolution with allowed outcomes and required notes.
- Render resolved investigations as terminal/read-only.
- Handle concurrent updates and `409` conflicts by refreshing authoritative state.

### Deliverables

- Investigation queue.
- Investigation creation flow.
- Investigation workspace.
- Assignment and lifecycle controls.
- Related transaction association.
- Resolution flow and resolved-case view.

### Exit criteria

- Authorized users can create investigations.
- New cases reflect backend-created state.
- Assignment behavior matches endpoint-level role and object rules.
- Related transaction behavior follows the backend predicate; frontend does not implement graph expansion.
- Only permitted users can resolve eligible cases.
- Resolved cases are read-only.
- Conflict and failure states are tested.

---

## 12. F6 — Evidence & AI-Assisted Investigation

### Objective

Complete evidence review and structured AI-assisted investigation support while preserving provenance and human decision authority.

### Key tasks

- Build paginated evidence list.
- Build evidence attachment form using verified request schemas.
- Enforce append-only UI behavior.
- Display evidence type, source, timestamp, and references returned by API.
- Build AI summary latest-view and history.
- Implement generation action for authorized roles.
- Implement the actual lifecycle behavior confirmed in F0 (synchronous response, status refresh, or documented polling).
- Display executive summary, observed facts, derived signals, potential interpretations, and uncertainties/limitations separately.
- Display stale, pending, and failed states as returned by the backend.
- Link evidence references only when resolvable through supported API.
- Preserve advisory labeling and do not convert AI content into case decisions.

### Deliverables

- Evidence list and attachment workflow.
- AI summary generation and display.
- AI summary history.
- Provenance-aware summary presentation.

### Exit criteria

- Evidence can be attached only by authorized users and cannot be edited/deleted in the UI.
- Payload and source constraints match the backend contract.
- AI summary sections remain semantically distinct.
- Stale/failed/pending states are accurately represented.
- AI output cannot change investigation status or resolution.
- AI and evidence tests pass.

---

## 13. F7 — Integration, Accessibility, Security & Hardening

### Objective

Validate the complete frontend as a coherent and secure application rather than a set of individually working pages.

### Key tasks

- Run full frontend test suite.
- Run contract verification against the target backend OpenAPI.
- Run role-specific E2E workflows.
- Test loading, empty, validation, network, authorization, conflict, and server-failure states.
- Review keyboard navigation, focus management, and screen-reader behavior.
- Run automated accessibility checks and remediate critical violations.
- Review responsive layouts at desktop, tablet, and mobile widths.
- Verify token handling, cache clearing, and sensitive-data logging rules.
- Verify safe rendering of user input, evidence, and AI output.
- Verify CORS, HTTPS, CSP, anti-framing, and other deployment headers in the target environment.
- Review dependency vulnerabilities and remove unnecessary dependencies.
- Profile transaction tables, charts, and large investigation histories.
- Conduct exploratory testing with each role.

### Deliverables

- Completed test evidence.
- Accessibility review.
- Security review checklist.
- Resolved high/critical defects.
- Release candidate build.

### Exit criteria

- Critical E2E journeys pass against a contract-faithful backend.
- No unresolved critical/high security or data-integrity defects.
- Core workflows meet the agreed accessibility target.
- Production build is reproducible.
- No sensitive data is exposed through logs, URLs, telemetry, or unapproved browser storage.
- Known limitations are documented and approved.

---

## 14. F8 — Deployment, Acceptance & Frontend Release

### Objective

Deploy the frontend to the selected hosting environment and complete the first frontend release.

### Key tasks

- Confirm frontend hosting and domain.
- Configure production API base URL.
- Configure backend CORS allowlist for the exact frontend origin.
- Configure HTTPS and security headers at the hosting/reverse-proxy layer.
- Configure environment-specific build settings.
- Verify no secrets are embedded in build artifacts.
- Deploy staging candidate.
- Run smoke tests against staging.
- Complete product acceptance criteria from `FRONTEND_PRD.md`.
- Review release notes and known limitations.
- Tag and publish the frontend release.
- Update README, master roadmap, project log, and architecture/document status.

### Deliverables

- Deployed frontend.
- Staging and production smoke-test results.
- Release notes.
- Updated project documentation.
- Frontend release tag/version.

### Exit criteria

- Frontend is accessible through the approved HTTPS origin.
- Backend CORS permits only approved origins.
- All required MVP acceptance criteria pass.
- No critical/high release-blocking defects remain.
- Deployment and rollback procedures are documented.
- Release artifacts and project status are updated.

---

## 15. Cross-Phase Quality Gates

Every phase must satisfy these baseline checks before it is considered complete:

| Gate | Requirement |
|---|---|
| Build | Production build succeeds |
| Type safety | TypeScript strict checks pass |
| Lint | ESLint and formatting checks pass |
| Tests | Relevant unit/component tests pass |
| API contract | No guessed or unverified request/response fields |
| Security | No secrets or unauthorized data exposure |
| Financial integrity | No browser-side authoritative calculations |
| UX states | Loading, empty, error, and relevant conflict states exist |
| Accessibility | Keyboard/focus/semantic checks for changed workflows |
| Documentation | Decisions, contracts, and known gaps are updated |

A phase is not complete solely because its primary page renders.

## 16. Release Acceptance Mapping

The final MVP release must satisfy the product acceptance criteria:

| PRD criterion | Primary roadmap phase |
|---|---|
| AC-001 Authentication and role context | F2 |
| AC-002 Dataset import | F4 |
| AC-003 Transaction exploration | F3 |
| AC-004 Analytics | F3 |
| AC-005 Risk analysis | F3 |
| AC-006 Investigation creation and queue | F5 |
| AC-007 Assignment and lifecycle | F5 |
| AC-008 Related transactions and evidence | F5, F6 |
| AC-009 AI summary | F6 |
| AC-010 Human resolution | F5 |
| AC-011 Failure handling | F2–F7 |
| AC-012 Accessibility and data integrity | F1–F8 |

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| API documentation differs from runtime | Rework and incorrect UI behavior | F0 contract verification; generated types; contract tests |
| Token/session decision delayed | Auth architecture rework | Resolve in F0 before F2 |
| Role matrix is inconsistent | Unauthorized or missing actions | Verify endpoint/object policy and centralize presentation capabilities |
| AI lifecycle is misunderstood | Broken loading/polling UX | Verify actual generation lifecycle before F6 |
| Frontend duplicates backend calculations | Financial inconsistency | Keep aggregates and risk scores server-authoritative |
| Large tables/charts degrade responsiveness | Poor investigation usability | Server pagination, profiling, selective lazy loading |
| MVP scope expands into optional detail pages | Delayed release | Keep explicit MVP boundary and defer unsupported screens |
| Third-party UI libraries overcomplicate design | Maintenance and visual inconsistency | Approve dependencies selectively; use shared design tokens |
| Sensitive data leaks through browser persistence/logging | Security and privacy impact | Apply `FRONTEND_SECURITY.md` and test it continuously |

## 18. Deferred Work After MVP

Potential future work, subject to product prioritization and backend contracts:

- Dedicated user administration.
- Dedicated audit-history exploration.
- Rich account behavior and unusual-spending drill-down.
- Merchant/device/location investigation detail.
- Export and reporting workflows.
- Saved filters and user preferences beyond basic UI preferences.
- Real-time alerts or streaming updates.
- Graph-based relationship exploration.
- Offline access or service-worker caching.
- Advanced case collaboration features.

These are not implicitly included in the MVP.

## 19. Project Documentation Updates

At the completion of F0:

- Record approved frontend ADRs in `DECISIONS.md`.
- Update `PROJECT_ROADMAP.md` to include the frontend track.
- Add frontend planning milestone to `PROJECT_LOG.md`.
- Update `TRD.md` to reference the frontend technical documents.

At the completion of F8:

- Update `README.md` with the released frontend capabilities and run instructions.
- Update `PROJECT_ROADMAP.md` with phase statuses and release version.
- Update `PROJECT_LOG.md` with implementation and release milestones.
- Reconcile any changed API, architecture, security, or testing documents.

Do not mark phases complete until their exit criteria have been met and recorded.

## 20. Status Tracking Template

Use this table during implementation. Status values should be controlled and evidence-based.

| Phase | Status | Completion evidence | Open blockers |
|---|---|---|---|
| F0 — Decisions & contract verification | COMPLETED | ADR-074–077 accepted; 3 F0 read endpoints & shared `MoneyStr` types implemented (`593` backend tests); `frontend/` scaffolded with `openapi.json`, `schema.ts`, drift check, API client, in-memory token store, and `4` Vitest smoke tests; documentation reconciled | None |
| F1 — Foundation & design system | COMPLETED & ACCEPTED (2026-11-11) | Tokens, 10 UI primitives, providers/routing/error boundary, CI workflow, Zod `4.6.7` & Vitest `5.1.0` upgrades, Prettier/ESLint/TS/`47` tests/build/drift/`npm audit --omit=dev` (`0` vulns) verified; remote CI run `43036181121` (`ad02a4e`) passed; `ADR-080` approved by owner (`2026-11-11`) | `F1-AUD-009` deferred (non-blocking) |
| F2 — Auth & application shell | IMPLEMENTED & LOCALLY VERIFIED (Formal Acceptance Pending) | F2.1–F2.6 implemented (`F1-AUD-005` & `F1-AUD-006` resolved); `format:check`/`lint`/`typecheck`/`build`/`check:types-drift`/`npm audit --omit=dev` (`0` prod vulns) pass; `87/87` Vitest tests (`22` files) + `5/5` mocked Playwright Chromium E2E pass | Remote F2 CI run pending; live-backend E2E (`E2E_API_MODE=live`) not executed; formal Phase F2 acceptance pending |
| F3 — Analytics, transactions & risk | NOT STARTED | API-backed workflow tests | |
| F4 — Dataset import | NOT STARTED | Upload/import E2E | |
| F5 — Investigation workflow | NOT STARTED | Role-specific investigation E2E | |
| F6 — Evidence & AI | NOT STARTED | Evidence/AI workflow tests | |
| F7 — Hardening | NOT STARTED | Security/accessibility/test reports | |
| F8 — Deployment & release | NOT STARTED | Staging acceptance and release record | |

## 21. Final Roadmap Principle

The frontend should be built as an investigation workspace over a trustworthy backend—not as a second financial intelligence engine.

**The release is successful when users can safely explore backend-authoritative financial data, understand risk signals, manage evidence-backed investigations, and make explicit human decisions through a clear and reliable interface.**
