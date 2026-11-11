# FinSignal — Frontend Design System

**Product:** FinSignal — Financial Transaction Intelligence &
Investigation Platform  
**Document:** Frontend Design System (`FRONTEND_DESIGN.md`)  
**Version:** 1.0.1  
**Status:** Baseline approved and partially implemented (Phase F1 Tokens & 10 UI Primitives)  
**Design direction:** Coinbase-inspired financial clarity + IBM-inspired
enterprise structure  
**Last Updated:** 2026-11-11

------------------------------------------------------------------------

## 1. Purpose

This document is the visual and interaction source of truth for the
FinSignal frontend.

It defines how the application should look, feel, and communicate
information across dashboards, transaction analysis, risk monitoring,
dataset management, and investigation workflows.

It is intended for frontend developers and AI coding agents. It should
be consulted before creating or modifying UI components.

This is a **FinSignal-specific adaptation**, not a copy of Coinbase or
IBM branding.

### 1.1 Design inspiration

- **Coinbase:** restrained blue-led financial identity, neutral
  surfaces, clear numerical presentation, and disciplined use of
  semantic color.
- **IBM / Carbon-style enterprise patterns:** structured layouts,
  predictable navigation, compact information hierarchy, precise tables,
  and functional controls.

The inspiration is used selectively. FinSignal is an investigation and
intelligence workspace, not a cryptocurrency exchange, marketing
website, or trading terminal.

### 1.2 Product character

FinSignal should feel:

- Trustworthy and professional
- Analytical rather than promotional
- Calm under high information density
- Precise with financial and risk information
- Explainable and auditable
- Efficient for repeated investigator workflows

The interface should prioritize clarity and decision support over
decoration.

------------------------------------------------------------------------

## 2. Core Design Principles

1.  **Evidence before decoration.** Visual emphasis must help users find
    relevant facts, risk signals, and investigation context.
2.  **Clear information hierarchy.** Page title, filters, summary
    metrics, primary data, and secondary context must be visually
    distinguishable.
3.  **Server-authoritative intelligence.** The frontend presents
    backend-provided financial calculations, analytics, risk scores, and
    investigation state. It must not independently calculate or
    reinterpret authoritative values.
4.  **Separate facts from interpretation.** Raw transaction facts,
    derived risk signals, AI-generated interpretations, and human
    decisions must never look like the same type of information.
5.  **Color is semantic.** Blue indicates primary interaction and
    navigation. Risk colors communicate severity or state only where
    appropriate.
6.  **Dense, not cramped.** Tables and investigation workspaces should
    support substantial information without tiny text or excessive card
    decoration.
7.  **Consistent interaction.** Similar actions, filters, forms, and
    status indicators must behave and look consistently across features.
8.  **Accessible by default.** Color is never the only carrier of
    meaning. Keyboard operation, visible focus, sufficient contrast, and
    readable text are required.
9.  **Progressive disclosure.** Show the information needed for the
    current task first; place detailed metadata and secondary evidence
    behind expandable sections or detail views.
10. **No false certainty.** Model outputs and AI summaries must
    communicate uncertainty and must not visually imply a final fraud
    verdict.

------------------------------------------------------------------------

## 3. Visual Theme & Atmosphere

### 3.1 Overall theme

Use a **light-first enterprise application shell**:

- Light neutral page canvas
- White content surfaces
- Cobalt-blue primary actions and selected navigation
- Near-black primary text
- Muted gray secondary text
- Fine neutral borders
- Minimal, subtle elevation
- Compact but comfortable spacing

A dark sidebar is permitted as a restrained navigation treatment, but
the default content workspace remains light. Do not turn the entire
application into a dark trading terminal.

### 3.2 Visual restraint

Avoid:

- Large marketing-style hero sections inside the authenticated
  application
- Decorative gradients behind operational data
- Neon colors and glow effects
- Glassmorphism
- Excessive shadows
- Oversized rounded cards
- Unnecessary animations
- Large illustrations that displace operational content
- Arbitrary colored cards for every metric

Use whitespace to establish grouping, not to create large empty areas
that reduce useful data density.

------------------------------------------------------------------------

## 4. Color Palette & Roles

The palette adapts Coinbase’s blue-and-neutral approach to an enterprise
investigation product. The values below are FinSignal design tokens;
they are not a claim that every value is an official Coinbase token.

### 4.1 Brand and interaction

| Token             |       Hex | Usage                                               |
|-------------------|----------:|-----------------------------------------------------|
| `color-brand-700` | `#0052FF` | Primary actions, active links, selected navigation  |
| `color-brand-800` | `#003ECC` | Hover/pressed primary action                        |
| `color-brand-100` | `#EAF0FF` | Selected navigation background, subtle blue surface |
| `color-brand-50`  | `#F5F8FF` | Very subtle informational background                |
| `color-focus`     | `#2563EB` | Visible keyboard focus ring                         |

Blue is the primary interaction color. Do not use it as a generic
highlight for every data point.

### 4.2 Neutral surfaces

