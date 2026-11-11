# FinSignal — Frontend Security Document

**Document:** `FRONTEND_SECURITY.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.1  
**Status:** Phase F0/F1 Controls Accepted (`ADR-075`, `ADR-078`–`ADR-080`); Phase F2 Authentication & Session Controls Implemented and Locally Verified (Remote F2 CI & Live-Backend E2E Pending)
**Scope:** Browser security, authentication/session handling, authorization presentation, sensitive financial data, and secure frontend integration

---

## 1. Purpose and Authority

This document defines security requirements for the FinSignal browser frontend.

It is subordinate to the backend security model in `SECURITY.md` and the actual authorization enforced by the API. It complements:

- `FRONTEND_PRD.md`
- `FRONTEND_TRD.md`
- `FRONTEND_ARCHITECTURE.md`
- `FRONTEND_API_INTEGRATION.md`
- `SECURITY.md`
- `API_GUIDELINES.md`
- `DECISIONS.md`

**Authority rule:** the backend is the security boundary. Frontend controls, route guards, hidden navigation items, and role-aware presentation do not grant or deny actual access. Every protected operation must be authorized by the backend.

This document makes recommendations where the existing project documentation leaves a decision open. A recommendation is not an approved architectural decision until it is reviewed and recorded in `DECISIONS.md`.

## 2. Security Objectives

The frontend must:

1. Protect authenticated access to financial and investigation data.
2. Minimize exposure of access tokens and sensitive data in the browser.
3. Avoid introducing insecure persistence or logging of financial information.
4. Respect backend RBAC and object-level authorization.
5. Prevent common browser threats, including XSS, CSRF where applicable, clickjacking, and unsafe content injection.
6. Preserve data integrity and the distinction between facts, model-derived signals, AI interpretations, and human decisions.
7. Fail closed when authentication or authorization state is unknown.
8. Avoid claiming security guarantees that the backend does not implement.

## 3. Threat Model and Trust Boundaries

### 3.1 Assets

- JWT access tokens and authenticated session state.
- User identity, email, role, and account status.
- Transaction records and account/merchant/device context.
- Risk scores, model metadata, and risk factors.
- Investigation assignments, status, priority, and resolution.
- Evidence payloads and evidence references.
- AI-generated investigation summaries and their provenance.
- Dataset import metadata and validation errors.
- API origin/configuration and non-secret runtime configuration.

### 3.2 Trust boundaries

| Boundary | Trust level | Requirement |
|---|---|---|
| Browser UI | Untrusted | Treat all browser state and client input as attacker-modifiable |
| Frontend JavaScript | Untrusted execution environment | Never place backend secrets or privileged credentials here |
| Frontend-to-API request | Authenticated but exposed to browser risks | Use HTTPS outside local development and approved token transport |
| FastAPI backend | Authoritative application boundary | Enforce authentication, RBAC, object-level checks, validation, and state transitions |
| PostgreSQL/database | Backend-controlled | Never connect to it from the browser |
| LLM/provider | External trust boundary | Follow backend data-minimization and provider policy; frontend must not call provider directly |

### 3.3 Attacker assumptions

Design defensively against:

- Malicious scripts executing in the application origin.
- Malicious or compromised browser extensions.
- A user modifying local JavaScript state, route parameters, or API requests.
- A user attempting to access another investigator's case.
- Stolen or expired access tokens.
- Malformed API responses and unexpected error content.
- Sensitive values accidentally copied into logs, analytics, URLs, or browser persistence.
- Network interception on insecure transport.
- Cross-origin requests from untrusted websites.

The frontend cannot protect against a fully compromised endpoint, browser, or operating system. It must nevertheless avoid making compromise easier or increasing the impact unnecessarily.

## 4. Authentication Model

### 4.1 Backend contract

The documented authentication model is JWT Bearer authentication.

- `POST /api/v1/auth/login` returns `access_token`, `token_type`, and `expires_in`.
- Protected requests send `Authorization: Bearer <access_token>`.
- `GET /api/v1/auth/me` returns the authenticated user's ID, email, role, and active status.
- JWT validation and authorization are enforced by the backend.
- The backend documentation describes stateless access tokens unless revocation infrastructure is implemented.

The frontend must not decode a JWT and treat its claims as proof that a request is authorized. `/auth/me` is the authoritative current-user context for presentation; the backend remains authoritative for each request.

### 4.2 Token storage options

| Storage approach | Advantages | Security and operational trade-offs |
|---|---|---|
| In-memory JavaScript state | Token is not persisted across reloads; reduces persistence after browser restart | XSS executing in the origin can still access or use the token; page reload requires re-authentication |
| `sessionStorage` | Survives reloads within a tab; generally cleared when the tab session ends | Accessible to same-origin JavaScript; exposed to successful XSS; behavior across duplicated/restored tabs varies |
| `localStorage` | Persistent across browser restarts and tabs | Accessible to same-origin JavaScript; persistent token theft impact; not recommended as the default |
| `HttpOnly` secure cookie | JavaScript cannot directly read the cookie; can support server-managed session patterns | Requires deliberate backend cookie support, `Secure`, `SameSite`, credentialed CORS, and CSRF design; not a frontend-only change |

### 4.3 Approved MVP decision — ADR-075 (2026-11-10)

<badge color="success">Accepted</badge>

**Decision: keep the access token in memory only for the initial MVP.**

Rationale:

- The system owner approved Option 1 (in-memory access-token storage) under ADR-075 on 2026-11-10.
- The current backend contract is a Bearer-token API.
- The backend documentation does not establish a refresh-token endpoint or revocation mechanism.
- In-memory storage avoids persisting the access token in `localStorage` or `sessionStorage`.
- It limits persistence after reload/closing the tab, at the cost of requiring the user to sign in again after a full reload.

Implementation implications:

1. Keep the token inside a small session/authentication service.
2. Do not expose token values through component props, URL parameters, query keys, logs, error reports, or analytics.
3. Do not store the token in global state that is persisted by a persistence plugin.
4. Clear the token on explicit logout and confirmed invalid/expired-session responses.
5. Re-authenticate after a full page reload.
6. Do not attempt silent refresh unless a backend refresh contract is implemented and separately approved.
7. Treat `TokenResponse.expires_in` as authoritative; 30 minutes is the documented default, not a frontend constant.
8. After re-authentication, restore only a validated safe internal destination. Do not persist sensitive evidence, private notes, or unsaved sensitive form payloads to preserve navigation.

This accepted decision is a trade-off, not a claim that in-memory storage prevents XSS. Any script executing in the application origin may be able to access or use the token while the session is active.

### 4.4 Alternatives requiring backend changes

If persistent sessions are a product requirement, evaluate a backend-supported `HttpOnly`, `Secure`, appropriately `SameSite` cookie/session design. That requires coordinated backend changes and explicit decisions for:

- Cookie domain and path.
- `SameSite` mode.
- Credentialed CORS.
- CSRF protection and origin validation.
- Session expiration and revocation.
- Refresh and rotation behavior.
- Logout invalidation.
- Local development proxy/origin behavior.

Do not simulate a cookie-based session solely in frontend code.

## 5. Session Lifecycle

### 5.1 Login

1. Submit credentials over HTTPS outside local development.
2. Do not persist or log the password.
3. Receive the access token and expiration duration.
4. Store the token using the approved session strategy.
5. Call `/api/v1/auth/me`.
6. Establish authenticated UI state only after the current-user request succeeds.
7. If `/auth/me` fails due to an invalid/expired token, clear the session and return to sign-in.

Do not treat a successful login response alone as sufficient to populate all user identity and authorization context.

### 5.2 Session bootstrap

For the approved in-memory strategy (ADR-075), a full reload starts unauthenticated. If a later strategy persists session state, bootstrap must validate the session with `/auth/me` before protected content is rendered.

While session status is unknown:

- Show a neutral loading state.
- Do not briefly render protected pages.
- Avoid redirect loops.
- Preserve a safe internal destination only; reject external redirect targets.

### 5.3 Expiration and `401`

- A confirmed `401` on an authenticated (`Bearer`) request notifies `AuthProvider` once per `sessionEpoch` (`session-events.ts`, `authAttemptId` + `sessionEpoch` guards prevent stale races and repeated loops):
  - Synchronously invalidates the attempt ID, clears the `expires_in` timer, aborts pending auth requests, calls `clearAccessToken()` (`sessionEpoch++`), sets `status = "unauthenticated"`, triggers `void queryClient.cancelQueries()`, and calls `queryClient.clear()` synchronously.
  - Emits one expiration notice without duplicate dialogs.
- Do not treat `403` as an expired session; `apiRequest` does not invoke `notifyUnauthorized` on `403`, preserving the authenticated session and surfacing authorization failure cleanly.

### 5.4 Logout

The backend security documentation and verified route `POST /api/v1/auth/logout` confirm that stateless JWT access tokens remain valid until expiration (`auth.py` implements no token blocklist or revocation).

As implemented in Phase F2 (`Option B` — local-only client logout):

- `signOut()` synchronizes attempt invalidation, clears expiration timers and in-memory access tokens (`token-store.ts`), sets `status = "unauthenticated"` (`preserveRedirectOnUnauthenticated = false` so deliberate sign-out navigates cleanly to `/login`), initiates `void queryClient.cancelQueries()`, and clears `QueryClient` cache synchronously.
- Does not call `POST /api/v1/auth/logout` during UI sign-out and never claims server-side JWT revocation (although typed `logout()` exists in `auth-api.ts` for future revocation/audit integration).

## 6. Authorization and Role-Aware UI

### 6.1 Roles

The documented roles are:

- `ADMIN`
- `ANALYST`
- `INVESTIGATOR`

In the generated OpenAPI contract, `UserResponse.role` is typed as `string`; Phase F2 validates roles at runtime (`isUserRole` / `parseAuthUser`) and fails closed whenever `is_active !== true` or `role` is unrecognized.

### 6.2 Authorization rules

- Backend authorization is mandatory for every protected API operation.
- Frontend permission helpers may hide or disable actions for usability; in Phase F2, `src/lib/permissions/capabilities.ts` separates read-only dataset import history visibility (`canViewDatasetImports`: `ADMIN`, `ANALYST`, `INVESTIGATOR`) from dataset upload/recovery management (`canManageDatasets`: `ADMIN`, `ANALYST` only), omitting speculative F3–F6 rules until their respective phases.
- Do not scatter role string comparisons across components.
- Use one centralized capability/presentation layer based on the approved endpoint-specific permission matrix.
- Include object-level context, such as whether an investigator is assigned to a case, when the API exposes it.
- Never infer assignment from a route parameter or locally cached selection.
- Refresh authoritative resource state after a conflict or relevant permission change.

### 6.3 Investigation permissions

`SECURITY.md` documents the following investigation policy:

**ADMIN**
- Global investigation visibility and write authority.
- Can assign, reassign, or unassign cases.
- Can transition eligible cases, update priority, link related transactions, attach evidence, and resolve cases.
- A resolved case is immutable even for ADMIN.

**INVESTIGATOR**
- Can view the shared triage queue and investigation workspaces.
- Can self-assign an unassigned case or self-unassign.
- Can modify priority, link related transactions, attach append-only evidence, and resolve only a case currently assigned to them.
- Cannot assign a case to a peer or reassign a case to another investigator.
- Cannot modify a resolved case.

**ANALYST**
- Can create unassigned investigations.
- Can view the shared queue, workspace, linked transactions, and evidence snapshots.
- Is read-only on existing investigations.
- Cannot self-assign, modify cases, link transactions, attach evidence, or resolve cases.

These rules must be reconciled with `API_GUIDELINES.md` and the running backend. Where endpoint-specific documentation conflicts with a general role matrix, do not guess: verify the implemented endpoint policy and record the canonical rule.

### 6.4 Access-denied behavior

On `403`:

- Show an access-denied state.
- Do not expose hidden data from the failed resource.
- Do not retry automatically.
- Do not assume the user's role is wrong; object-level assignment or lifecycle rules may be the reason.

A hidden button is not a security control.

## 7. Browser Threat Mitigations

### 7.1 Cross-Site Scripting (XSS)

Requirements:

- Prefer React's normal escaped text rendering.
- Do not use `dangerouslySetInnerHTML` for API-provided content.
- Do not render user notes, evidence payloads, filenames, or AI output as trusted HTML.
- If rich text is introduced, use a maintained sanitizer with a narrowly defined allowlist and security review.
- Avoid dynamic script injection and untrusted URL construction.
- Keep dependencies maintained and review security advisories.
- Apply a restrictive Content Security Policy (CSP) where deployment infrastructure supports it.
- Avoid inline scripts and unsafe CSP exceptions where practical.

AI-generated summaries are untrusted text, even when returned by the backend. Render as plain text or safely parsed, sanitized Markdown if Markdown is explicitly supported.

### 7.2 Cross-Site Request Forgery (CSRF)

The backend security documentation states that the current API uses Bearer tokens in the `Authorization` header. Browsers do not automatically attach this header cross-origin, so this model is not inherently subject to traditional ambient-cookie CSRF.

Requirements:

- Keep Bearer tokens out of URLs and cookies unless the architecture is deliberately changed.
- Maintain the explicit backend CORS allowlist.
- Do not use `mode: "no-cors"` to work around CORS.
- If cookie-based authentication is introduced, implement the backend's approved CSRF defenses before deployment.
- Reassess CSRF if authentication transport changes.

CORS is not a substitute for authentication or authorization.

### 7.3 Clickjacking and framing

Production deployment should use an appropriate anti-framing policy, preferably through response headers such as `frame-ancestors` in CSP and/or `X-Frame-Options` where compatible.

The frontend build itself cannot reliably enforce response headers. Configure them at the hosting/reverse-proxy layer and verify the deployed response.

### 7.4 Open redirects

- Accept only internal application paths for post-login redirects.
- Reject absolute external URLs and protocol-relative URLs.
- Do not trust `returnUrl`, `next`, or similar query parameters without validation.

### 7.5 URL and referrer hygiene

Never place the following in URLs:

- Access tokens or passwords.
- Full transaction payloads.
- Evidence payloads.
- Sensitive AI summary text.
- Personal or financial data not needed for navigation.

Use opaque resource IDs only where the API's authorization model supports them. UUIDs do not replace object-level authorization.

## 8. CORS, HTTPS, and Deployment

### 8.1 CORS

`SECURITY.md` documents:

- Explicit origin allowlist through backend `cors_origins`.
- Development defaults include `http://localhost:3000` and `http://localhost:5173`.
- Production must override defaults with explicit frontend origins.
- Allowed methods include standard REST methods.
- Allowed headers include `Authorization`, `Content-Type`, and `X-Request-ID`.
- `X-Request-ID` is exposed to browser clients.
- Wildcard origin with credentialed CORS is rejected by configuration validation.

