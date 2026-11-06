# FinSignal — Frontend Testing Strategy

**Document:** `FRONTEND_TESTING_STRATEGY.md`  
**Product:** FinSignal — Financial Transaction Intelligence & Investigation Platform  
**Version:** 1.0  
**Status:** Draft — align test coverage with verified API contracts and approved frontend decisions  
**Scope:** Automated and manual testing of the React/TypeScript frontend

---

## 1. Purpose

This document defines the frontend testing strategy for FinSignal. It establishes the testing layers, quality gates, test data principles, critical workflows, security checks, and release criteria required to deliver a reliable financial investigation interface.

The frontend is a client of the backend. Tests must verify that it presents backend-authoritative data and state accurately; they must not encode frontend implementations of financial calculations or backend business rules.

This document complements:

- `FRONTEND_PRD.md`
- `FRONTEND_TRD.md`
- `FRONTEND_ARCHITECTURE.md`
- `FRONTEND_API_INTEGRATION.md`
- `FRONTEND_SECURITY.md`
- `TESTING_STRATEGY.md`
- `API_GUIDELINES.md`

## 2. Testing Principles

1. Test observable user behavior rather than private implementation details.
2. Verify the frontend against the documented and runtime-verified API contract.
3. Keep unit tests fast and deterministic.
4. Use mocked network responses for isolated frontend tests, but retain a smaller set of real backend integration tests.
5. Never use mock data to conceal a backend/API contract mismatch.
6. Test loading, empty, error, unauthorized, forbidden, stale, and conflict states—not only successful rendering.
7. Preserve financial precision, currency, timestamp, and provenance semantics.
8. Treat role-aware UI as presentation behavior; verify backend authorization separately.
9. Use deterministic fixtures and avoid dependence on production data.
10. Make accessibility and security part of normal testing, not a final visual checklist.

## 3. Testing Scope

### 3.1 In scope

- Shared UI components and design-system behavior.
- Routing and protected-route behavior.
- Authentication/session lifecycle as approved in `FRONTEND_SECURITY.md`.
- API client request construction and error normalization.
- Feature-level query and mutation behavior.
- Transaction, analytics, dataset, risk, and investigation workflows.
- Evidence and AI summary presentation.
- Role-aware navigation and action availability.
- Financial value and date/time formatting.
- Responsive behavior and accessibility.
- Browser security controls implemented by the frontend.
- Build, lint, type-check, and deployment configuration.

### 3.2 Out of scope for frontend unit tests

- Re-testing backend fraud/risk algorithms.
- Recomputing or validating backend financial aggregates in browser code.
- Proving database transaction isolation or ledger correctness.
- Proving backend RBAC using only hidden/disabled frontend controls.
- Validating LLM provider behavior or prompt security from the browser.
- Replacing backend API, integration, security, or performance testing.

These remain backend or system-level responsibilities. The frontend should test that it handles their API outputs and failures correctly.

## 4. Test Pyramid and Tooling

The proposed frontend stack identifies these tools; confirm the final dependency choices in `FRONTEND_TRD.md` and `DECISIONS.md`.

| Layer | Proposed tools | Purpose |
|---|---|---|
| Static checks | TypeScript, ESLint, Prettier | Type safety, code quality, consistent formatting |
| Unit tests | Vitest | Pure utilities, formatters, permission helpers, reducers |
| Component tests | Vitest, React Testing Library, user-event | Accessible user interactions and component states |
| API mocking | MSW | Deterministic HTTP behavior at the network boundary |
| Contract checks | OpenAPI-generated types and contract verification | Detect frontend/backend schema drift |
| End-to-end | Playwright | Critical workflows in a real browser |
| Accessibility | axe integration plus keyboard/manual checks | Automated and human accessibility validation |

Do not add every tool automatically. Use the approved stack and avoid overlapping tools without a clear benefit.

### 4.1 Testing balance

- Many unit tests for deterministic logic and formatters.
- A substantial component/integration layer for feature workflows.
- A smaller number of end-to-end tests for high-value user journeys.
- Contract tests at API boundaries.
- Manual exploratory checks for visual clarity, keyboard use, and complex investigation workflows.

The exact test count is not a quality target. Coverage of meaningful behavior is more important than maximizing line coverage.

## 5. Test Environments

### 5.1 Local development

