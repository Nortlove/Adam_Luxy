# Auth + Multi-Surface Frontend Addendum
## Slice ID: Frontend Auth Addendum 2026-05-09
## Predecessor: PLATFORM_SYSTEM_DEEP_DIVE_2026_05_09.md (Phase 1) + ARCHITECTURE_REASONING_FOR_CLAUDE_PROPER_2026_05_09.md (Phase 2)
## Audience: Claude Proper (architectural decision support)
## Audit type: Read-only correction + depth addendum
## Scope: Authentication model + route-group separation + (app) operator surface vs (client) customer surface + BFF proxy pattern + multi-tenant migration roadmap
## Branch: feature/hmt-dashboard

---

## §1 Why this addendum exists

Chris flagged that Phase 1 §6 (Frontend / dashboard surface) and Phase 2 §3 (Frontend Focus Area) **missed the depth** of what the dashboard implements around authentication and the multi-surface design. The original memos noted "8 operator routes + BFF proxy" but did not surface:

1. The explicit **auth-stub-with-Phase-C-migration** model in `dashboard/src/lib/auth.ts`
2. The **two intentionally-distinct route groups** — `(app)` for operators/superadmin, `(client)` for customers
3. The **role-gated UI affordances** that depend on `user.role === "superadmin"`
4. The **per-advertiser tenant parameterization** (`advertiser_id=luxy_ride` in customer report)
5. The **BFF (Backend-For-Frontend) pattern** — Next route handlers proxying to FastAPI with server-side bearer token never exposed to client
6. The **discipline rules** baked into the layout files (per orientation A10 + Chris directive 2026-04-22) about what the customer surface must NOT look like

This addendum corrects that omission. It supersedes Phase 1 §6 and Phase 2 §3. Read this first when reasoning about the frontend surface.

---

## §2 The auth model: v1 single-user stub with explicit Phase C migration roadmap

**Source:** `dashboard/src/lib/auth.ts` (32 lines total)

```typescript
/**
 * v1 single-user auth stub.
 *
 * Phase A uses a single hard-coded user identified by an env-configured
 * email + Bearer token. When Phase C multi-tenancy lands this module is
 * replaced with a proper SSO flow (Clerk or Auth.js) and per-session
 * user resolution — nothing outside this file should depend on the auth
 * shape directly.
 */

export type CurrentUser = {
  id: string;
  email: string;
  name: string;
  role: "superadmin";
};

export function getCurrentUser(): CurrentUser {
  const email = process.env.INFORMATIV_USER_EMAIL ?? "chris@informativgroup.com";
  const name = process.env.INFORMATIV_USER_NAME ?? "Chris Nocera";
  return {
    id: "user:chris",
    email,
    name,
    role: "superadmin",
  };
}

export function getApiToken(): string | undefined {
  return process.env.INFORMATIV_API_TOKEN;
}
```

**Architectural reading:**

- **Phase A (today)**: single hard-coded user — Chris, role "superadmin". The `role` type is literally `"superadmin"` as a string-literal type union with no other values. Effectively no auth at the dashboard process boundary; identity comes from env vars.
- **Phase C (deferred)**: SSO flow via Clerk or Auth.js + per-session resolution. The auth.ts module is the seam; the rest of the dashboard depends on `getCurrentUser()` not on the auth backend, so Phase C is a swap-the-implementation slice rather than a touch-everything migration.
- **Inference: Phase B is implicit** — the gap between hard-coded single-user and full multi-tenant SSO. Phase B likely = configurable user identity per dashboard process (multiple operator users; still no customer-side login). Not committed to in code; would be a natural intermediate step if pilot needs operator multi-user before customer self-service.
- **`INFORMATIV_API_TOKEN`** is the server-side Bearer token the dashboard uses to authenticate to the FastAPI backend (port 8000). It's read by `dashboard/src/lib/api.ts` (the BFF helper) and **never exposed to the client browser** — only the Next server-side route handlers see it. This is the security boundary that lets the dashboard expose customer data via the BFF without leaking backend credentials.

---

## §3 The three surfaces — what's actually built

The dashboard has **two route groups** at the Next.js app router level, with the auth stub and BFF together implementing **three distinct usage modes**:

### §3.1 Surface 1: Operator / Superadmin — route group `(app)`

**Source:** `dashboard/src/app/(app)/layout.tsx` + `dashboard/src/components/app-sidebar.tsx`