| Token                  |                      Hex | Usage                                         |
|------------------------|-------------------------:|-----------------------------------------------|
| `color-canvas`         |                `#F7F8FA` | Application page background                   |
| `color-surface`        |                `#FFFFFF` | Cards, tables, dialogs, forms                 |
| `color-surface-subtle` |                `#F3F4F6` | Secondary panels and table header backgrounds |
| `color-surface-hover`  |                `#F8FAFC` | Hovered rows and interactive surfaces         |
| `color-border`         |                `#E2E5EA` | Default dividers and borders                  |
| `color-border-strong`  |                `#CBD1D9` | Emphasized boundaries                         |
| `color-overlay`        | `rgba(15, 23, 42, 0.48)` | Modal backdrop                                |

### 4.3 Text

| Token                  |       Hex | Usage                                     |
|------------------------|----------:|-------------------------------------------|
| `color-text-primary`   | `#111827` | Headings, primary values, body text       |
| `color-text-secondary` | `#4B5563` | Supporting text, descriptions             |
| `color-text-muted`     | `#6B7280` | Metadata, timestamps, helper text         |
| `color-text-disabled`  | `#9CA3AF` | Disabled controls only                    |
| `color-text-inverse`   | `#FFFFFF` | Text on dark surfaces and primary buttons |

Do not use muted text for essential transaction values, risk labels, or
required form instructions.

### 4.4 Risk and status semantics

| Token                 |       Hex | Meaning                                     |
|-----------------------|----------:|---------------------------------------------|
| `color-risk-critical` | `#B42318` | Critical severity                           |
| `color-risk-high`     | `#D92D20` | High severity                               |
| `color-risk-medium`   | `#B54708` | Medium severity                             |
| `color-risk-low`      | `#027A48` | Low severity                                |
| `color-info`          | `#175CD3` | Informational state                         |
| `color-success`       | `#067647` | Successful operation / confirmed completion |
| `color-warning`       | `#B54708` | Caution or action required                  |
| `color-danger`        | `#B42318` | Destructive action or failure               |

**Important semantic rules:**

- Risk severity must be accompanied by a readable label, such as `HIGH`
  or `MEDIUM`; color alone is insufficient.
- Do not use green and red as generic positive/negative financial
  movement indicators. FinSignal is not a trading product.
- A low-risk score does not mean a transaction is proven legitimate.
- A high-risk score does not mean fraud is confirmed.
- Investigation resolution and model risk level are separate concepts
  and must have separate labels and visual treatments.
- Use neutral styling for unknown, unavailable, or not-yet-analyzed
  values. Never silently map missing data to low risk.

### 4.5 Color usage rules

- Reserve strong blue for primary actions and selected states.
- Use risk colors only for risk-related meaning, warnings, and relevant
  statuses.
- Use red-filled surfaces sparingly; reserve them for critical warnings
  or destructive confirmations.
- Avoid coloring entire dashboard cards by risk category. Prefer a
  neutral card with a colored badge, icon, or narrow accent.
- Charts should use a restrained palette and highlight only the series
  or data point relevant to the user’s current task.

------------------------------------------------------------------------

## 5. Typography Rules

### 5.1 Font families

Preferred stack:

``` css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

Use a clean sans-serif for interface text. Use a tabular-numeral or
monospace treatment for identifiers and selected numerical fields.

Suggested numeric stack:

``` css
font-family:
  "IBM Plex Mono",
  "SFMono-Regular",
  Consolas,
  "Liberation Mono",
  monospace;
