# FinSignal — Frontend Implementation Roadmap

**Document:** `FRONTEND_ROADMAP.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.0  
**Status:** Draft — implementation-ready after prerequisite decisions and API contract verification  
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

### Objective

Remove the major unknowns that could force expensive rework during implementation. Coordinate and verify backend read API readiness (`BACKEND_API_READINESS.md`), ratify frontend architectural decisions, and prepare the repository foundation.

### Key tasks

- Ratify and record frontend ADRs (ADR-074, ADR-076, ADR-077 ACCEPTED; finalize ADR-075 review).
- Coordinate backend API readiness implementation for missing read endpoints per `docs/BACKEND_API_READINESS.md`:
  - `GET /api/v1/transactions`
  - `GET /api/v1/transactions/{id}`
  - `GET /api/v1/datasets/imports`
- Verify running backend OpenAPI routes and schemas (`/openapi.json`) for every MVP workflow.
- Execute build-time TypeScript type generation via `openapi-typescript` (ADR-076).
- Confirm package manager (npm) and Node.js 20+ LTS runtime policy (.nvmrc).
- Configure development CORS origins and Vite development proxying.
- Confirm role and object-level authorization rules.
- Finalize access-token storage and session lifecycle decision (ADR-075).
- Scaffold frontend workspace with strict TypeScript compiler flags, ESLint, Prettier, and Vitest.

### Deliverables

- Ratified frontend decisions in `DECISIONS.md`.
- Backend API readiness endpoints implemented, tested, and verified in OpenAPI (`docs/BACKEND_API_READINESS.md`).
- Verified MVP API contract inventory and generated TypeScript types.
- Scaffolded frontend project with passing baseline smoke test and typecheck.
- Confirmed development environment and test-account plan.

### Exit criteria

- Backend API readiness endpoints (`/transactions`, `/transactions/{id}`, `/datasets/imports`) return HTTP 200 with verified Pydantic schemas.
- No unresolved security decision blocks authentication implementation.
- All MVP endpoint contracts are verified in `/openapi.json` with generated types committed.
- Frontend builds cleanly, passes lint/typecheck, and runs unit tests without error.
- Core dependency choices are approved and locked via `package-lock.json`.

**Do not start dependent implementation while critical F0 decisions remain unresolved.**

---

## 7. F1 — Application Foundation & Design System

### Objective

Create a reproducible frontend project with a stable application foundation and shared visual primitives.

### Key tasks

- Initialize the React + TypeScript + Vite application.
- Configure strict TypeScript.
- Configure Tailwind CSS and approved design tokens.
- Add approved routing, query, form, validation, and UI dependencies only.
- Configure linting, formatting, scripts, and lockfile.
- Establish feature-oriented source structure.
- Establish environment configuration and API base URL handling.
- Add global typography, spacing, color, border, and focus tokens.
- Implement foundational components: buttons, inputs, selects, badges, cards, dialogs, tables, skeletons, alerts, and empty states.
- Establish accessible component patterns.
- Add error boundary and not-found route.
- Configure unit/component test environment and MSW.
- Add CI for lint, type-check, tests, and production build.

### Deliverables

- Running frontend development application.
- Approved design tokens and foundational components.
- Source structure aligned with `FRONTEND_ARCHITECTURE.md`.
- CI baseline.
- Component and utility test examples.

### Exit criteria

- Clean install from lockfile succeeds.
- Development server and production build work.
- Type-check, lint, and initial tests pass.
- Shared components follow design and accessibility requirements.
- No backend credentials or secrets are present in frontend configuration.

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
| F0 — Decisions & contract verification | NOT STARTED | ADRs, verified OpenAPI inventory | |
| F1 — Foundation & design system | NOT STARTED | Build, CI, component tests | |
| F2 — Auth & application shell | NOT STARTED | Auth E2E and role checks | |
| F3 — Analytics, transactions & risk | NOT STARTED | API-backed workflow tests | |
| F4 — Dataset import | NOT STARTED | Upload/import E2E | |
| F5 — Investigation workflow | NOT STARTED | Role-specific investigation E2E | |
| F6 — Evidence & AI | NOT STARTED | Evidence/AI workflow tests | |
| F7 — Hardening | NOT STARTED | Security/accessibility/test reports | |
| F8 — Deployment & release | NOT STARTED | Staging acceptance and release record | |

## 21. Final Roadmap Principle

The frontend should be built as an investigation workspace over a trustworthy backend—not as a second financial intelligence engine.

**The release is successful when users can safely explore backend-authoritative financial data, understand risk signals, manage evidence-backed investigations, and make explicit human decisions through a clear and reliable interface.**