Deployment requirements:

- Add only the actual deployed frontend origin(s).
- Do not use wildcard origins in production.
- Do not enable credentialed CORS unless the selected authentication strategy requires it.
- Verify preflight requests for required methods and headers.
- Remember that CORS constrains browser access; it does not block non-browser clients.

### 8.2 HTTPS

- HTTPS is mandatory outside local development.
- Do not send credentials or financial data over plain HTTP in production.
- Configure HSTS at the hosting/reverse-proxy layer after confirming the domain and deployment topology.
- Avoid mixed content; all API and asset requests must use secure transport.

### 8.3 Environment variables

- Only non-secret configuration may use Vite-exposed `VITE_` variables.
- Never place API signing keys, database credentials, LLM provider keys, or private backend secrets in frontend environment variables.
- Frontend API base URL is configuration, not a secret.
- Validate production configuration during deployment.

## 9. Sensitive Data Handling

### 9.1 Data minimization

- Fetch only data needed for the active workflow.
- Avoid retaining full transaction/evidence payloads in global state.
- Clear authenticated caches on logout and session expiration.
- Do not copy sensitive data into URLs, browser titles, telemetry, or client-side analytics.
- Avoid unnecessarily long-lived in-memory caches for sensitive investigation content.

### 9.2 Browser storage