font-variant-numeric: tabular-nums;
```

Do not require proprietary Coinbase fonts. Use fonts that can be legally
and reliably loaded by the application, with sensible system fallbacks.

### 5.2 Type scale

| Style           | Size / line height |  Weight | Usage                              |
|-----------------|--------------------|--------:|------------------------------------|
| Page title      | 24px / 32px        |     600 | Main page heading                  |
| Section title   | 18px / 26px        |     600 | Major content sections             |
| Panel title     | 15px / 22px        |     600 | Cards and workspace panels         |
| Body            | 14px / 21px        |     400 | Default application text           |
| Body strong     | 14px / 21px        |     600 | Emphasized body text               |
| Supporting      | 13px / 19px        |     400 | Descriptions and secondary content |
| Caption         | 12px / 16px        | 400–500 | Metadata and helper text           |
| Table header    | 12px / 16px        |     600 | Column labels                      |
| KPI value       | 24–30px / 32–36px  |     600 | Important summary values           |
| Financial value | 13–14px / 20px     |     500 | Amounts and numeric columns        |
| Identifier      | 12–13px / 18px     |     500 | UUID fragments, references, codes  |

Avoid using very large display typography in authenticated operational
pages.

### 5.3 Numerical and financial typography

- Use tabular numerals for amounts, scores, counts, and timestamps so
  columns align visually.
- Keep transaction identifiers and technical references visually
  distinct from monetary amounts.
- Align numerical table columns consistently, generally to the right.
- Preserve the currency code or symbol with the amount.
- Do not truncate monetary values in a way that hides their magnitude or
  precision.
- Do not convert authoritative decimal strings to JavaScript
  floating-point values for calculations. The frontend is a presentation
  layer; authoritative arithmetic belongs to the backend.
- Use the API’s supplied precision and formatting contract. Do not
  invent additional rounding rules.

### 5.4 Text hierarchy

A typical page should follow:

1.  Page title
2.  One-sentence page context or description, if needed
3.  Primary actions
4.  Filters or scope controls
5.  Summary metrics, when useful
6.  Main table, chart, or workflow content
7.  Supporting details and metadata

------------------------------------------------------------------------

## 6. Layout Principles

### 6.1 Application shell

Use a persistent application shell for authenticated pages.

Recommended desktop structure:

``` text
+--------------------------------------------------------------+
| Sidebar       | Top bar: breadcrumb / search / user menu      |
|               +----------------------------------------------+
| Overview      | Page title                       Primary CTA  |
| Transactions  | Description / context                         |
| Accounts      +----------------------------------------------+
| Risk          | Filters / tabs / date range                    |
| Investigations+----------------------------------------------+
| Datasets      | Main content                                   |
| Analytics     |                                                |
| Audit         |                                                |
| Admin         |                                                |
+--------------------------------------------------------------+
```

The exact navigation items must reflect implemented backend capabilities
and the user’s role. Do not expose dead links or placeholder modules as
if they were functional.

### 6.2 Sidebar

- Desktop width: approximately 240–256px expanded.
- Collapsed desktop width: approximately 64–72px, if collapse behavior
  is implemented.
- Use a clear product mark and product name.
- Group navigation by operational task rather than backend module names.
- Show the active route with a restrained blue background or left
  indicator and a readable label.
- Use icons consistently and always retain accessible labels.
- Place account/profile actions and sign-out in a predictable lower or
  top-bar location.
- Role-based visibility is a usability feature only; the backend remains
  the authorization authority.

### 6.3 Top bar

- Approximate height: 56–64px.
- Keep it visually quiet.
- Include breadcrumbs where they improve orientation.
- Include global search only if a real search capability exists.
- Include user identity/menu and relevant session actions.
- Avoid decorative notification icons without a working notification
  feature.

### 6.4 Main content

- Desktop page padding: 24–32px.
- Tablet page padding: 20–24px.
- Mobile page padding: 16px.
- Use a consistent content grid and aligned page edges.
- Prefer a full-width workspace for data tables and investigation
  details.
- Use a narrower reading width for long explanatory content and AI
  summaries.
- Do not force every page into the same card grid; choose layout based
  on the task.

### 6.5 Cards and panels

- Cards are for grouping related information, not for wrapping every
  individual field.
- Use white surfaces on the light canvas.
- Use a 1px neutral border as the default boundary.
- Use subtle shadow only for overlays or surfaces that need elevation.
- Use compact corner radii: 8px for controls and small panels; 10–12px
  for larger panels.
- Avoid 24px rounded cards and pill-shaped controls as a universal rule.
- Keep card padding consistent, typically 16–20px.

### 6.6 Spacing scale

Use a 4px base scale:

| Token      | Value |
|------------|------:|
| `space-1`  |   4px |
| `space-2`  |   8px |
| `space-3`  |  12px |
| `space-4`  |  16px |
| `space-5`  |  20px |
| `space-6`  |  24px |
| `space-8`  |  32px |
| `space-10` |  40px |
| `space-12` |  48px |

Use spacing consistently. Do not introduce arbitrary one-off values
without a clear layout reason.

------------------------------------------------------------------------

## 7. Component Styling

### 7.1 Buttons

Use compact, clear rectangular buttons with modest corner radii.

| Variant   | Appearance                            | Usage                                            |
|-----------|---------------------------------------|--------------------------------------------------|
| Primary   | Brand blue fill, white text           | Main action on a page                            |
| Secondary | White or subtle neutral fill, border  | Secondary actions                                |
| Tertiary  | Text or subtle background             | Low-emphasis actions                             |
| Danger    | Red fill or red text with clear label | Destructive actions                              |
| Icon-only | Neutral surface or transparent        | Only for familiar actions with accessible labels |

Rules:

- Default height: 36–40px.
- Primary/high-priority actions may use 40–44px.
- Use sentence case labels and action verbs: `Create investigation`,
  `Run analysis`, `Upload dataset`.
- Do not use pill buttons as the default.
- Avoid multiple competing primary buttons in one view.
- Destructive actions require clear wording and confirmation when
  consequential.
- Disabled controls must communicate why the action is unavailable where
  practical.

### 7.2 Inputs and forms

- Default control height: 36–40px.
- Use persistent labels above inputs; placeholders are examples, not
  labels.
- Show required and optional fields clearly.
- Put validation messages close to the relevant field.
- Preserve entered values when validation fails.
- Explain accepted file types, maximum size, and other upload
  restrictions before upload.
- Do not rely on color alone to indicate invalid fields.
- Use a visible focus ring.
- Distinguish read-only values from editable controls.

#### Implemented `Input` state styling (`src/components/ui/Input.tsx`)

Because the class joiner (`cn`) concatenates strings without utility deduplication, `Input` emits mutually exclusive foreground, surface, and border token classes per state (verified via compiled stylesheet inspection and Chromium computed styles):

| State | Foreground | Surface / Background | Border | Additional Rules / ARIA |
|---|---|---|---|---|
| **Normal** | `text-text-primary` (`#111827`) | `bg-surface` (`#FFFFFF`) | `border-border-strong` (`#CBD1D9`) | Editable default |
| **Disabled** | `text-text-disabled` (`#9CA3AF`) | `bg-surface-subtle` (`#F3F4F6`) | `border-border` (`#E2E5EA`) | `cursor-not-allowed`, `opacity-75`; takes visual precedence over `readOnly`; never emits `text-text-primary` |
| **Read-only** | `text-text-secondary` (`#4B5563`) | `bg-surface-subtle` (`#F3F4F6`) | `border-border` (`#E2E5EA`) | `readOnly` HTML attribute preserved; editable-surface border suppressed |
| **Error / Invalid** | Preserves active state foreground (`text-text-primary`, `text-text-secondary`, or `text-text-disabled`) | Preserves active state surface | `border-danger` (`#B42318`) | Sets `aria-invalid="true"`, renders inline error icon + text, and associates hint/error via `aria-describedby` |