- Run frontend tests without requiring production services.
- Use MSW for isolated API-dependent component tests.
- Use deterministic fixtures.
- Allow a separate local integration mode against a developer backend.
- Never point automated destructive tests at shared or production data.

### 5.2 CI

CI should run:

1. Dependency installation from the committed lockfile.
2. Formatting check.
3. ESLint.
4. TypeScript type-check.
5. Unit and component tests.
6. Contract/type-generation consistency check, where configured.
7. Production build.
8. End-to-end smoke tests against a controlled test environment.
9. Dependency/security checks according to repository policy.

Fail the pipeline when a required quality gate fails.

### 5.3 Staging

Staging should use:

- A frontend build matching the candidate release.
- A backend environment with a compatible API version.
- Synthetic or approved test data.
- Test accounts for each role.
- No production credentials or real sensitive transaction data unless explicitly approved.

## 6. Test Data and Fixtures

### 6.1 Fixture requirements

Create reusable fixtures for:

- `ADMIN`, `ANALYST`, and `INVESTIGATOR` identities.
- Active and inactive user states where supported.
- Transactions with debit and credit directions.
- Multiple currencies.
- Decimal amounts with trailing zeros and large values.
- Transactions with and without risk analysis.
- Risk results across documented levels.
- Dataset imports in pending, processing, completed, failed, and duplicate states where those states exist in the API contract.
- Investigations in `OPEN`, `UNDER_REVIEW`, and `RESOLVED`.
- Investigations assigned, unassigned, and assigned to another investigator.
- Evidence entries from supported evidence/source combinations.
- AI summaries in documented pending, completed, and failed states, plus stale summaries.
- Empty and paginated collection responses.
- API errors including `401`, `403`, `404`, `409`, `413`, `422`, `429`, and server failures.

Do not invent enum values or fields. Fixtures must be derived from generated API types or verified backend schemas.

### 6.2 Synthetic data

- Use synthetic names, accounts, identifiers, merchants, and transaction values.
- Do not copy production records into test fixtures.
- Keep fixtures small and purpose-built.
- Include edge cases that expose formatting and state bugs.
- Keep test IDs deterministic where practical.

### 6.3 Financial fixture edge cases

Include values such as:

```json
{
  "amount": "0.10",
  "currency": "INR"
}
```

```json
{
  "amount": "1250.50",
  "currency": "INR"
}
```

```json
{
  "amount": "999999999999.99",
  "currency": "INR"
}
```

These are formatting test values, not assumptions about backend validation limits.

Verify that the frontend does not convert decimal strings to binary floating-point numbers for authoritative display or calculations.

## 7. Unit Testing

Unit tests should cover pure functions and isolated logic.

### 7.1 Formatting utilities

Test:

- Monetary string formatting without precision loss.
- Currency code display.
- Negative, zero, and large monetary values.
- Missing or unsupported currency behavior.
- ISO-8601 timestamp parsing and display.
- Explicit timezone conversion.
- Invalid timestamp fallback.
- Date-range query serialization for half-open intervals where required.
- Risk-level label and semantic style mapping.
- Investigation status, priority, and resolution labels.
- File-size display and validation.

Do not test a frontend implementation of a backend financial formula if the frontend must not own that calculation.

### 7.2 Permission helpers

Test:

- Role-to-capability presentation mapping.
- Assignment-scoped action visibility.
- Resolved-case read-only behavior.
- Unknown role or missing identity fails closed.
- Missing assignment context does not grant investigator write controls.

These tests verify presentation logic only. They do not prove backend authorization.

### 7.3 API client

Test:

- Base URL composition without duplicate `/api/v1`.
- JSON request headers and serialization.
- Bearer header injection through the approved session adapter.
- Multipart upload without manually setting the boundary header.
- `204 No Content` handling.
- Valid JSON response parsing.
- Empty or malformed error body handling.
- Stable backend error code preservation.
- Request ID extraction using the verified transport.
- `AbortSignal` propagation.
- No token or sensitive payload logging.
- Correct handling of `401`, `403`, `409`, `422`, `429`, and server errors.

### 7.4 Query keys and cache helpers

If TanStack Query is approved, verify that query keys distinguish all response-affecting inputs:

- Filters and search terms.
- Pagination.
- Sort field and order.
- Namespace.
- Currency.
- Time range and timezone.
- Resource ID.

Verify that credentials never appear in query keys.

## 8. Component and Feature Integration Testing