Do not persist the following in `localStorage`, `sessionStorage`, IndexedDB, or service-worker caches without a reviewed requirement:

- Access tokens.
- Passwords.
- Full transaction records.
- Evidence payloads.
- AI investigation summaries.
- Sensitive investigation notes.
- Exported financial datasets.

The recommended in-memory token strategy does not automatically prohibit harmless UI preferences such as theme or table density from being persisted, provided those preferences contain no sensitive data.

### 9.3 Cache behavior

- Do not implement a service worker or offline cache for authenticated financial data in the MVP unless a separate security review approves it.
- Ensure authenticated query/cache state is cleared when the session ends.
- Do not rely on browser cache clearing as the only protection against access.
- Configure sensitive API response caching on the backend where appropriate; frontend behavior cannot override server cache headers.

### 9.4 Clipboard and downloads

- Copy/export actions should be explicit user actions.
- Do not automatically copy transaction details or evidence.
- Do not include tokens or credentials in exports.
- Verify export authorization and scope on the backend.
- Revoke temporary object URLs after downloads where applicable.
- Warn users when exporting sensitive data if the product requirements call for it.

### 9.5 Logging and telemetry

Never log:

- Passwords or access tokens.
- Authorization headers.
- Full transaction or evidence payloads.
- Full AI summaries.
- Sensitive user-provided investigation notes.