### 7.3 Tables

Tables are a primary interaction pattern in FinSignal.

Use tables for transactions, accounts, risk alerts, investigations,
evidence lists, dataset imports, and audit history where the backend
exposes list data.

Table rules:

- Use a subtle neutral header surface and clear column labels.
- Use thin horizontal row dividers.
- Avoid heavy vertical gridlines unless they materially improve
  comparison.
- Use consistent row heights, generally 44–52px depending on density.
- Align text columns left and numerical columns right.
- Use tabular numerals for financial and numerical fields.
- Keep status and risk labels visible as text badges.
- Make row navigation explicit; do not make an entire row appear
  clickable unless it is.
- Provide clear hover and keyboard-focus states.
- Keep sorting indicators visible when sorting is supported.
- Keep pagination and result count near the table.
- Filters must reflect actual API capabilities; do not offer client-only
  filters that imply server-wide filtering.
- Preserve the current filter and pagination context when opening and
  returning from a detail view where feasible.
- Use a responsive horizontal scroll container for wide tables on
  smaller screens. Do not silently remove important columns.
- On narrow screens, use a deliberate compact row/card representation
  only when it preserves the essential fields and actions.

Do not load unbounded transaction lists. Use backend pagination and
bounded filters.

### 7.4 Badges and status labels

- Use small, readable badges with restrained background tints.
- Include text labels for status and severity.
- Use consistent label vocabulary from backend enums and API contracts.
- Do not invent a frontend-only lifecycle state.
- Do not make badges excessively rounded or oversized.
- Keep model risk level, investigation status, priority, and AI-summary
  status visually distinct.

### 7.5 Charts and data visualization

Use Apache ECharts for charts, consistent with the existing technical
requirements.

Chart principles:

- Every chart needs a clear title and, where needed, a concise
  description.
- Label axes, units, and date ranges.
- Use a restrained palette and avoid unnecessary gradients.
- Use risk colors only when the series represents risk semantics.
- Use neutral colors for contextual or baseline series.
- Provide tooltips with exact values and relevant context.
- Do not rely on color alone; use legends, labels, markers, or patterns
  where needed.
- Provide empty, loading, and error states.
- Provide a tabular or textual alternative for important chart data when
  practical.
- Respect backend-provided aggregation, timezone, and reporting
  boundaries.
- Never calculate authoritative risk scores, financial totals, medians,
  or behavioral features in the browser.

### 7.6 KPI and summary cards

Use KPI cards selectively for high-value metrics such as transaction
volume, flagged activity, open investigations, or dataset status—only
where those metrics are available from the API.

- Use a short label, a prominent value, and optional context.
- Keep cards neutral; do not color the entire card by severity.
- Do not invent percentage changes or trends if the API does not provide
  a valid comparison.
- Include units, time range, and scope where ambiguity is possible.
- Avoid presenting a metric without explaining its population or period
  when that context matters.

### 7.7 Modals, drawers, and confirmations

- Use dialogs for focused, short actions or confirmations.
- Use a side drawer for contextual details when preserving the
  underlying list is useful.
- Use a dedicated detail/workspace page for complex investigations.
- Keep modal actions explicit and ordered consistently.
- Ensure focus is trapped appropriately while a modal is open and
  restored when it closes.
- Do not place long investigation workflows inside oversized modals.

### 7.8 Notifications and feedback

- Use concise toast notifications for transient success or failure
  feedback.
- Use inline alerts for persistent, page-relevant problems.
- Use confirmation dialogs for destructive or irreversible operations.
- Display actionable error messages without exposing stack traces, SQL,
  tokens, or internal implementation details.
- Preserve request/correlation identifiers only where useful for support
  or diagnostics.

------------------------------------------------------------------------

## 8. FinSignal-Specific Experience Patterns

### 8.1 Dashboard

The dashboard should answer: **What requires attention, and where should
the user go next?**