Use React Testing Library to test components through accessible user behavior. Use MSW to simulate API responses at the network boundary.

For each feature, cover the following states where applicable:

- Initial loading.
- Successful populated state.
- Empty state.
- Validation failure.
- Network/server failure.
- Unauthorized (`401`).
- Forbidden (`403`).
- Not found (`404`).
- Conflict (`409`).
- Stale data.
- Retry or refresh behavior.
- Keyboard interaction and focus behavior.

### 8.1 Authentication

Tests:

- Login form accepts valid input and submits once.
- Invalid credentials display a safe error.
- Password is not echoed or logged.
- Successful login establishes the session only after current-user validation.
- Failed `/auth/me` does not render protected content.
- `401` expires the session once without redirect loops.
- Logout clears in-memory session and authenticated query data.
- Reload behavior matches the approved token-storage decision.

### 8.2 Application shell and navigation

Tests:

- Navigation renders according to current-user context.
- Unknown session state does not expose protected navigation.
- Direct navigation to a protected route is handled safely.
- Unknown route displays a not-found page.
- Navigation remains usable with keyboard only.
- Responsive navigation opens and closes correctly.
- Active navigation state reflects the current route.

### 8.3 Dashboard and analytics

Tests:

- Overview cards render backend-returned values.
- Trend/category/merchant charts map API data correctly.
- Empty analytics response is distinct from failed request.
- Date range, namespace, currency, and timezone parameters serialize correctly.
- Filter changes trigger the correct query.
- Stale data is not mislabeled as current if the API exposes freshness metadata.
- Chart legends, labels, and accessible summaries are available.
- The frontend does not recompute aggregate totals from transaction rows.

### 8.4 Transactions

Tests:

- Transaction list supports documented filters, sorting, and pagination.
- Changing a filter resets pagination where the UX contract requires it.
- Transaction detail displays raw transaction facts faithfully.
- Decimal strings preserve precision and trailing zeros as specified by display rules.
- Missing risk analysis is not shown as low risk.
- Risk result metadata and risk factors are displayed only when returned.
- Risk analysis action handles role/model restrictions and conflicts.
- A failed risk request does not replace a previous valid result with fabricated data.

### 8.5 Dataset imports

Tests:

- File selection and client-side size feedback.
- Correct multipart field names.
- No manual multipart `Content-Type` header.
- Upload progress behavior only if supported by the selected transport.
- New import response renders row counts and status.
- Duplicate completed import is explained using `is_duplicate`.
- `IMPORT_IN_PROGRESS` conflict is handled without repeated submission.
- `413` and `422` responses render safely.
- Import detail displays backend validation errors.
- Recovery requires the original file and handles hash mismatch safely.
- A timeout triggers status reconciliation before another upload attempt.

### 8.6 Investigations

Tests:

- Queue filters and pagination use documented parameters.
- Empty queue and failed queue request are distinct.
- Create flow sends only supported fields.
- Workspace renders primary and related transaction context.
- Assignment controls match approved role and assignment rules.
- Invalid state transition (`409`) refreshes the authoritative case.
- Resolved case renders read-only.
- Resolution requires a non-empty explanation in the UI and is validated by the backend.
- Related transaction linking respects API outcomes; frontend does not perform recursive relationship expansion.
- Evidence list uses documented ordering/pagination.
- Evidence attachment is append-only in the UI.
- Evidence payload validation errors are mapped safely.

### 8.7 AI investigation assistant

Tests:

- Summary sections remain distinct.
- Observed facts are not merged into interpretations.
- Derived signals remain distinguishable from raw facts.
- Uncertainties and limitations are visible.
- Evidence references are linked only when resolvable.
- Stale summaries display a stale indicator.
- Failed generation displays a safe failure state.
- Analysts see read-only access if the backend permission contract confirms it.
- Unauthorized users cannot generate through the UI; backend `403` is still handled.
- The UI never converts AI output into an investigation resolution.

## 9. API Contract Testing

### 9.1 OpenAPI source

Generate frontend types from the verified FastAPI OpenAPI document. Type generation is a compile-time aid; it does not prove runtime responses conform.

### 9.2 Contract verification

For each MVP endpoint, verify:

- HTTP method and path.
- Path parameter names and formats.
- Query parameter names, defaults, and allowed values.
- Request body schema.
- Response schema and status codes.
- Multipart field names and constraints.
- Authentication requirements.
- Role/object-level authorization behavior.
- Error schema.