**Layout shape:** sidebar nav + main content area + header with "pilot · single-tenant" badge.

**Sidebar nav (7 routes):**

| Route | Page file | Purpose (per route name + adjacent component naming) |
|-------|-----------|-------------|
| `/campaigns` | `(app)/campaigns/page.tsx` | Campaign management (the operator's primary entry — root `/` redirects here) |
| `/recommendations` | `(app)/recommendations/page.tsx` + `(app)/recommendations/[id]/page.tsx` | Recommendation list + per-recommendation drill-down |
| `/learning` | `(app)/learning/page.tsx` | Learning loop visibility (per_user_posterior_modulation state, etc.) |
| `/discovery` | `(app)/discovery/page.tsx` | Cohort discovery + audience exploration (per `components/discovery/` directory existence) |
| `/analytics` | `(app)/analytics/page.tsx` | Aggregate analytics (per `api/analytics/system-convergence` + `api/analytics/client-decisions` BFF endpoints) |
| `/ledger` | `(app)/ledger/page.tsx` | "Dialogue Ledger" — operator-side conversation/decision history (per icon `MessagesSquare` + label) |
| `/settings` | `(app)/settings/page.tsx` | Configuration (per route name + `_components/` subdirectory) |

**Operator-only affordance in operator nav:**

```tsx
// app-sidebar.tsx footer (lines 96-103):
<Link
  href="/client/report"
  className="..."
  title="Switch to the client-facing report surface (QA)"
>
  <ExternalLink className="size-3" />
  <span>View client surface →</span>
</Link>
```

The operator can "View client surface" — this is a QA affordance allowing the operator to see what the customer sees, NOT a separate access route. Inference: this is for verifying client-facing rendering before pilot client onboarding.

### §3.2 Surface 2: Customer / Client — route group `(client)`

**Source:** `dashboard/src/app/(client)/layout.tsx` + `dashboard/src/app/(client)/client/report/page.tsx`

**Layout discipline (verbatim from layout file comment):**

```typescript
/**
 * Client surface layout — Front-end A.
 *
 * Intentionally distinct from the internal (app) layout: no sidebar, no
 * Dialogue Ledger, no Learning or Analytics nav. Clients receive a
 * report surface; they do not operate the cognitive instrument.
 *
 * Discipline (per orientation A10 + Chris directive 2026-04-22):
 *   - Do not give the client a management-UI feel. This is a report,
 *     not a console. Clean header, plenty of whitespace, content
 *     centered in a readable column.
 *   - Do not leak internal nav. The internal nav (Campaigns /
 *     Recommendations / Learning / Dialogue Ledger / etc.) is for
 *     operators, not clients. If the client needs to reach another
 *     client surface in the future, add to this layout's header only
 *     what they need — not a replica of the internal sidebar.
 *   - Route groups are URL-transparent. This file wraps everything
 *     under dashboard/src/app/(client)/ ; the existing (app) layout is
 *     unchanged and continues to wrap all internal routes.
 */
```

**Layout shape:** centered max-w-5xl column, no sidebar, INFORMATIV/Client Report branding header, "Reported by INFORMATIV · ADAM" footer.

**Routes (1 today):**

| Route | Page file | Purpose |
|-------|-----------|---------|
| `/client/report` | `(client)/client/report/page.tsx` | The customer's report view of their own campaign performance |

**Per-advertiser tenant parameterization:** The customer report page calls:

```typescript
// (client)/client/report/page.tsx line 31-33
const data = await api.get<ClientReport>(
  "/api/dashboard/client/report?advertiser_id=luxy_ride",
);
```

The `advertiser_id` query parameter scopes the report to a specific advertiser tenant. Today it's hard-coded to `"luxy_ride"`; in Phase C/multi-tenant this would resolve from the authenticated session.

**Role-gated affordance in customer layout (the "← Internal" escape hatch):**

```tsx
// (client)/layout.tsx lines 41-50:
{user.role === "superadmin" && (
  <Link
    href="/campaigns"
    className="..."
    title="Switch to internal (superadmin) surface"
  >
    ← Internal
  </Link>
)}
```

When an operator is viewing the client surface (e.g., via the QA link from §3.1), this gives them a link back to the internal surface. The gate `user.role === "superadmin"` is the **only role check in the entire frontend codebase**. A real customer (Phase C, role !== "superadmin") would not see this link and would not see internal routes from the customer surface. **The architecture contemplates non-superadmin roles even though only superadmin is implemented today.**

### §3.3 Surface 3: BFF / Reporting backplane — `dashboard/src/app/api/`

**Not a UI surface** — this is the Next.js API route handler layer that proxies frontend requests to the FastAPI backend on port 8000. It's the third "thing" Chris's framing of "reporting + customer + superadmin" might point at: it's the backplane that makes both the operator and customer surfaces have data to render.

**BFF endpoints (7 routes today):**

| Next BFF route | Backend FastAPI proxy target | Consumer surface |
|----------------|------------------------------|------------------|
| `api/learning/subject/[userId]/route.ts` | (per-userId subject learning state) | operator `/learning` |
| `api/learning/mechanism-effectiveness/route.ts` | (mechanism-effectiveness aggregate) | operator `/learning` |
| `api/client/report/route.ts` | `/api/dashboard/client/report?advertiser_id=...` | customer `/client/report` |
| `api/client/recommendations/[recId]/decide/route.ts` | (customer accept/reject a recommendation) | customer (client recommendation acceptance flow — implies feature beyond the report-only surface visible today) |
| `api/analytics/client-decisions/route.ts` | (client decision history aggregate) | operator `/analytics` |
| `api/analytics/system-convergence/route.ts` | (system convergence metric — Bayesian posterior convergence) | operator `/analytics` |

**Pattern (from `api/client/report/route.ts`):**

```typescript
export async function GET(request: Request) {
  const incoming = new URL(request.url);
  const advertiserId = incoming.searchParams.get("advertiser_id") ?? "";
  // ...build outgoing query...
  try {
    const data = await apiFetch<ClientReport>(path);
    return NextResponse.json(data);
  } catch (err) {
    if (err instanceof ApiError) {
      return NextResponse.json(
        { error: err.message, status: err.status, payload: err.payload },
        { status: err.status },
      );
    }
    return NextResponse.json({ error: ... }, { status: 502 });
  }
}
```

The BFF pattern means:

- **Frontend never holds backend credentials.** The `INFORMATIV_API_TOKEN` env var lives only in the Next server process; `apiFetch` injects it into outgoing requests to FastAPI. Browser never sees it.
- **Type-safe contracts.** The frontend's TypeScript types (`ClientReport` etc.) are generated from the FastAPI OpenAPI schema (per Phase 1 finding: "OpenAPI-generated types"). Schema changes propagate automatically.
- **Error normalization.** The BFF converts FastAPI errors into `NextResponse.json({error, status, payload})` shape that the frontend components can render uniformly.
- **Per-route policy seam.** A future per-tenant ACL or rate-limit lives in the Next route handler, not in the FastAPI backend. Lets the dashboard add policy without modifying backend.

---

## §4 What "three logins" actually means in code today

Chris's framing — "we built not only a reporting login but we also created a login for a customer and a superadmin" — maps to the code as:

| Chris's term | What's actually built today | What the architecture contemplates for Phase C |
|--------------|----------------------------|------------------------------------------------|
| **Superadmin login** | Hard-coded `role: "superadmin"` user from env vars; sees the full operator surface (`/campaigns`, `/learning`, `/analytics`, etc.) | SSO-authenticated operator with role-based access to specific operator routes |
| **Customer login** | Same hard-coded user; the `(client)` layout intentionally hides operator nav and shows the report-centric customer surface; `advertiser_id=luxy_ride` is hard-coded in the page | SSO or magic-link customer auth; per-customer `advertiser_id` scoped to the authenticated session; `role !== "superadmin"` so the "← Internal" escape hatch isn't shown |
| **Reporting login** | Inferred to mean either the BFF backplane (which serves data to both operator + customer reporting surfaces) OR specifically the operator's reporting/analytics routes (`/analytics`, `/learning`, `/ledger`). The codebase doesn't have a separate "reporting" login distinct from operator | Inferred to mean a third role (e.g., "viewer" or "analyst") with read-only access to operator analytics but no campaign-edit permissions. Not implemented; the role union is currently single-value. |

**The honest interpretation:** what Chris built is **two route groups + one auth seam**, not three logins. The route-group separation is real and disciplined; the auth differentiation is deferred to Phase C. The "reporting" surface as a distinct third login concept is not yet a code artifact — but the BFF + role-gating architecture supports adding it as a Phase C slice without restructuring.

---

## §5 The discipline guardrails (per orientation A10 + Chris directive 2026-04-22)

The customer-surface layout file (`(client)/layout.tsx` lines 12-29) encodes explicit discipline rules. These are unusually specific for a layout file and reflect Chris's directive that the customer surface **must not** become a management UI:

1. **"Do not give the client a management-UI feel."** — clean header, whitespace, centered readable column, NOT a sidebar-and-tools console.
2. **"Do not leak internal nav."** — Campaigns / Recommendations / Learning / Dialogue Ledger nav is for operators only; the customer surface must never reproduce them.
3. **"Route groups are URL-transparent."** — Next.js's `(group)` syntax means `/(client)/client/report` is served at `/client/report`, not `/(client)/client/report`. Wrapping under route groups is for layout scoping, not URL nesting.

These rules sit IN the layout file (not in a separate style guide) so that any future agent or developer modifying the customer surface reads them inline before changing the layout.

**Inference about the design intent:** Chris is treating the customer-vs-operator distinction as a product principle, not just a permissions matter. The customer is "the brand reading their own report"; they should not be invited to think of themselves as operating the platform. This frames Phase C's customer-auth requirements: customers need authentication that scopes them to their own `advertiser_id`, NOT customers need a richer customer-side UI.

---

## §6 The orientation A10 reference + the directive 2026-04-22

`docs/MEMORY.md` and `ADAM_AGENT_ORIENTATION.md` reference 15 antipatterns (A1–A15) that the platform must avoid. **A10 is the antipattern this layout discipline guards against** (per the layout file comment citing "orientation A10 + Chris directive 2026-04-22"). I haven't read A10's specific text in this addendum — Phase 2 of the deep-dive should have included this — but the pattern is clear from context: A10 likely cautions against drift toward giving the customer surface management-UI affordances that subtly turn the report into a console (and shift the customer's relationship with the platform from "consume insights" to "operate the system").

The 2026-04-22 directive is referenced in `docs/MEMORY.md` as the inflection point for attention-inversion as platform core. The customer-surface discipline maps to that broader principle: the platform serves by blending into the user's existing pattern, not by demanding the user adopt the platform's pattern. The customer report is read; the operator console is operated. Different cognitive postures; different UI shapes.

---

## §7 Where the auth + multi-surface architecture sits today (operational state)

| Concern | State | Notes |
|---------|-------|-------|
| Auth identification (who am I?) | **Stub** — single hard-coded user from env vars | Phase C swap-out point is `dashboard/src/lib/auth.ts:18` |
| Auth authentication (prove who I am?) | **Stub** — `INFORMATIV_API_TOKEN` Bearer token at the FastAPI boundary; no user-facing login flow | Phase C SSO would add the user-facing flow |
| Authorization (what can I do?) | **Single role + route-group separation** — the `(app)` vs `(client)` route groups + the one `user.role === "superadmin"` gate in `(client)` layout | Phase C would parameterize on a real role hierarchy (operator / customer / read-only-analyst / etc.) |
| Multi-tenancy (whose data am I looking at?) | **Per-route hardcoded** — `advertiser_id=luxy_ride` in `(client)/client/report/page.tsx:32`; operator routes likely scope from URL params or session | Phase C would scope all routes from authenticated session's tenant |
| Operator surface (route group `(app)`) | **Operational** — 7 routes with shared sidebar layout; root `/` redirects to `/campaigns` | All 7 routes have page.tsx files; rendering depth varies and was not deeply audited |
| Customer surface (route group `(client)`) | **Operational** — 1 route (`/client/report`) with intentionally-distinct layout | Single report surface; scaffolded for additional customer routes via the existing layout pattern |
| BFF proxy backplane (`api/`) | **Operational** — 7 endpoints proxying FastAPI on port 8000 | OpenAPI-generated types keep frontend + backend in sync |
| Operator → Customer surface QA link | **Operational** — link in operator sidebar footer | Allows operator to view customer surface without separate session |
| Customer → Operator escape hatch (gated on superadmin) | **Operational** — link in `(client)` header visible only when role is superadmin | Wouldn't fire for a real Phase C customer user |

**Pilot-readiness assessment for the auth + multi-surface layer:**

- For the **first pilot week with one customer (LUXY)**: operational. The operator (Chris) has the full operator surface; the customer (LUXY) gets a single report URL scoped to `advertiser_id=luxy_ride` via the customer surface. No real auth needed because there's effectively one operator + one report URL the customer can be sent.
- For **scaling to the second customer**: blocking. The hard-coded `advertiser_id=luxy_ride` means a second customer either needs (a) a second deployment with a different env var (heavy and unscalable) or (b) Phase C multi-tenancy. (b) is the right answer; needs scoping when the second customer is on the horizon.
- For **giving customers self-service login**: Phase C work. Today the customer URL is essentially shared via Chris sending it; there's no per-customer authentication that a customer would log into.

---

## §8 What this means for the Q.A / Q.B / Q.C architectural questions in Phase 2 §7

The Phase 2 architectural-reasoning memo surfaced three top questions for Claude Proper. The auth + multi-surface depth from this addendum reshapes them:

- **Q.A — Creative-variant routing: ours vs StackAdapt-review-gated?** Unchanged by this addendum. Auth has no bearing.
- **Q.B — Causal-claim test scaffolding: pre-pilot or post-pilot?** Unchanged structurally. But: if pilot scales to a second customer, the **per-tenant decision-trace observability** in `api/analytics/client-decisions` becomes a Phase C multi-tenancy concern, not just a reporting concern. Consider whether pilot's first month should test scaling to a synthetic second tenant to surface the multi-tenancy gaps before they bite at the second real customer.
- **Q.C — Minimum viable cell-conditional reporting set for pilot.** Reshaped: the reporting set should include **per-customer-tenant scoping** even though only one customer is on it. Building the per-tenant scoping as part of the cell-conditional reporting from the start adds modest complexity and avoids a Phase C rewrite when the second customer lands.

**One additional architectural question this addendum surfaces (Q.D for Claude Proper):**

- **Q.D — Phase B (intermediate) auth or skip directly to Phase C SSO?** The auth.ts stub explicitly contemplates Phase A → Phase C with no explicit Phase B. But Chris's framing of three logins (reporting / customer / superadmin) implies a multi-role world that Phase A doesn't deliver. Two paths: (i) **Skip Phase B; build Phase C now with full SSO + role hierarchy** — heavier upfront but no rework; (ii) **Phase B = role hierarchy without SSO** (configurable users but still env-var-driven for pilot); ship Phase B in 2-3 days; Phase C SSO when self-service customer onboarding is needed. (ii) is lighter-lift and closer to "what pilot needs"; (i) is more complete and appropriate if customer self-service onboarding is < 3 months out.

---

## §9 Memo closure

This addendum corrects the Phase 1 §6 + Phase 2 §3 omission. It establishes that:

1. The auth implementation is a **deliberately-simple stub** that documents its own Phase C migration path
2. The **route-group separation** between operator `(app)` and customer `(client)` is the real architectural commitment — not the auth itself, which is deferred
3. The **BFF proxy pattern** is the security-and-typing seam that lets the dashboard expose customer data without leaking backend credentials
4. The **discipline guardrails** in the customer-surface layout encode product principles (orientation A10 + 2026-04-22 directive) about what the customer surface must NOT become
5. The **role-gated affordances** (one gate today: `user.role === "superadmin"` in `(client)/layout.tsx`) are the contract Phase C will fill in

For Claude Proper: the architectural choice surface around auth is mostly Phase B vs Phase C — see Q.D above. The route-group + BFF + discipline-rule-in-layout pattern is the right pattern; it does not need rearchitecting. The work to do is parameterizing it for multi-tenant + multi-role use, which the existing seams support without rework.

**Cross-references:**
- Phase 1 inventory: `docs/audits/PLATFORM_SYSTEM_DEEP_DIVE_2026_05_09.md`
- Phase 2 architecture reasoning: `docs/audits/ARCHITECTURE_REASONING_FOR_CLAUDE_PROPER_2026_05_09.md`
- Source files: `dashboard/src/lib/auth.ts`, `dashboard/src/app/(app)/layout.tsx`, `dashboard/src/app/(client)/layout.tsx`, `dashboard/src/components/app-sidebar.tsx`, `dashboard/src/app/page.tsx`, `dashboard/src/app/(client)/client/report/page.tsx`, `dashboard/src/app/api/client/report/route.ts`