Prefer safe metadata such as request ID, endpoint category, status code, duration, and non-sensitive error code. Review any third-party analytics/error-monitoring provider before sending user or financial context.

## 10. Financial and Investigation Data Integrity

The frontend must preserve the backend's meaning and provenance.

- Keep monetary values as decimal-safe strings at the API boundary.
- Do not calculate authoritative balances, risk scores, financial aggregates, or behavioral features in the browser.
- Preserve currency and timezone metadata.
- Distinguish raw transaction facts from derived risk signals.
- Distinguish model risk output from a human investigation resolution.
- Never convert `SUSPICIOUS` or a high risk score into `CONFIRMED_FRAUD`.
- Do not label a low risk score as proof of legitimacy.
- Do not modify immutable evidence.
- Do not let AI summary content modify investigation status, priority, evidence, or resolution.
- Show stale AI summaries as stale when the API says they are stale.
- Preserve uncertainties and limitations in AI-generated output.

## 11. File Upload Security

Dataset import is a sensitive operation.

- Use the documented multipart field names and backend contract.
- Enforce the documented 50 MB client-side limit for user feedback; backend validation remains authoritative.
- Do not trust filename extensions or browser-provided MIME type as proof of file contents.
- Do not parse or execute uploaded file content in the browser.
- Do not render raw CSV cells as HTML.
- Display backend validation errors as escaped text.
- Do not expose internal file paths or storage locations.
- Do not retry a potentially completed import blindly after a timeout; retrieve import state first.
- Recovery must use the original file and the backend's documented hash verification.
- Restrict upload/recovery controls by role for usability, while relying on backend authorization.