Recommended hierarchy:

1.  Page title and selected data scope
2.  High-value summary metrics returned by the backend
3.  Risk/investigation overview
4.  Recent or priority work queues
5.  Relevant trend visualizations
6.  Recent dataset/import activity, if relevant to the user’s role

Avoid turning the dashboard into a wall of unrelated charts. Each
visualization must support a real user question.

### 8.2 Transaction explorer

The transaction explorer is a data-first workspace.

Prioritize:

- Transaction reference
- Timestamp
- Account or relevant party
- Amount and currency
- Transaction type
- Transaction status, if provided
- Risk level/score, if analyzed
- Clear access to transaction details

Use filters supported by the API, such as date range, account, amount
range, transaction type, or risk criteria only when those filters are
actually implemented by the backend.

Transaction details should distinguish:

- Original transaction attributes
- Related account/merchant/device/location context
- Backend-derived analytics or behavioral signals
- Risk analysis and risk factors

Do not visually merge raw transaction attributes with derived
intelligence.

### 8.3 Risk monitoring

Risk monitoring is a prioritization interface, not a verdict screen.

- Make severity and score readable but not sensational.
- Display risk factors and their explanations alongside the score where
  available.
- Show analysis timestamp and relevant model/context metadata when
  exposed by the API.
- Distinguish unanalysed, unavailable, failed, and low-risk states.
- Provide a clear route from a risk item to the associated transaction
  or investigation.
- Never label a transaction as confirmed fraud solely because its model
  risk is high.

### 8.4 Investigation workspace

The investigation workspace is one of the most important screens in
FinSignal.

Recommended structure:

``` text
+------------------------------------------------------------------+
| Investigation reference / status / priority / assignment         |
+--------------------------------------+---------------------------+
| Primary transaction                  | Investigation context    |
| Core transaction facts               | Owner / status / dates    |
| Risk analysis and factors             | Resolution information    |
+--------------------------------------+---------------------------+
| Related transactions                  | Evidence                  |
| Bounded related activity              | Attached evidence items  |
+--------------------------------------+---------------------------+
| AI investigation summary (if present and available)              |
| Executive summary                                               |
| Observed facts                                                  |
| Derived signals                                                 |
| Potential interpretations                                       |
| Uncertainties and limitations                                   |
+------------------------------------------------------------------+
| Human investigator actions / resolution controls                |
+------------------------------------------------------------------+
```

The exact panel layout may adapt to available API data and screen width.

Rules:

- Keep investigation status, priority, and assignment prominent.
- Make the primary transaction visually identifiable.
- Show related transactions as related context, not as proof of
  wrongdoing.
- Present evidence as individually inspectable items with source/type
  and timestamps where available.
- Preserve the distinction between current state and immutable evidence
  snapshots.
- Make important human actions explicit and auditable.
- Do not imply that the frontend can bypass backend lifecycle rules.
- Do not present a resolved/closed case as editable if the API disallows
  the operation.

### 8.5 AI investigation summary

AI content must be displayed as **decision support**, never as an
autonomous verdict.

Preserve the backend’s structured fields:

1.  `executive_summary`
2.  `observed_facts`
3.  `derived_signals`
4.  `potential_interpretations`
5.  `uncertainties_and_limitations`

Presentation rules:

- Give the summary a visible label such as `AI-assisted summary`.
- Keep observed facts visually distinct from interpretations.
- Present uncertainties and limitations; do not hide them in a tooltip
  or collapsed footnote by default.
- Display cited evidence/transaction references as navigable references
  only when the API provides valid references.
- Show stale or outdated summary state when the API indicates
  `is_stale`.
- Show pending, failed, unavailable, and generated states distinctly
  when exposed by the API.
- Provide a clear refresh/regenerate action only when authorized and
  supported.
- Do not add an unrestricted chatbot interface to this feature.
- Do not allow AI content to resolve an investigation, modify evidence,
  or change a risk score.

### 8.6 Dataset management

Dataset management should communicate the ingestion lifecycle clearly.

- Explain accepted file type and size constraints before upload.
- Show upload progress only when the client can measure it reliably.
- Display validation/import state using backend status values.
- Summarize accepted, rejected, or failed records only when returned by
  the API.
- Make error details understandable and actionable.
- Do not display a successful import until the backend confirms it.
- Keep import history and dataset scope visible.

### 8.7 Audit history

Audit views should prioritize chronology and traceability.

- Show event type, actor, timestamp, and affected resource when
  available.
- Use a consistent timestamp format and timezone display.
- Keep audit events visually read-only.
- Do not offer edit/delete affordances for append-only audit records.
- Distinguish audit history from ordinary application logs.

------------------------------------------------------------------------

## 9. Navigation & Information Architecture

The application navigation should reflect user tasks and backend
capabilities.

Candidate groups:

**Workspace** - Overview - Transactions - Accounts

**Intelligence** - Risk Monitoring - Analytics

**Operations** - Investigations - Datasets / Imports - Audit History

**Administration** - User Management - System settings, only if
implemented

The final menu must be reconciled with actual API routes, role
permissions, and implemented screens before each phase is built.

