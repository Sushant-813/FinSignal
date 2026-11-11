# FinSignal — Frontend Technical Requirements Document

**Document:** `FRONTEND_TRD.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.1  
**Status:** Reconciled with Phase F2 Implementation Baseline (`package-lock.json` Authoritative; Phase F1 Accepted; Phase F2 Locally Verified)
**Scope:** Browser-based frontend for the existing Backend + ML v1.0.0 platform  
**Prerequisite:** `FRONTEND_PRD.md` and `FRONTEND_DESIGN.md`

---

## 1. Purpose

This document defines the proposed technical stack, engineering constraints, tooling, integration approach, and quality requirements for the FinSignal frontend.

It expands the high-level frontend stack already recorded in the main `TRD.md`:

- React
- TypeScript
- Vite
- Tailwind CSS
- Apache ECharts

This document does not replace the backend TRD, architecture, API guidelines, or security policy. It defines how a separate browser client should consume the existing FastAPI REST API.

**Status discipline:** React, TypeScript, Vite, Tailwind CSS, and Apache ECharts are already named in the main TRD. The additional libraries and implementation conventions below are proposals for approval, not claims that they are already adopted in the repository.

## 2. Technical Goals

The frontend implementation must:

1. Provide a maintainable, typed React application.
2. Consume the versioned REST API under `/api/v1`.
3. Treat the backend and OpenAPI schema as the source of truth for API contracts.
4. Keep server state separate from local UI state.
5. Preserve financial precision and backend-defined semantics.
6. Enforce a clear boundary between presentation, API integration, and domain workflows.
7. Support role-aware navigation while relying on backend authorization.
8. Provide predictable loading, validation, error, and mutation behavior.
9. Support accessible, responsive investigation workflows.
10. Be reproducible through a lockfile and documented scripts.
11. Be testable without requiring a live production service for every component test.
12. Avoid unnecessary infrastructure, abstractions, and dependencies.

## 3. Proposed Technology Stack

### 3.1 Core stack

| Concern | Technology | Status / rationale |
|---|---|---|
| UI library | React | Existing main TRD choice |
| Language | TypeScript | Existing main TRD choice; strict mode required |
| Build/dev server | Vite | Existing main TRD choice |
| Styling | Tailwind CSS | Existing main TRD choice |
| Charts | Apache ECharts | Existing main TRD choice |
| Routing | React Router | Proposed; mature client-side routing |
| Server state | TanStack Query | Proposed; caching, request lifecycle, invalidation |
| Client UI state | React Context initially; Zustand only if justified | Proposed; avoid a global store by default |
| Forms | React Hook Form | Proposed; controlled validation and form state |
| Schema validation | Zod | Proposed; form/input validation |
| HTTP | Native Fetch API behind a typed API client | Proposed; avoid an unnecessary HTTP dependency |
| API type generation | `openapi-typescript` | Proposed; derive compile-time types from backend OpenAPI |
| UI primitives | Radix UI primitives and selected shadcn/ui patterns | Proposed; use as accessible foundations, not as an unmodified visual system |
| Icons | Lucide React | Proposed; consistent icon set |
| Unit/component tests | Vitest, React Testing Library, user-event | Proposed |
| API mocking | Mock Service Worker (MSW) | Proposed; realistic network-boundary tests |
| E2E tests | Playwright | Proposed |
| Linting/formatting | ESLint and Prettier | Proposed; exact config to be committed |
| Package manager | npm with committed `package-lock.json` | Proposed default unless repository already standardizes another manager |

### 3.2 Implemented, Approved, and Deferred Toolchain Baseline (Phase F1 Lockfile)

Per `frontend/package.json`, `frontend/package-lock.json`, and `frontend/.nvmrc` (authoritative over draft estimates), the current dependency and runtime status is:

| Concern | Package / Runtime | `package.json` Range | Installed (`package-lock.json`) | Phase F1 Status |
|---|---|---|---|---|
| Node.js runtime | Node.js | `engines.node`: `^22.12.0 \|\| >=24.0.0` | `.nvmrc`: `24` (verified `v24.18.0`) | **Active (`ADR-079`)** |
| Package manager | npm | — | Verified `11.16.0` | **Active (`ADR-074`)** |
| UI library | `react`, `react-dom` | `^19.1.0` | `19.3.1` | **Installed & Active** |
| TypeScript | `typescript` | `^5.8.3` | `5.9.3` | **Installed & Active** |
| Build/dev server | `vite`, `@vitejs/plugin-react` | `^6.4.0`, `^4.5.0` | `6.4.6`, `4.7.0` | **Installed & Active** |
| Styling | `tailwindcss`, `@tailwindcss/vite` | `^4.1.7` | `4.3.5` | **Installed & Active** |
| Routing | `react-router` | `^7.6.0` | `7.18.5` | **Installed & Active (F2 protected/public/shell routes)** |
| Server state | `@tanstack/react-query` | `^5.76.1` | `5.107.1` | **Installed & Provider Wired (`QueryProvider`; F2 cancel/clear on session end)** |
| Forms & validation | `react-hook-form`, `@hookform/resolvers`, `zod` | `^7.56.4`, `^5.0.1`, `^4.6.7` | `7.91.0`, `5.9.2`, `4.6.7` | **Installed & Active (`ADR-078`; F2 Login form active)** |
| UI primitives & icons | `@radix-ui/react-dialog`, `react-select`, `react-slot`, `lucide-react` | `^1.1.14`, `^2.2.5`, `^1.2.3`, `^0.511.0` | `1.3.1`, `2.4.1`, `1.5.0`, `0.511.0` | **Installed & Active** |
| Charts | Apache ECharts | — *(not yet in `package.json`)* | Not installed | **Approved (`ADR-074`), Deferred to Phase F3** |
| Global client store | Zustand / Redux | — | Rejected / Not installed | **Excluded (`ADR-074`)** |
| HTTP transport | Native `fetch` (`src/lib/api/client.ts`) | Built-in browser/Node | Built-in | **Implemented & Hardened (F2.1 / `F1-AUD-005` resolved)** |
| API contract types | `openapi-typescript` | `^7.8.0` | `7.13.0` | **Installed & Active (`ADR-076`)** |
| Unit/component tests | `vitest`, `@testing-library/*`, `jsdom` | `^5.1.0`, `^16.3.0`/`^6.6.3`/`^14.6.1`, `^26.1.0` | `5.1.0`, `16.3.3`/`6.9.1`/`14.6.9`, `26.1.0` | **Installed & Active (`ADR-079`; `87/87` passing across `22` files)** |
| Network mocking | `msw` | `^2.8.4` | `2.15.0` | **Installed & Active (`onUnhandledRequest: "error"`)** |
| End-to-end tests | `@playwright/test` | `^1.52.0` | `1.65.0` | **Installed & Active (`playwright.config.ts`, `tests/e2e/`, `5/5` mocked Chromium E2E passing; `F1-AUD-006` resolved)** |
| Linting / formatting | `eslint`, `typescript-eslint`, `prettier` | `^9.27.0`, `^8.32.1`, `^3.5.3` | `9.39.5`, `8.72.2`, `3.9.10` | **Installed & Active (`ADR-080` temporary dev-only exception ACCEPTED `2026-11-11`)** |

### 3.3 Version policy

- Use mutually compatible stable releases and pin exact dependency trees in `frontend/package-lock.json`.
- **Node.js & Vite alignment (`ADR-079`):** Because `vitest@5.1.0` requires Node.js `^22.12.0 || ^24.0.0 || >=26.0.0` (dropping Node 20) and `vite@^6.4.0`, `frontend/.nvmrc` is set to `24`, `package.json` `engines.node` is `^22.12.0 || >=24.0.0`, and `vite` requires `^6.4.0` (`6.4.6` locked).
- Do not use floating CDN scripts, unapproved libraries (`ADR-074`), `npm audit fix --force`, or silent npm `overrides`.
- Upgrade major dependencies only via explicit owner approval and ADR documentation (`ADR-078`, `ADR-079`).

### 3.4 Stack decisions & governance record

- `ADR-074` (`ACCEPTED`): Core React/TypeScript/Vite/Tailwind/ECharts stack, React Router, TanStack Query, React Hook Form + Zod, Native Fetch, `openapi-typescript`, Radix UI, Lucide React, Vitest/RTL/MSW/Playwright, npm lockfile; rejects Axios/Redux/Zustand for MVP.
- `ADR-078` (`ACCEPTED`): Zod `3.25.76` → `4.6.7` upgrade (remediates production high advisory `1243066`).
- `ADR-079` (`ACCEPTED`): Vitest `3.2.7` → `5.1.0` upgrade & Node `24` alignment (remediates critical `tinypool`/`@vitest/mocker` dev advisories).
- `ADR-080` (`ACCEPTED` 2026-11-11): Temporary dev-only risk acceptance exception for `typescript-eslint@8.72.2` → `minimatch@10.2.6` (`GHSA-g3hv-75wg-m249`).

*(Original baseline policy note: React, TypeScript, Vite, Tailwind CSS, and Apache ECharts originated in main `TRD.md`; ECharts installation remains intentionally deferred until Phase F3 analytics implementation.)*

## 4. Runtime and Browser Support

### 4.1 Runtime

- The frontend is a browser application served as static assets or through the selected frontend hosting environment.
- The backend remains a separately deployed FastAPI service.
- The browser communicates with the backend through HTTPS in non-local environments.
- No database connection string or database driver belongs in the browser bundle.
- The frontend must not call PostgreSQL directly.

### 4.2 Browser support

Support the current and previous major versions of:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Safari

The application should degrade gracefully where browser features differ. Browser support must be verified during release testing rather than assumed from development in one browser.

### 4.3 Responsive target

The primary design target is desktop investigation work. Tablet and mobile layouts remain supported for review and triage tasks.

Suggested viewport test widths:

- Desktop: 1440 px and 1280 px
- Tablet: 1024 px and 768 px
- Mobile: 390 px and 360 px

These are test viewports, not minimum device requirements.

## 5. TypeScript Requirements

- Enable `strict: true`.
- Avoid `any`; use `unknown` at untrusted boundaries and narrow it explicitly.
- Do not use TypeScript types as a substitute for runtime validation of untrusted input.
- Do not duplicate backend enums or schemas manually when they can be generated from the verified OpenAPI schema.
- Keep domain-specific types separate from view component props where useful.
- Model nullable and optional API fields accurately.
- Treat monetary amounts returned as decimal strings as strings; do not coerce them to JavaScript `number` for calculations.
- Treat identifiers as opaque strings. Do not assume that a UUID-like string can safely be parsed or reformatted.
- Handle timestamps as timezone-aware instants and preserve the original API value where required for round-tripping.
- Use discriminated unions for known API states where the contract supports them.

Implemented compiler constraints (`frontend/tsconfig.app.json`):

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "moduleResolution": "bundler",
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  }
}
```

- **ESLint (`frontend/eslint.config.js`):** Enforces `@eslint/js` recommended, `typescript-eslint` recommended, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, and `@typescript-eslint/no-explicit-any: "error"`.
- **Prettier (`frontend/.prettierrc.json`):** Enforces `semi: true`, `singleQuote: false`, `tabWidth: 2`, `trailingComma: "es5"`, `printWidth: 100`.
- **Testing & MSW integration:** Configured in `frontend/vite.config.ts` (`environment: "jsdom"`, `globals: true`, `setupFiles: ["./tests/setup.ts"]`, `exclude: ["tests/e2e/**"]`) and `frontend/tests/mocks/server.ts` (`onUnhandledRequest: "error"`).

`tsconfig.node.json` covers `vite.config.ts` and `playwright.config.ts` with `strict: true` and `moduleResolution: "bundler"`. Any future relaxation must be deliberate and documented.

## 6. Application Structure

Use a feature-oriented structure with shared infrastructure. Avoid both a single flat `components/` directory and excessive micro-packages.

Proposed structure:

```text
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── providers/
│   │   ├── router/
│   │   └── app-shell/
│   ├── features/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── transactions/
│   │   ├── analytics/
│   │   ├── accounts/
│   │   ├── datasets/
│   │   ├── risk/
│   │   └── investigations/
│   │       ├── queue/
│   │       ├── workspace/
│   │       ├── evidence/
│   │       └── ai-summary/
│   ├── components/
│   │   ├── ui/
│   │   ├── data-display/
│   │   ├── feedback/
│   │   └── forms/
│   ├── lib/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── formatting/
│   │   ├── permissions/
│   │   └── utils/
│   ├── hooks/
│   ├── styles/
│   ├── types/
│   └── main.tsx
├── tests/
│   ├── e2e/
│   ├── fixtures/
│   └── mocks/
├── .env.example
├── package.json
├── package-lock.json
├── tsconfig.json
└── vite.config.ts
```

This is a starting boundary, not a requirement to create empty folders. Add files and modules when a real feature needs them.

### 6.1 Feature module conventions

A feature may contain:

```text
feature-name/
├── api/
├── components/
├── hooks/
├── pages/
├── schemas/
├── types/
└── index.ts
```

Do not create all subdirectories for every feature by default. Keep related code together until its size justifies separation.

### 6.2 Dependency direction

Expected dependency direction:

```text
Pages / Feature UI
        |
        v
Feature hooks and use-cases
        |
        v
Shared API client / generated API types
        |
        v
Backend REST API
```

Shared UI components must not import feature-specific API modules. API modules must not import page components. Avoid circular dependencies between features.

## 7. Routing Requirements

Use client-side routes for the authenticated application.

Proposed route map:

| Route | Screen | Access |
|---|---|---|
| `/login` | Sign In | Public |
| `/` | Role-appropriate landing page | Authenticated |
| `/dashboard` | Dashboard | Authenticated |
| `/transactions` | Transaction list | Authenticated |
| `/transactions/:transactionId` | Transaction detail | Authenticated |
| `/analytics` | Analytics | Authenticated |
| `/accounts` | Account list | Authenticated |
| `/accounts/:accountId` | Account detail, only if contract exists | Authenticated |
| `/datasets` | Dataset management | Admin, Analyst |
| `/investigations` | Investigation queue | Authenticated |
| `/investigations/:investigationId` | Investigation workspace | Authenticated; object-level rules enforced by API |
| `/admin/users` | User management | Admin, only if API exists |
| `*` | Not found | Public |

Route guards are a user-experience mechanism only. A protected route must still handle backend `401` and `403` responses.

### 7.1 Landing page

The default landing page by role remains an open product decision in `FRONTEND_PRD.md`. Do not hard-code a role-to-home mapping until that decision is approved.

## 8. State Management

State must be classified by ownership. Do not put every value in a global store.

### 8.1 Server state

Use TanStack Query if approved for:

- Current-user profile
- Transaction and account lists/details
- Analytics responses
- Dataset import records/details
- Risk analyses
- Investigation queue/workspaces
- Evidence lists
- AI summary status and history

Requirements:

- Query keys must include all parameters that affect the response, including namespace, currency, time range, filters, and pagination.
- Mutations must invalidate or update the relevant queries after success.
- Sensitive lifecycle mutations should prefer authoritative response/refetch behavior over speculative optimistic updates.
- Avoid stale data being presented as current without a visible stale/refresh state where freshness matters.
- Cancel obsolete requests when a user changes filters or navigates away where practical.
- Do not retry non-idempotent mutations automatically unless the API provides an explicit idempotency contract.
- Retry safe read requests only under a bounded policy; do not retry authorization, validation, or conflict failures blindly.

### 8.2 Client/UI state

Use component state for local interactions. Use React Context for small cross-cutting state such as theme or application shell state where appropriate.

Zustand may be introduced only for genuinely shared client-only state, for example:

- Sidebar collapsed/expanded state
- Temporary multi-panel workspace layout
- Cross-page UI preferences that are not server data

Do not store API entities, query results, or a second copy of the current user's server permissions in Zustand.

### 8.3 URL state

State that should survive refresh or be shareable should generally be represented in query parameters:

- Search terms
- Filters
- Sort order
- Page or cursor
- Selected date range, where appropriate

Do not place credentials, access tokens, sensitive evidence, or private notes in URLs.

## 9. API Integration

### 9.1 API base URL

- Use one centralized API base URL configuration.
- The API path includes `/api/v1` unless the deployment configuration explicitly supplies the versioned prefix.
- Do not hard-code hostnames in feature components.
- Local development may use a Vite proxy or an explicit backend origin; select one approach and document it.
- Production origins must be configured per environment.

Suggested environment variable:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Vite exposes `VITE_` variables to browser code. Therefore, this prefix is for public configuration only. Never place secrets in frontend environment variables.

### 9.2 Central API client

Create a small centralized API client responsible for:

- Base URL construction
- JSON request/response handling
- Bearer-token/session integration through the approved auth abstraction
- Multipart form submission
- Consistent API error parsing
- Request cancellation via `AbortSignal`
- Request correlation metadata where supported
- Safe handling of empty `204` responses

Feature code should call domain-specific functions, not construct arbitrary URLs throughout components.

### 9.3 HTTP method behavior

- `GET`: safe retrieval; may be cached.
- `POST`: creation or explicit operation; do not automatically retry without idempotency guarantees.
- `PATCH`: state mutation; handle `409` and server authorization failures.
- `DELETE`: do not expose unless the backend contract explicitly permits the operation. Evidence and resolved investigations are immutable.

### 9.4 OpenAPI and type generation

The backend OpenAPI schema is the contract source of truth.

Proposed process:

1. Start the backend in a known environment.
2. Retrieve the actual `/openapi.json`.
3. Verify it describes implemented routes, request/response schemas, security requirements, and status codes.
4. Generate TypeScript types using the selected OpenAPI generator.
5. Commit generated types or regenerate deterministically in CI, choosing one approach.
6. Fail CI when generated types are stale, if generation is part of the CI workflow.
7. Keep handwritten API functions thin and domain-oriented.

Important limitation: generated TypeScript types provide compile-time assistance; they do not validate runtime JSON. Add runtime validation only at boundaries where it provides material value, especially for external/untrusted payloads or critical structured responses. Avoid duplicating every generated schema in Zod without a reason.

### 9.5 API contract verification

Before implementing a feature, confirm the exact route and schema in the running OpenAPI document. Documentation examples alone may be stale.

In particular, confirm:

- Account detail/behavior routes and response schemas.
- User-management routes and exact permissions.
- Audit-event read/list routes, if any.
- Investigation list filters and pagination.
- Investigation assignment and status transition request bodies.
- Evidence attachment request/response schemas.
- AI summary generation response, lifecycle, status retrieval, history, and stale-state fields.
- Risk analysis request parameters and model lifecycle authorization.
- Dataset import recovery behavior and import detail schema.

Do not invent a route or response shape to make a screen easier to implement.

## 10. Authentication and Authorization Integration

This section defines frontend integration behavior, not token storage policy. Token/session architecture is decided in `FRONTEND_SECURITY.md`.

### 10.1 Authentication endpoints

The documented API includes:

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/register
```

Login returns an access token, token type, and expiration duration. Protected calls use:

```http
Authorization: Bearer <access_token>
```

### 10.2 Current-user lifecycle

- Load current-user context after the approved session is established.
- Do not treat a decoded JWT role claim as the sole source of UI permissions.
- Treat `/auth/me` as the current identity context.
- Clear authenticated client state after a confirmed invalid/expired session.
- Avoid redirect loops between login and protected routes.
- Preserve the user's intended destination after login only if doing so does not expose sensitive data in the URL.

### 10.3 Authorization behavior

- Build a small centralized permission/presentation helper from the approved role/capability matrix.
- Include object-level context such as investigation assignment where the API exposes it.
- Do not scatter raw role string comparisons across components.
- Do not assume that route visibility guarantees access.
- If the API returns `403`, show an access-denied state without leaking resource details.
- If authorization changes during a session, refresh authoritative user/resource context as appropriate.

### 10.4 Logout

The API guidelines explicitly note that JWT logout is stateless unless revocation or refresh-token infrastructure is implemented. Frontend logout must follow the final decision in `FRONTEND_SECURITY.md`; do not claim server-side token invalidation if the implementation only removes local client state.

## 11. Financial Data and Formatting

### 11.1 Monetary values

The API guidelines specify decimal-safe monetary representations as strings, for example:

```json
{
  "amount": "1250.50",
  "currency": "INR"
}
```

Frontend requirements:

- Keep monetary values as strings at the API boundary.
- Do not use JavaScript floating-point arithmetic for authoritative financial values.
- Do not calculate totals, averages, balances, net cash flow, or risk scores from transaction rows in the browser.
- Display the currency code explicitly.
- Do not combine amounts from different currencies.
- Do not render missing values as zero.
- Use a decimal-safe display/formatting strategy that does not mutate the underlying value.
- If client-side arithmetic is needed for a non-authoritative UI-only purpose, use a decimal library and label the result as such; prefer avoiding such calculations.

### 11.2 Timestamps

- Parse ISO-8601 timestamps with timezone awareness.
- Display a clearly defined timezone.
- Keep raw API timestamps available for audit/context display when appropriate.
- Do not assume UTC timestamps are local time.
- Analytics requests must preserve the API's half-open time-window semantics `[from_time, to_time)`.

### 11.3 Risk semantics

- Risk scores and levels are backend outputs.
- Display the exact returned level/score and associated factors.
- Do not map `HIGH` or `CRITICAL` to a fraud verdict.
- Distinguish missing analysis, failed analysis, stale analysis, and low score where the API exposes these states.

## 12. Charts and Data Visualization

Apache ECharts is the charting library named by the main TRD.

Requirements:

- Use ECharts for analytical visualizations that materially improve understanding.
- Prefer clear time-series, category, and comparison charts over decorative visualizations.
- Use backend-computed series and aggregates.
- Do not derive financial totals from the currently loaded transaction page.
- Include axis labels, units, currency, selected time range, and timezone context.
- Provide accessible text summaries or equivalent tabular views.
- Avoid misleading truncated axes and unexplained normalization.
- Risk visualizations must not imply statistical certainty or final fraud classification.
- Keep chart components isolated from data-fetching logic so they can be tested with deterministic fixtures.

## 13. Forms and Validation

If React Hook Form and Zod are approved:

- Use form schemas for client-side input validation.
- Treat frontend validation as usability support; backend validation remains authoritative.
- Map backend field-level validation errors to the relevant fields when the response supports it.
- Preserve user-entered values after recoverable validation failures.
- Prevent duplicate submissions while a mutation is pending.
- Require explicit confirmation for irreversible or terminal actions such as investigation resolution.
- Do not silently normalize or change financial input values in a way that changes their meaning.

For dataset upload:

- Enforce the documented 50 MB client-side file-size limit for immediate feedback.
- Check `.csv` extension as a convenience only; backend validation is authoritative.
- Submit `multipart/form-data` correctly; do not manually set a multipart boundary header.
- Display import ID, status, row counts, duplicate status, and available validation errors.
- Support the documented UTF-8 and UTF-8 BOM behavior without trying to re-encode the uploaded file in the browser.

## 14. Error Handling and Observability

### 14.1 API error model

The API guidelines identify common status codes:

- `400` malformed request
- `401` unauthenticated
- `403` forbidden
- `404` missing resource
- `409` state/uniqueness conflict
- `413` payload too large
- `422` validation failure
- `429` rate limit exceeded
- `500` unexpected server error
- `503` dependency/system unavailable

The API client should normalize errors into a stable frontend error type while preserving:

- HTTP status
- Backend error code
- Safe user-facing message
- Field validation details, if provided
- Request/correlation ID, if provided
- Retry guidance such as `Retry-After`, if provided

Do not display raw stack traces, SQL messages, internal file paths, tokens, or provider secrets.

### 14.2 Error presentation

- Field validation errors belong next to the relevant form field.
- Page-level failures should provide a retry path when retry is safe.
- A failed panel must not make the entire page look empty or successful.
- A `409` should prompt a refresh/reconciliation of server state where appropriate.
- A `429` should respect server-provided retry timing.
- A `413` should explain the upload-size limit.
- A `403` should not trigger repeated automatic retries.
- A network failure should be distinguishable from an empty result.

### 14.3 Logging

- Do not log credentials, access tokens, raw evidence payloads, or unnecessary financial/personal data.
- Development logging may include safe request method/path/status and request ID.
- Production telemetry, if added, must follow privacy and security review.
- Do not introduce a third-party analytics or session-replay service without explicit approval and a data-handling assessment.

## 15. Environment Configuration

Use separate configuration for local development, test, staging, and production.

Suggested public configuration:

```text
VITE_API_BASE_URL
VITE_APP_ENV
```

Rules:

- `.env.example` contains placeholders only.
- Real environment files must be ignored by version control.
- No secret values may use the `VITE_` prefix.
- The application should fail clearly when required public configuration is missing or malformed.
- Avoid embedding environment-specific URLs in source code.
- CORS must be configured on the backend for the exact frontend origin. Frontend configuration does not bypass CORS.

## 16. Build and Development Scripts

Actual scripts implemented in `frontend/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc -b --pretty",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "api:types": "openapi-typescript openapi.json -o src/api/generated/schema.ts",
    "check:types-drift": "node scripts/check-types-drift.mjs"
  }
}
```

- OpenAPI types are generated from `frontend/openapi.json` into `frontend/src/api/generated/schema.ts` and verified for zero drift in CI via `npm run check:types-drift`.
- Playwright E2E tests (`npm run test:e2e`, `F1-AUD-006` resolved in F2.6) build a fresh production bundle and serve via `vite preview` (`reuseExistingServer: false`) for mocked-API Chromium tests, with an optional `E2E_API_MODE=live` mode targeting Vite dev proxy (`:5173` -> FastAPI).

### 16.1 Local development

Expected developer workflow:

1. Install the documented Node.js version.
2. Install dependencies from the lockfile.
3. Configure the public API base URL.
4. Start the backend and database using the project's approved local workflow.
5. Start the Vite development server.
6. Run lint, typecheck, unit tests, and relevant E2E tests before committing.

## 17. Testing Requirements

The frontend test strategy is specified in `FRONTEND_TESTING_STRATEGY.md`. At minimum:

- Unit tests for formatting, permission helpers, and API error normalization.
- Component tests for forms, tables, status indicators, and structured AI summary rendering.
- API integration tests using mocked HTTP responses at the network boundary.
- Tests for `401`, `403`, `404`, `409`, `413`, `422`, `429`, `5xx`, and network failure behavior.
- Tests proving monetary decimal strings are not converted to floating-point values for calculations.
- Tests proving AI interpretations are visually distinct from observed facts and human decisions.
- E2E tests for sign-in, dataset import, transaction review, investigation creation, evidence attachment, AI summary, and human resolution.
- Accessibility checks for core routes and workflows.

Do not test only implementation details. Prefer assertions about user-observable behavior and API contracts.

## 18. Performance Requirements

Do not set arbitrary numerical performance claims before measuring the deployed application.

Engineering requirements:

- Use server-side pagination and filtering for large collections.
- Do not fetch unbounded transaction or evidence collections.
- Lazy-load non-critical routes and heavy charting modules where beneficial.
- Avoid rendering thousands of table rows at once.
- Debounce text search where appropriate, while ensuring the query state remains understandable.
- Cancel obsolete requests where practical.
- Keep chart data bounded by backend-supported date ranges and aggregation.
- Measure production build size and route-level loading behavior before release.
- Establish concrete budgets after the first baseline build and record them in the roadmap or CI configuration.

## 19. Deployment and Hosting Boundary

Frontend hosting is not finalized by this document.

Regardless of hosting provider:

- Build output must be deployable as static assets unless a later requirement justifies server rendering.
- SPA route fallback must be configured so direct navigation to nested routes works.
- Backend API origin must be configured per environment.
- Backend CORS allowlist must include the deployed frontend origin.
- HTTPS is required outside local development.
- No secrets are shipped in static assets.
- Deployment configuration must be documented in the frontend roadmap and master deployment plan.

Do not assume frontend and backend share a domain. If they do not, cookie-based authentication, if selected, requires deliberate SameSite, Secure, CORS, and CSRF design.

## 20. Coding Standards

- Prefer small, readable components with explicit props.
- Keep API calls out of presentational components.
- Keep business/domain rules out of generic UI components.
- Use semantic HTML before custom interactive elements.
- Avoid unnecessary `useEffect` for derived state or event-driven operations.
- Avoid premature generic abstractions.
- Keep component files focused; split when complexity warrants it.
- Use consistent naming and import conventions.
- Do not suppress TypeScript or lint errors without an explained, narrow reason.
- Do not commit generated build artifacts unless the repository explicitly requires them.
- Keep design tokens centralized and consistent with `FRONTEND_DESIGN.md`.
- Never hard-code role permissions in multiple unrelated components.
- Never use mock data as a silent fallback in production.

## 21. Technical Constraints and Prohibited Patterns

The frontend must not:

1. Connect directly to PostgreSQL.
2. Reimplement backend financial calculations, behavioral feature generation, risk scoring, or analytics aggregation.
3. Treat browser-side role checks as authorization.
4. Store API results redundantly in a global UI store when query caching owns them.
5. use `localStorage` for JWTs unless explicitly approved in `FRONTEND_SECURITY.md`.
6. Put secrets in Vite environment variables or browser bundles.
7. Invent endpoints or infer undocumented request/response fields.
8. Automatically retry non-idempotent operations without an idempotency guarantee.
9. Edit/delete immutable evidence or mutate resolved investigations.
10. Present anomaly/risk output as proof of fraud.
11. Render untrusted user content as raw HTML.
12. Expose internal model/provider implementation details as ordinary user-facing controls.
13. Load all transactions to calculate a client-side dashboard.
14. Merge financial amounts across currencies without backend-defined conversion semantics.

## 22. Dependencies and Relationship to Other Documents

| Document | Relationship |
|---|---|
| `FRONTEND_PRD.md` | Defines frontend product scope, roles, workflows, and acceptance criteria |
| `FRONTEND_DESIGN.md` | Defines visual language, layout, component behavior, and accessibility presentation |
| `FRONTEND_ARCHITECTURE.md` | Defines application structure, module boundaries, routing, state ownership, and data flow |
| `FRONTEND_API_INTEGRATION.md` | Defines exact API operations, request/response integration, and contract generation |
| `FRONTEND_SECURITY.md` | Final authority for token/session storage, browser security, and sensitive-data handling |
| `FRONTEND_TESTING_STRATEGY.md` | Defines detailed frontend test levels and coverage |
| `FRONTEND_ROADMAP.md` | Defines implementation sequencing and phase exit criteria |
| `TRD.md` | Parent technical requirements and approved high-level stack |
| `API_GUIDELINES.md` | Backend REST API conventions and endpoint contracts |
| `SECURITY.md` | Backend security policy and authorization rules |
| `ARCHITECTURE.md` | System boundaries and backend architecture |
| `CODING_STANDARDS.md` | Existing engineering principles; frontend-specific standards are expanded here |
| `DECISIONS.md` | Records accepted technology and architecture decisions |

## 23. Open Technical Decisions

The following items require explicit approval or verification before implementation:

1. Ratify the proposed dependency set and package manager.
2. Select exact supported Node.js version and dependency versions.
3. Decide whether API types are generated during development, CI, or both.
4. Verify the OpenAPI schema accurately represents the implemented API before generating types.
5. Finalize JWT storage/session behavior in `FRONTEND_SECURITY.md`.
6. Decide Vite proxy versus direct backend origin for local development.
7. Confirm account detail/behavior, user management, and audit read API availability.
8. Define production hosting and SPA route fallback.
9. Establish measurable performance budgets after a baseline build.
10. Confirm whether the frontend repository is a new top-level `frontend/` directory or a separate repository.

## 24. Definition of Done

This technical requirements document is ready to guide implementation when:

- The proposed dependency set is reviewed and ratified.
- The repository location and package-manager convention are agreed.
- The API type-generation approach is verified against the running OpenAPI schema.
- The authentication/session decision is documented in `FRONTEND_SECURITY.md`.
- The frontend architecture and API integration documents align with this TRD.
- All known backend contract gaps affecting MVP screens are resolved or explicitly excluded.
- CI checks and test tooling are agreed.
- Technical decisions are recorded in `DECISIONS.md`.

## 25. Final Technical Principle

The frontend is a typed, testable client of FinSignal's backend—not a parallel financial intelligence engine.

**Keep the browser responsible for interaction and presentation; keep the backend responsible for authoritative financial data, intelligence, permissions, evidence, and investigation state.**