## 12. AI Output and External Provider Boundaries

The frontend consumes structured AI summary output from the backend. It must not call the LLM provider directly.

- Treat AI output as untrusted content.
- Render the documented sections separately: executive summary, observed facts, derived signals, potential interpretations, uncertainties and limitations.
- Do not present potential interpretations as established facts.
- Preserve evidence references and provenance when returned.
- Do not invent evidence links.
- Display stale/failed/pending states from the API accurately.
- Do not imply that AI generated content is a final fraud decision.
- Do not include sensitive case data in client-side third-party telemetry.

Provider selection, prompt security, data retention, and external data processing are governed by backend `SECURITY.md` and related decisions.

## 13. Dependency and Build Security

- Use the approved package manager and lockfile.
- Pin dependencies through the lockfile; avoid unreviewed floating versions.
- Review direct and transitive dependencies before adding them.
- Run dependency vulnerability checks in CI.
- Remove unused dependencies.
- Do not execute arbitrary install scripts or copy unreviewed code into the application.
- Keep TypeScript strict; do not use `any` to bypass API contract validation.
- Do not expose source maps publicly if the deployment threat model or policy disallows them; decide deliberately.
- Build artifacts must not contain secrets.

A dependency scanner is a detection aid, not proof that the application is secure.

### 13.1 Phase F1 Verification & Dependency Exception Status (2026-11-11)