### 9.1 Role-aware experience

FinSignal includes `ADMIN`, `ANALYST`, and `INVESTIGATOR` roles.

- Navigation and action visibility may adapt to the authenticated user’s
  role.
- Do not treat hidden UI controls as authorization.
- The backend must enforce every protected operation.
- On a `403 Forbidden`, show a clear permission message and do not retry
  as another role.
- Avoid exposing administrative controls to users who do not need them.

------------------------------------------------------------------------

## 10. Responsive Behavior

FinSignal is desktop-first because transaction analysis and
investigation workflows benefit from wide tables and multi-panel
layouts. It must still remain usable on tablets and phones.

| Breakpoint   |         Width | Behavior                                                                                               |
|--------------|--------------:|--------------------------------------------------------------------------------------------------------|
| Mobile       |     `< 640px` | Single-column content, compact navigation, stacked forms, scrollable tables or deliberate compact rows |
| Tablet       |  `640–1023px` | Collapsible sidebar, reduced multi-column layouts, charts stack as needed                              |
| Desktop      | `1024–1439px` | Full application shell, standard table density, two-column workspaces where useful                     |
| Wide desktop |   `>= 1440px` | Wider investigation panels and charts while preserving readable line lengths                           |

Rules:

- Do not shrink desktop tables until text becomes unreadable.
- Use horizontal scrolling for genuinely wide tables.
- Keep primary actions accessible on narrow screens.
- Stack filters into a clear filter panel or drawer on mobile.
- Ensure dialogs fit within the viewport.
- Avoid hover-only actions; touch users must have an equivalent
  interaction.
- Keep touch targets approximately 44px where practical.
- Test the investigation workspace at tablet widths; it is the most
  layout-sensitive screen.

------------------------------------------------------------------------

## 11. Interaction States

Every data-driven component must account for the following states where
applicable:

### Loading

- Use skeletons for stable page structures and tables.
- Use a spinner for short, localized actions.
- Keep the page context visible during background refreshes.
- Avoid flashing empty states while a request is still loading.

#### Implemented `Skeleton` & `TableSkeleton` sizing (`src/components/ui/Skeleton.tsx`)

- **`Skeleton` variants:** Supports explicit non-conflicting variants `"text"` (`h-4` / `16px`, `rounded-badge`), `"text-sm"` (`h-3.5` / `14px`, `rounded-badge`), `"block"` (`h-20`, `rounded-control`), and `"circle"` (`h-9 w-9`, `rounded-full`) with `aria-hidden="true"` and `animate-pulse bg-surface-subtle`.
- **`TableSkeleton`:** Renders header cells with `variant="text-sm"` (`14px`) and body cells with `variant="text"` (`16px`), avoiding passing conflicting Tailwind `h-*` utilities over a fixed default height (because compiled CSS puts `.h-4` after `.h-3.5`).

### Empty

- Explain why there is no data.
- Provide a relevant next action when one exists.
- Distinguish “no records match these filters” from “no records exist.”

### Error

- State what failed in plain language.
- Provide retry only when retry is safe and meaningful.
- Preserve filter/form context where possible.
- Do not expose internal stack traces or sensitive backend details.

### Partial data

- Identify which section is unavailable.
- Do not replace unavailable data with zero, low risk, or a fabricated
  default.
- Keep successfully loaded sections usable when independent.

### Disabled

- Use a clear disabled state.
- Explain missing prerequisites when possible.
- Do not visually suggest an action is available if the backend will
  reject it.

### Success

- Confirm the completed operation.
- For consequential operations, reflect the authoritative state returned
  by the backend rather than optimistic assumptions.

------------------------------------------------------------------------

## 12. Motion & Micro-interactions

Motion should be subtle and functional.

- Use short transitions for hover, focus, and menu state changes.
- Avoid animated charts that obscure comparisons or imply real-time data
  where none exists.
- Respect `prefers-reduced-motion`.
- Do not use pulsing red indicators to create urgency unless there is a
  genuine live alert capability.
- Loading animations must not imply progress percentages unless progress
  is measured.

------------------------------------------------------------------------

## 13. Accessibility Requirements

Target WCAG 2.2 AA as the baseline.

- Maintain sufficient text and non-text contrast.
- Provide visible keyboard focus.
- Support keyboard navigation for menus, dialogs, tables, and forms.
- Use semantic headings and landmarks.
- Associate form labels and validation messages programmatically.
- Provide accessible names for icon-only buttons.
- Do not use color as the only indicator of risk or status.
- Ensure charts have meaningful text alternatives or accessible
  summaries.
- Respect reduced-motion preferences.
- Ensure zoom and text scaling do not hide essential actions.
- Announce important asynchronous status changes to assistive technology
  where appropriate.

Accessibility must be tested, not assumed from component-library
defaults.

------------------------------------------------------------------------

## 14. Data Presentation & Integrity Rules

These rules are mandatory because FinSignal handles financial and
investigative data.

1.  **No browser-side authoritative calculations.** Do not calculate
    risk scores, behavioral features, financial aggregates, or
    investigation outcomes in the frontend.
