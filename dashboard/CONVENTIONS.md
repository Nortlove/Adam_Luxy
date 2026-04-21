# Dashboard conventions

## API types

The dashboard sources its API types from two places:

- **`src/lib/types.ts`** — manually maintained types that components
  consume directly. These mirror the Pydantic models in
  `adam/api/dashboard/models.py`.
- **`src/lib/api-types.gen.ts`** — auto-generated from the FastAPI
  OpenAPI schema. Acts as a contract check — if backend models
  change in a way that breaks the dashboard, regenerating these
  surfaces the drift as a TypeScript error.

To regenerate:

```bash
# With backend running locally on :8000
pnpm gen:types

# Or pointed at staging / production
OPENAPI_URL=https://informativ-backend.up.railway.app/openapi.json pnpm gen:types
```

Commit `api-types.gen.ts` after regeneration so PR diffs show schema
changes intentionally. Over time, types currently in `types.ts` will
migrate to using the generated shapes via re-export.

## Component layout

- `components/ui/*` — shadcn primitives (untouched copy from registry)
- `components/elicitation/*` — HMT elicitation primitives
  (`ForcedPair`, `TimedPair`, `StoryPrompt`, `RecallabilityProbe`,
  `KAFC`, `MoodProbe`)
- `components/discovery/*` — Discovery flow building blocks
- `components/*` (root) — app-level shared components
  (sidebar, providers, page header, uncertainty panel)

## Server actions

Per Next 16 conventions, server actions live in `actions.ts` files
co-located with the route that uses them. The actions wrap the
typed `api.*` client and call `revalidatePath()` to refresh affected
server-rendered pages.

## Auth

`src/lib/auth.ts` is a single-tenant stub. When Phase C lands, it
gets replaced by a proper SSO flow — nothing outside this file
should depend on the `getCurrentUser` shape directly.