- **Verified Phase F1 Runtime & Code Controls:**
  - `frontend/src/lib/auth/token-store.ts` holds access tokens strictly in memory (`ADR-075`), with zero `localStorage`, `sessionStorage`, or `document.cookie` writes (`smoke.test.tsx`, `api-client.test.ts`).
  - `frontend/src/lib/api/env.ts` and `frontend/.env.example` expose only non-secret public variables (`VITE_API_BASE_URL`, `VITE_APP_ENV`); repository scans confirm zero backend credentials or secrets in `frontend/src/`.
  - `frontend/src/app/errors/RootErrorBoundary.tsx` suppresses raw stack traces and internal error payloads (`resilience.test.tsx`); `Alert` renders children via safe escaped React text (`alert.test.tsx`).
  - `zod` upgraded to `4.6.7` (`ADR-078`) and `vitest` upgraded to `5.1.0` (`ADR-079`) without `npm audit fix --force` or silent `overrides`.
- **Production Dependency Audit (`npm audit --omit=dev`):** **`0` vulnerabilities** (`PASS`, exit `0`).
- **Full Dependency Audit (`npm audit`) — Mandatory Transparency (`ADR-080`):**
  - `npm audit` reports **`7 moderate` advisories** (`0 critical`, `0 high`) on advisory **`GHSA-g3hv-75wg-m249`** (*`minimatch` denial of service via globparts amplification*, affected range `7.0.0 - 11.0.0`).
  - **Dependency path:** `typescript-eslint@8.72.2` (direct devDependency, latest upstream release) → `@typescript-eslint/{eslint-plugin,parser,type-utils,utils,typescript-estree}@8.72.2` → `minimatch@10.2.6`.
  - **Exposure & governance:** Exposed strictly in development/CI ESLint static analysis CLI tooling (`devDependencies`); absent from the Vite production bundle (`dist/`). Because `@typescript-eslint/typescript-estree@8.72.2` constrains `"minimatch": "^10.2.2"` and `10.2.6` is the newest `10.x` release (`11.0.1+` is a major bump), `npm audit fix` (without `--force`) performs zero changes.
  - **Approval status:** **`ACCEPTED` (`ADR-080`, owner approved `2026-11-11`)**. This temporary dev-only risk acceptance permits `minimatch@10.2.6` under `typescript-eslint@8.72.2` without npm `overrides` or `npm audit fix --force` (it is a temporary exception, not a vulnerability fix) and must be revisited when upstream `@typescript-eslint` adopts `minimatch@^11.0.1` and prior to Phase F7/F8 release.
