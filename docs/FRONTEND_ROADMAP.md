# FinSignal — Frontend Implementation Roadmap

**Document:** `FRONTEND_ROADMAP.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.2  
**Status:** Phase F0 Completed; Phase F1 CONDITIONALLY READY (Audit Remediation & Local Verification Complete; Formal Acceptance Pending)  
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

> [!IMPORTANT]
> **Phase Status: CONDITIONALLY READY (2026-11-11)** — Implementation remediation and local verification are complete; formal acceptance is pending owner approval of the dev-only `minimatch@10.2.6` security exception (`ADR-080`) and remote GitHub Actions CI verification.

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
| Remote GitHub Actions (`.github/workflows/ci.yml`) | **PENDING** |

### Explicitly Deferred Findings from Phase F1 Audit

| Finding | Description | Follow-up |
|---|---|---|
| `F1-AUD-005` | API client and base URL edge-case hardening (`fetch` network `TypeError` normalization, non-JSON `2xx` guard, `/api/v1` dedup, scheme validation) | Phase F2 API integration milestone |
| `F1-AUD-006` | Committed Playwright E2E suite (`frontend/tests/e2e/`) and `playwright.config.ts` `webServer` configuration | Phase F2 testing milestone |
| `F1-AUD-009` | `Button` `size="icon"` loading layout and `Alert` `data-*`/attribute passthrough ergonomics | Future UI refinement |

### Exit criteria & Open Acceptance Conditions

- [x] Clean install compatibility, strict TypeScript, lint, formatting, build, and `47/47` automated tests pass locally.
- [x] Shared components conform to design tokens, CSS computed-style checks, and accessibility requirements.
- [x] No backend credentials, secrets, or browser-storage token persistence exist in frontend code (`npm audit --omit=dev` = `0` vulnerabilities).
- [ ] **Owner security-exception approval (`ADR-080`):** Formal owner sign-off pending for the 7 moderate dev-only advisories (`typescript-eslint@8.72.2` → `minimatch@10.2.6`, `GHSA-g3hv-75wg-m249`).
- [ ] **Remote CI verification:** First remote GitHub Actions execution of `.github/workflows/ci.yml` (`frontend` job on `ubuntu-latest` with Node `24` via `.nvmrc`) is pending push/PR.

---

## 8. F2 — Authentication, Session & Application Shell

### Objective

Deliver a secure sign-in experience and the common application frame.

### Key tasks

- Implement centralized API client and normalized error handling.
- Implement login and current-user API functions.
- Implement the approved session/token adapter.
- Implement session bootstrap and expiration handling.
- Implement logout behavior that accurately reflects backend semantics.
- Add protected route handling.
- Add role-aware navigation and capability presentation.
- Implement application header, sidebar/navigation, page container, and user menu.
- Implement safe post-login return navigation.
- Clear authenticated query/cache state on logout or session expiration.
- Test direct navigation to protected routes.

### Deliverables

- Login page.
- Authenticated application shell.
- Current-user context.
- Protected route behavior.
- Role-aware navigation.
- Session and error handling.

### Exit criteria

- Valid users can authenticate and load `/auth/me`.
- Invalid/expired sessions cannot render protected content.
- `401` and `403` are handled distinctly.
- Logout clears frontend session state without overstating server-side revocation.
- ADMIN, ANALYST, and INVESTIGATOR navigation behavior matches approved permissions.
- Authentication tests pass.

---

## 9. F3 — Analytics, Transaction Exploration & Risk

### Objective

Give users the core read-only financial intelligence experience.

### Key tasks

- Implement analytics API modules and query keys.
- Build dashboard overview using backend analytics responses.
- Build trends, category, and merchant visualizations supported by verified contracts.
- Implement namespace, currency, date-range, and timezone context.
- Build transaction list with server pagination, sorting, and supported filters.
- Build transaction detail view.
- Implement risk result retrieval.
- Implement authorized on-demand risk analysis for supported model lifecycle states.
- Display risk factors and model metadata returned by the API.
- Handle no-risk-result, stale, loading, and failure states.
- Preserve decimal strings and timestamp semantics.

### Deliverables

- Dashboard / analytics overview.
- Analytics views supported by the API.
- Transaction list and detail.
- Risk result panel and authorized analysis action.

### Exit criteria

- Dashboard values match backend responses.
- Transaction filters, sort, and pagination match the API contract.
- Missing risk analysis is not displayed as low risk or zero risk.
- Risk score is not presented as a final fraud verdict.
- No authoritative financial aggregate or risk calculation is performed in the browser.
- Core analytics and transaction tests pass.

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
| F1 — Foundation & design system | CONDITIONALLY READY | Tokens, 10 UI primitives, providers/routing/error boundary, CI workflow, Zod `4.6.7` & Vitest `5.1.0` upgrades, CSS/AbortSignal/Button remediations complete; Prettier/ESLint/TS/`47` tests/build/drift/prod-audit (`0` vulns)/Chrome checks pass locally | Pending owner approval of dev-only `minimatch@10.2.6` exception (`ADR-080`); remote GitHub Actions CI run pending |
| F2 — Auth & application shell | NOT STARTED (BLOCKED UNTIL F1 ACCEPTANCE) | Auth E2E and role checks | Phase F1 formal acceptance |
| F3 — Analytics, transactions & risk | NOT STARTED | API-backed workflow tests | |
| F4 — Dataset import | NOT STARTED | Upload/import E2E | |
| F5 — Investigation workflow | NOT STARTED | Role-specific investigation E2E | |
| F6 — Evidence & AI | NOT STARTED | Evidence/AI workflow tests | |
| F7 — Hardening | NOT STARTED | Security/accessibility/test reports | |
| F8 — Deployment & release | NOT STARTED | Staging acceptance and release record | |

## 21. Final Roadmap Principle

The frontend should be built as an investigation workspace over a trustworthy backend—not as a second financial intelligence engine.

**The release is successful when users can safely explore backend-authoritative financial data, understand risk signals, manage evidence-backed investigations, and make explicit human decisions through a clear and reliable interface.**