2.  **Preserve decimal precision.** Treat monetary API values as decimal
    strings according to the API contract. Do not use JavaScript
    `Number` arithmetic for authoritative monetary values.
3.  **Always show currency.** Amounts must include the relevant currency
    code or symbol.
4.  **Respect timestamps.** Backend timestamps are timezone-aware and
    persisted in UTC. Convert for display only with an explicit timezone
    convention; do not silently change the underlying value.
5.  **Respect pagination.** Do not fetch all transactions or
    investigations to implement local pagination.
6.  **Respect API filters.** Only present filters supported by the
    backend contract.
7.  **Do not invent data.** Demo fixtures must be clearly confined to
    development/demo mode and must never be mixed with production API
    data.
8.  **Preserve provenance.** Distinguish raw transaction fields, derived
    analytics, model outputs, evidence snapshots, and AI-generated
    content.
9.  **Do not infer missing values.** Use explicit unavailable/unknown
    states.
10. **Use backend state.** Investigation lifecycle, assignment,
    evidence, and permissions are controlled by backend responses.

------------------------------------------------------------------------

## 15. Security-Aware UI Rules

- Do not display, log, or expose access tokens.
- Do not put secrets or credentials in frontend source code or
  environment variables prefixed for client exposure.
- Do not assume that client-side route guards provide security.
- Handle `401 Unauthorized` and `403 Forbidden` distinctly.
- Do not render untrusted transaction descriptions, merchant names,
  evidence text, or AI content as raw HTML.
- Treat uploaded files and their filenames as untrusted input.
- Show upload restrictions and server-side validation outcomes.
- Do not expose internal error traces, database details, model artifact
  paths, or provider credentials.
- Authentication token storage and refresh behavior must follow the
  separately approved frontend security/API integration decision. This
  design document does not choose local storage or cookie storage.
- Do not cache sensitive investigation content beyond the requirements
  of the application and approved session behavior.

------------------------------------------------------------------------

## 16. Design Tokens & Implementation Guidance

Implement tokens centrally using the styling system selected by the
frontend technical design.

Suggested token names:

``` css
:root {
  --color-brand-700: #0052FF;
  --color-brand-800: #003ECC;
  --color-brand-100: #EAF0FF;
  --color-brand-50: #F5F8FF;

  --color-canvas: #F7F8FA;
  --color-surface: #FFFFFF;
  --color-surface-subtle: #F3F4F6;
  --color-surface-hover: #F8FAFC;
  --color-border: #E2E5EA;
  --color-border-strong: #CBD1D9;

  --color-text-primary: #111827;
  --color-text-secondary: #4B5563;
  --color-text-muted: #6B7280;
  --color-text-disabled: #9CA3AF;

  --color-risk-critical: #B42318;
  --color-risk-high: #D92D20;
  --color-risk-medium: #B54708;
  --color-risk-low: #027A48;
  --color-info: #175CD3;
  --color-success: #067647;
  --color-warning: #B54708;
  --color-danger: #B42318;

  --radius-control: 8px;
  --radius-panel: 10px;
  --radius-dialog: 12px;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
}
```

These are design-level tokens. The implementation maps them in `frontend/src/styles/tokens.css` using `--fs-*` CSS custom properties under `:root` mapped cleanly into Tailwind CSS v4 `@theme inline` namespaces (avoiding self-referential CSS variables), with base layout, `:focus-visible` (`2px solid var(--fs-focus)`), `.tabular-nums`, and `@media (prefers-reduced-motion: reduce)` rules in `frontend/src/index.css`.

### 16.1 Component consistency

Prefer a small set of reusable primitives:

- `Button` *(Implemented F1 — variants `primary`, `secondary`, `tertiary`, `danger`; sizes `sm`, `md`, `lg`, `icon`; `isLoading` + `aria-busy`; `asChild` via Radix Slot strips `disabled`/`isLoading` even in production builds; `F1-AUD-009` icon-loading crowding deferred)*
- `Input` / `Select` *(Implemented F1 — accessible labels, hints, errors, mutually exclusive state classes; Date range deferred to F2+)*
- `Badge` *(Implemented F1 — `neutral`, `brand`, semantic `info`/`success`/`warning`/`danger`, risk tiers `risk-low`/`risk-medium`/`risk-high`/`risk-critical`)*
- `Card` (`Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`) *(Implemented F1)*
- `Table` (`TableContainer`, `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell`, `TableCaption`) *(Implemented F1 — `numeric` right-aligned monospace `.tabular-nums` without float coercion; `aria-sort`)*
- `Tabs` *(Deferred to F2+)*
- `Dialog` *(Implemented F1 — Radix Dialog portal, backdrop overlay, focus trap, Escape/close restoration; Drawer deferred to F2+)*
- `Alert` *(Implemented F1 — `status` default, opt-in `alert`/`region`, `requestId`, escaped React children; `F1-AUD-009` attribute passthrough deferred)*
- `Tooltip` *(Deferred to F2+)*
- `Pagination` *(Deferred to F3)*
- `Skeleton` / `TableSkeleton` *(Implemented F1)*
- `EmptyState` *(Implemented F1 — `"empty"` vs `"no-results"` variants)*
- `Page header` / `Filter bar` *(Deferred to F2/F3)*