- **Resolved & Implemented Phase F2 Security Controls (`2026-11-11` Local Verification):**
  - `F1-AUD-005` resolved: `resolveApiBaseUrl` validates schemes, production `https:`, embedded credentials, control chars, and rejects unexpected `?query`/`#hash`; `apiRequest` prevents duplicate `/api/v1` prefixes, rejects scheme/`//` paths before `fetch`, normalizes `NETWORK_ERROR` and `INVALID_RESPONSE`, enforces explicit `authMode: "bearer" | "none"`, and captures `X-Request-ID` + `429` retry timing.
  - `AuthProvider.tsx` enforces the 8-step `signIn` flow (`/login` -> token store -> `sessionEpoch` -> `/auth/me`) with dual `authAttemptId` + `sessionEpoch` race protection, `expires_in` timeout expiration, single-flight `401` cleanup, `403` session preservation, local-only logout (`Option B`), and `QueryClient` cancel + synchronous cache clearing.
  - `sanitizeRedirectPath` blocks open redirects (`//`, `\`, schemes, `/login` loops, sensitive query params); `capabilities.ts` narrows `UserResponse.role` via runtime `isUserRole` and fails closed on unknown/inactive roles.
  - Local verification: `87/87` Vitest tests (`22` files), `5/5` mocked Chromium Playwright E2E tests (fresh production `vite preview`), and `npm audit --omit=dev` (`0` vulnerabilities). Live-backend E2E and remote F2 CI remain pending.

## 14. Error and Failure Handling

- Normalize API errors without discarding stable backend error codes.
- Do not show stack traces, SQL errors, filesystem paths, secrets, or internal provider details to end users.
- Show request IDs where available to support investigation.
- Treat `401` as authentication/session failure.
- Treat `403` as authorization failure.
- Treat `409` as a domain/concurrency conflict; refresh authoritative state before retrying.
- Treat `422` as validation failure and map field errors only when the schema is understood.
- For network timeouts on mutations, reconcile server state before resubmission.
- Do not present a failed request as an empty successful result.

## 15. Security Testing Requirements

At minimum, include tests or verification for:

### Authentication
- Protected route is not rendered while session status is unknown.
- Invalid/expired session clears authenticated state.
- `401` does not cause repeated request loops.
- Logout clears in-memory token and authenticated caches.
- No token appears in URL, logs, or persisted browser storage under the approved MVP strategy.

### Authorization
- UI capability helpers match the approved permission matrix.
- Direct navigation to a restricted page does not expose protected data.
- `403` is handled safely.
- Assignment-scoped investigator actions are hidden/disabled appropriately but still rely on backend checks.
- Resolved investigation controls are read-only.

### Browser security
- API text is rendered as text, not executable HTML.
- Untrusted Markdown/HTML is sanitized if rich rendering is introduced.
- External redirect targets are rejected.
- Production security headers are verified.
- Production API requests use HTTPS.
- CORS preflight succeeds only for configured origins and required headers.

### Data handling
- Tokens and sensitive payloads are not sent to telemetry.
- Authenticated cache is cleared on session end.
- Monetary values remain strings at API boundaries.
- Stale AI summary state is visible.
- Evidence is never editable/deletable in the UI.

### Upload
- Oversized file is rejected client-side for usability and server-side authoritatively.
- Invalid CSV responses are safely rendered.
- Timeout recovery reconciles import state before another submission.

## 16. Security Decisions Requiring Approval

These items must be resolved and recorded in `DECISIONS.md` before the corresponding behavior is implemented.

| Decision | Recommendation | Why it matters |
|---|---|---|
| Access-token storage | In-memory for MVP | Avoids persistent browser token storage; requires re-login after reload |
| Refresh tokens | Do not add in MVP without a concrete persistence requirement | Backend currently documents no refresh endpoint/rotation contract |
| Logout | Client-side token removal unless backend revocation is implemented | Stateless JWT is otherwise valid until expiry |
| Cookie-based auth | Defer unless persistent sessions justify coordinated backend changes | Requires CSRF, CORS, cookie, and session design |
| CSP/security headers | Configure at deployment/reverse proxy | Frontend source code alone cannot enforce response headers |
| Third-party telemetry | No sensitive financial or investigation payloads | Prevents data leakage to external processors |
| Service worker/offline cache | Defer for authenticated financial data | Avoids unintended persistence of sensitive responses |

## 17. Contract and Documentation Reconciliation

Before implementation, verify the following against backend code and runtime configuration:

1. Actual JWT signing algorithm and accepted claims.
2. Actual access-token expiration and `expires_in` behavior.
3. Whether `/auth/logout` exists and whether it revokes tokens.
4. Whether any refresh-token endpoint exists.
5. Whether the backend uses cookies anywhere in the authentication flow.
6. Actual CORS settings in development and production.
7. Exact error response schema and `X-Request-ID` behavior.
8. Endpoint-specific role and object-level permission behavior.
9. Whether sensitive API responses set appropriate cache headers.
10. Deployment support for CSP, HSTS, and anti-framing headers.

Do not infer implementation from a recommendation in a design document. If runtime behavior conflicts with documentation, stop and reconcile it.

## 18. Security Definition of Done

The frontend security baseline is acceptable for MVP review when:

- [x] Authentication transport and token storage are explicitly approved in `DECISIONS.md` (ADR-075; in-memory Bearer token + `sessionEpoch` verified in F2 unit and Playwright E2E tests).
- [x] Production dependencies pass `npm audit --omit=dev` (`0` vulnerabilities); dev-only `minimatch@10.2.6` temporary risk acceptance (`ADR-080`) approved by project owner (`2026-11-11`).
- [x] Logout semantics are accurately represented (local-only Option B clearing in-memory token and `QueryClient` cache synchronously with zero server-side JWT revocation claim).
- [x] `/auth/me` establishes current-user context and runtime role narrowing (`isUserRole` / `parseAuthUser` fail closed).
- [x] Protected UI does not render while authentication is unresolved (`ProtectedRoute` / `PublicOnlyRoute` `initializing` loading guard).
- [x] Backend remains authoritative for all permissions (`canViewDatasetImports` vs `canManageDatasets` documented as UI policy only; backend `403` preserves session).
- [ ] Endpoint and object-level authorization behavior is verified across remaining F3–F6 workflows (datasets upload/recovery, risk models, investigations, evidence, AI summary).
- [x] Tokens and sensitive payloads are absent from URLs, logs, telemetry, and browser persistence in F2 tests (`session-lifecycle.test.tsx`, `auth.spec.ts`).
- [x] XSS-safe rendering and open-redirect rejection (`sanitizeRedirectPath`) are implemented for F2 auth/shell views.
- [ ] CORS and HTTPS are verified against a live deployed/staging backend (local mocked E2E and `env.ts` production HTTPS validation complete; live-backend E2E pending).
- [ ] Production security headers are configured at the hosting layer.
- [ ] Upload and evidence content are handled as untrusted input (Phase F4/F6).
- [ ] AI output is rendered with provenance and uncertainty preserved (Phase F6).
- [x] Authenticated caches are cleared on session end (`void queryClient.cancelQueries()` + synchronous `queryClient.clear()`).
- [x] F2 security unit/integration/mocked-E2E tests pass and unresolved risks/verification items are documented (remote F2 CI & live-backend E2E pending).

## 19. Final Security Principle

FinSignal handles financial transactions, risk intelligence, evidence, and human investigation outcomes. The frontend is a presentation and workflow client—not a trusted authority.

**Never rely on the browser to enforce a permission, validate a financial decision, preserve evidence integrity, or establish the truth of an investigation. The backend must enforce the rule, and the frontend must present the result faithfully.**