### 9.3 Drift detection

When backend OpenAPI changes:

1. Regenerate frontend API types.
2. Review the diff.
3. Identify breaking and additive changes.
4. Update API modules and fixtures.
5. Update affected component and E2E tests.
6. Confirm the frontend does not silently rely on removed fields or enum values.

Do not manually patch generated types to conceal a backend contract change.

## 10. End-to-End Testing

Playwright tests should focus on a small number of critical, representative user journeys.

### 10.1 Core smoke journeys

1. Sign in as an authorized user and load the dashboard.
2. Open a transaction list, apply a supported filter, and view transaction details.
3. View an existing risk result and distinguish “no result” from low risk.
4. Upload a valid synthetic dataset and inspect import status.
5. Create an investigation from a transaction.
6. Open the investigation workspace and inspect linked transaction context.
7. Add evidence as an authorized investigator.
8. Generate or view an AI summary according to role permissions.
9. Resolve an eligible investigation with required resolution notes.
10. Sign out and verify protected content is no longer accessible.

Only include journeys supported by the actual backend contract and enabled product scope.

### 10.2 Role scenarios

At minimum, test:

- ADMIN: privileged workflow.
- ANALYST: read/analysis workflow and restrictions on write operations.
- INVESTIGATOR: assignment-scoped investigation workflow.

Use backend-issued test credentials in a controlled environment. Do not mock authorization in the only test of a protected workflow.

### 10.3 E2E data isolation

- Use dedicated test accounts and synthetic data.
- Ensure test setup and cleanup are deterministic.
- Avoid tests that depend on ordering or state left by another test.
- Do not run destructive workflows against production.
- Do not store credentials in the repository or Playwright traces.

## 11. Accessibility Testing

Target WCAG 2.2 AA as specified by the frontend product/design requirements.

Automated checks should cover:

- Accessible names and roles.
- Form labels and validation association.
- Heading hierarchy.
- Color contrast.
- Keyboard focus visibility.
- Dialog semantics and focus management.
- Table headers and relationships.
- Chart accessible summaries or equivalent data tables.
- Status messages announced appropriately.
- No color-only risk/status communication.

Manual checks should cover:

- Full keyboard-only navigation.
- Focus order and focus restoration.
- Screen-reader review of critical workflows.
- Zoom and reflow at narrow widths.
- Dense transaction and evidence table usability.
- Modal/dialog escape and focus behavior.

Automated accessibility scans do not prove WCAG conformance.

## 12. Responsive and Visual Testing

Test at representative widths, including:

- Wide desktop investigation workspace.
- Standard laptop dashboard and tables.
- Tablet navigation and investigation layout.
- Narrow mobile transaction and case views.

Verify:

- No unintended horizontal page overflow.
- Critical information remains available on narrow screens.
- Dense tables use a deliberate strategy (responsive columns, horizontal scrolling, or alternate layout).
- Charts remain interpretable.
- Dialogs and forms fit the viewport.
- Risk/status labels remain readable and explicit.

Visual regression snapshots may be used for stable high-value pages, but should not become brittle tests of every pixel. Review snapshots when design tokens or component behavior intentionally changes.

## 13. Performance Testing

Frontend performance checks should focus on user-perceived behavior and regression detection.

Measure:

- Initial application load.
- Route transitions.
- Dashboard data loading.
- Transaction table rendering at realistic page sizes.
- Large evidence/history lists.
- Chart rendering.
- Upload interaction responsiveness.

Requirements:

- Use server pagination rather than downloading unbounded transaction history.
- Avoid rendering all rows when a large result set is returned.
- Avoid duplicate requests caused by component lifecycle or query configuration.
- Cancel obsolete reads where appropriate.
- Lazy-load non-critical routes and heavy chart modules where beneficial.
- Do not sacrifice financial correctness or accessibility for performance.

Set numeric budgets only after establishing a baseline on the intended deployment environment and representative hardware.

## 14. Security Testing

Security test coverage must align with `FRONTEND_SECURITY.md`.

Verify:

- Tokens do not appear in URLs, logs, query keys, or unapproved persistent storage.
- API-provided text and AI output are rendered safely.
- External redirect targets are rejected.
- `401` and `403` are handled distinctly.
- Authenticated caches are cleared on logout/session expiry.
- Production requests use HTTPS.
- CORS and security headers are verified in deployment tests.
- No secrets are present in built assets.
- File names and CSV validation messages are rendered as untrusted text.
- No client-side permission helper is treated as a security boundary.