Feature-specific components should compose these primitives rather than
implement unrelated visual variants.

------------------------------------------------------------------------

## 17. Do’s and Don’ts

### Do

- Use blue for primary actions and active navigation.
- Use neutral backgrounds and subtle borders.
- Make tables readable and information-dense.
- Align financial values and use tabular numerals.
- Label risk severity explicitly.
- Separate facts, model signals, AI interpretations, and human
  decisions.
- Show loading, empty, error, and partial-data states.
- Keep investigation actions clear and deliberate.
- Use consistent spacing, radii, and component states.
- Make the desktop workflow efficient without neglecting mobile
  usability.

### Don’t

- Copy Coinbase’s cryptocurrency content, market rows, or marketing
  hero.
- Use pill-shaped buttons and 24px card corners everywhere.
- Turn every metric into a brightly colored card.
- Use red/green as generic transaction movement colors.
- Present a model score as a fraud verdict.
- Present AI interpretations as verified facts.
- Calculate authoritative financial or risk values in the browser.
- Hide important information behind color alone.
- Use fake metrics, fake charts, or fabricated activity in production.
- Create UI actions that the backend does not support.
- Treat client-side role visibility as access control.
- Add decorative animations that reduce clarity.

------------------------------------------------------------------------

## 18. Agent Prompt Guide

When generating or modifying FinSignal UI, follow this instruction:

> Build a professional financial transaction intelligence and
> investigation interface using this DESIGN.md as the visual source of
> truth. Use a light-first, blue-led enterprise visual system with
> restrained neutral surfaces, compact controls, readable data tables,
> and clear semantic risk indicators. Prioritize information hierarchy,
> traceability, accessibility, and investigator workflow efficiency.
> Keep raw transaction facts, backend-derived risk signals, AI-generated
> interpretations, and human investigation decisions visually distinct.
> Do not invent data or capabilities. Do not calculate authoritative
> financial or risk values in the browser. Use backend-provided values
> and statuses. Avoid generic fintech marketing layouts,
> trading-terminal aesthetics, excessive rounded cards, gradients, and
> decorative effects.

Quick reference:

- **Theme:** light-first enterprise investigation workspace
- **Primary:** `#0052FF`
- **Canvas:** `#F7F8FA`
- **Surface:** `#FFFFFF`
- **Text:** `#111827`
- **Border:** `#E2E5EA`
- **Risk:** explicit red / amber / green severity labels
- **Typography:** Inter/system sans + tabular numerals
- **Controls:** compact, rectangular, 8px radius
- **Panels:** subtle borders, 10–12px radius
- **Tables:** dense, readable, paginated, horizontally scrollable when
  needed
- **Charts:** Apache ECharts, restrained palette, backend-authoritative
  data
- **Accessibility:** WCAG 2.2 AA target

------------------------------------------------------------------------

## 19. Relationship to Other Frontend Documents

This document defines visual presentation and interaction patterns. It
does not replace:

| Concern                                        | Source of truth                                          |
|------------------------------------------------|----------------------------------------------------------|
| Product goals, personas, and scope             | `FRONTEND_PRD.md`                                        |
| Frontend stack and dependencies                | `FRONTEND_TRD.md`                                        |
| Component boundaries and application structure | `FRONTEND_ARCHITECTURE.md`                               |
| API endpoints and response schemas             | Backend `API_GUIDELINES.md` and generated OpenAPI schema |
| Authentication and browser security            | `SECURITY.md` plus frontend security decisions           |
| Test strategy                                  | `FRONTEND_TESTING_STRATEGY.md`                           |
| Delivery phases                                | `FRONTEND_ROADMAP.md`                                    |
| Accepted architectural decisions               | `DECISIONS.md`                                           |

If this document conflicts with an API contract or backend invariant,
the backend contract and invariant remain authoritative. Raise the
conflict for review rather than silently changing backend semantics in
the UI.

------------------------------------------------------------------------

## 20. Source & Adaptation Notes

This design direction was informed by:

- getdesign.md’s Coinbase design analysis and preview:
  https://getdesign.md/coinbase/design-md
- Coinbase preview: https://getdesign.md/design-md/coinbase/preview
- VoltAgent’s `awesome-design-md` collection:
  https://github.com/VoltAgent/awesome-design-md
- FinSignal project documentation: `ARCHITECTURE.md`, `TRD.md`,
  `API_GUIDELINES.md`, `SECURITY.md`, `CODING_STANDARDS.md`, and
  `PROJECT_ROADMAP.md`.

The getdesign.md Coinbase analysis describes a clean blue identity,
neutral surfaces, numerical typography, hairline-divided data rows, and
restrained semantic trading colors. FinSignal adapts those patterns to
its own investigative domain and deliberately changes the component
geometry, information architecture, severity semantics, and workflow
patterns.

The document is a project-specific design specification. It is not
affiliated with or endorsed by Coinbase or IBM.