## 15. Test Naming and Organization

Suggested structure:

```text
src/
  features/
    transactions/
      api/
      components/
      hooks/
      pages/
      __tests__/
        transactions-api.test.ts
        transaction-list.test.tsx
        transaction-detail.test.tsx
  shared/
    api/
      __tests__/
    lib/
      __tests__/

tests/
  e2e/
    auth.spec.ts
    transactions.spec.ts
    dataset-import.spec.ts
    investigations.spec.ts
```

Conventions:

- Name tests by observable behavior.
- Keep fixtures close to the feature or in a shared test-fixture directory.
- Avoid giant fixtures that combine unrelated domain states.
- Keep MSW handlers reusable and explicit.
- Reset handlers, query clients, and test state between tests.
- Do not use arbitrary sleeps in E2E tests; wait for observable UI or network conditions.

## 16. Coverage and Quality Gates

Coverage is a diagnostic, not the sole quality metric.

Suggested initial quality gates:

- TypeScript strict type-check passes.
- ESLint passes.
- Production build succeeds.
- All unit/component tests pass.
- Critical API client and financial-formatting utilities have strong branch coverage.
- Critical authentication, transaction, dataset, and investigation journeys have E2E coverage.
- No known high-severity dependency vulnerability is accepted without documented risk approval.
- Accessibility checks have no unresolved critical violations in key workflows.
- No test relies on production data or secrets.

Set a numeric overall coverage threshold only after the initial implementation establishes a meaningful baseline. Avoid optimizing for a percentage at the expense of behavior coverage.

## 17. Defect Severity and Release Blocking

| Severity | Example | Release handling |
|---|---|---|
| Critical | Unauthorized access to financial/investigation data; token exposure; wrong human resolution submitted | Block release |
| High | Incorrect transaction amount/currency display; risk level misrepresented; evidence mutation exposed; core workflow unusable | Block release |
| Medium | Important workflow degraded with a safe workaround; pagination/filter bug with limited scope | Fix before release where feasible; otherwise document and approve |
| Low | Minor visual inconsistency or non-blocking usability issue | May defer with owner and target milestone |

Any defect that confuses model risk with a confirmed fraud decision is at least High severity.

## 18. Definition of Done

A frontend feature is complete when:

- [ ] API behavior is based on verified OpenAPI/runtime contract.
- [ ] Unit tests cover its deterministic logic.
- [ ] Component tests cover success, loading, empty, and relevant failure states.
- [ ] Authorization presentation matches the approved capability rules.
- [ ] Backend authorization failures are handled safely.
- [ ] Financial values, timestamps, and provenance are preserved.
- [ ] Accessibility requirements are checked.
- [ ] Responsive behavior is reviewed at relevant widths.
- [ ] Security-sensitive behavior is covered.
- [ ] No secrets or sensitive test data are committed.
- [ ] Lint, type-check, tests, and production build pass.
- [ ] Any known gap or deferred test is documented.

## 19. MVP Release Test Checklist

### Automated

- [ ] Formatting and lint checks pass.
- [ ] TypeScript type-check passes.
- [ ] Unit and component suites pass.
- [ ] API client and contract checks pass.
- [ ] Critical E2E smoke journeys pass.
- [ ] Production build succeeds.
- [ ] Dependency/security checks pass according to policy.

### Manual

- [ ] ADMIN, ANALYST, and INVESTIGATOR workflows reviewed.
- [ ] Authentication expiration and logout reviewed.
- [ ] Transaction precision and currency display reviewed.
- [ ] Risk result semantics reviewed.
- [ ] Dataset import and recovery reviewed.
- [ ] Investigation assignment and resolution reviewed.
- [ ] Evidence immutability reviewed.
- [ ] AI summary provenance, stale state, and limitations reviewed.
- [ ] Keyboard navigation and screen-reader behavior reviewed on critical flows.
- [ ] Staging deployment headers, HTTPS, and CORS verified.

## 20. Final Testing Principle

FinSignal's frontend must not merely look correct in a successful demo. It must behave correctly when the API is slow, unavailable, unauthorized, stale, conflicting, or returns incomplete data.

**Test the boundaries and failure states that protect financial meaning, evidence integrity, and human investigation decisions—not just whether a page renders.**
