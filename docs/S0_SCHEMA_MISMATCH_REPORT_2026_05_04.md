# S0 Schema Mismatch Report — Directive Q1 ↔ Live StackAdapt GraphQL

**Date:** 2026-05-04
**Branch:** `feature/hmt-dashboard` @ `9936cf6`
**Slice:** S0 (StackAdapt Historical URL Extraction)
**State:** BLOCKED (per directive §0.3 — surfaced for Claude Proper adjudication)
**Origin:** §1.2 Notes for Claude Code — "*If field names differ at the live endpoint... surfaces any field rename as a `QUESTION:` block.*"

---

## §1.1 Pre-Flight Result

**PASS.** Introspection ping `query IntrospectionPing { __schema { queryType { name } } }` returned `{ "queryType": { "name": "Query" } }` from `https://api.stackadapt.com/graphql`. No 401 / 403 / "REST key not supported" envelope. 60 query fields enumerable.

Auth is solid via `STACKADAPT_GRAPHQL_KEY` (64 chars) loaded from `.env`. The existing `StackAdaptGraphQLClient` (`adam/integrations/stackadapt/graphql_client.py`, last touched 2026-05-02) authenticates Bearer-style; full schema introspection succeeds.

---

## The Mismatch

The directive §1.2 specifies Q1 against a field named `deliveryReportImpressionLevel` with args `advertiserIds, dateFrom, dateTo, breakdowns, after, first` and breakdowns enum `[DAY, CREATIVE_ID, CAMPAIGN_ID, DEVICE_TYPE, GEO, DOMAIN, IAB_CATEGORY, CONTENT_LANGUAGE]`.

**This field does not exist in the live schema.** Introspection of `Query.deliveryReportImpressionLevel` returns `{}`.

The four real fields whose names contain "delivery":

| Field                    | Args                                                                          | Return                          | Granularity exposed       |
|---|---|---|---|
| `adDelivery`             | `dataType: DeliveryStatsDataType, date: DateRangeInput, filterBy: AdFilters, granularity: DeliveryStatsGranularity` | `AdDeliveryPayload`             | domain (per existing `get_domain_performance`); URL not exposed at row level |
| `advertiserDelivery`     | `dataType, date, granularity, ids`                                            | `AdvertiserDeliveryPayload`     | advertiser-roll-up         |
| `campaignDelivery`       | `dataType, date, filterBy: CampaignFilters, granularity`                     | `CampaignDeliveryPayload`       | campaign-roll-up           |
| `campaignGroupDelivery`  | `dataType, date, filterBy: CampaignGroupFilters, granularity`                | `CampaignGroupDeliveryPayload`  | campaign-group-roll-up     |

**Common features of all four:**
- No `breakdowns` arg.
- No Relay cursor args (`after`, `first`).
- Pagination is by date-window rotation, not by cursor.
- None expose URL-level row granularity. The finest granularity reachable on `adDelivery` is `DOMAIN` (per the existing `get_domain_performance` query that uses `groupBy: DOMAIN`).

---

## The Only URL-Bearing Cursor-Paginated Surface

`conversionPath` — which the directive itself names in Q3 (Appendix A) for "trajectory reconstruction":

```
conversionPath(after: String, before: String, filterBy: ConversionPathFilters, first: Int, last: Int)
  : ConversionPathRecordsConnection { edges, nodes, pageInfo, totalCount }
```

Per the directive's Q3 spec, the inner `touchpoints` array carries `creativeId campaignId touchTimestamp domain url sapid`.

**This is the only Relay-paginated, URL-bearing field in the live schema.**

---

## Other URL-Adjacent Fields Surveyed

- `campaignPageContext(date, filterBy: CampaignFilters) : CampaignPageContextPayload` — exists; introspection helper did not fully resolve inner fields, so URL availability is unconfirmed without a live test query against a known campaign.
- `inventoryPackages` — exists; suggestive name; not introspected (low priority on this round).
- `ctvPublishers` — exists; CTV-only.

Full list of 60 Query field names captured during introspection (preserved in tool output of session 2026-05-04 #001).

---

## Three Schema-Grounded Paths Forward

### Path α — `conversionPath`-based extraction

**What:** Use `conversionPath` directly. Cursor-paginate via `after`/`first`. Flatten each `ConversionPathRecord.touchpoints[]` into per-touch rows containing `(url, domain, creative_id, campaign_id, touch_timestamp, sapid, conversion_id, conversion_timestamp, revenue_usd)`. Dedup on `url` to produce the §1.4 `unique_urls.jsonl` artifact. HTTP HEAD validate per §1.4.

**Strengths:**
- Real Relay cursor pagination (matches §1.3 pagination intent literally).
- URL is a first-class field on the touchpoint.
- Schema is well-defined; query is straightforward to write.
- Directive already canonicalizes the field shape in Q3 — this just promotes Q3's role from "trajectory reconstruction" to "S0's URL source."

**Weaknesses:**
- **Sample is conversion-path-only.** Non-converting impressions never appear in `conversionPath`. The S1 4-rater label set produced from this stream will systematically over-represent bottom-of-funnel surfaces and under-represent top-of-funnel research/leisure pages. This biases the held-out fixture for criterion (ii) → Gate G1 closure may then validate a posture classifier on a non-representative URL distribution.
- The `INFORMATION_FORAGING` and `LEISURE_BROWSING` posture classes are exactly the classes most likely under-served by a conversion-only URL pull.

### Path β — `adDelivery` over date-window rotation + `campaignPageContext` augmentation

**What:** Pull `adDelivery(dataType: PERFORMANCE, date: { startDate, endDate }, granularity: AGGREGATE, filterBy: { advertiserId })` over rolling 7-day windows. Get domain-aggregate rows. Then call `campaignPageContext(date, filterBy: { campaignId })` for each active campaign in the window to discover URL-level page context.

**Strengths:**
- Population-level (every served campaign-day), not conversion-conditional. Better representativeness for posture-classifier training.

**Weaknesses:**
- `campaignPageContext` inner-field shape is unconfirmed. If it doesn't expose URL, this path collapses entirely.
- No cursor pagination at the `*Delivery` layer — would need to roll our own date-window iteration semantics.
- Higher API call count (one `campaignPageContext` per active-campaign-window).

### Path γ — Directive amendment via Claude Proper

**What:** Stop S0 build. Send this report to Claude Proper. Claude Proper amends directive §1.2 (and possibly §1.4–§1.6) against the real schema. Claude Proper writes the new S0 prompt for execution.

**Strengths:**
- Preserves §0.4 strict separation: Claude Proper makes the architectural call, not Claude Code.
- Result is a directive that matches reality, so subsequent slices don't re-encounter the same gap.
- The same mismatch likely affects S4 (permanent ingestion pipeline), which inherits S0's schema assumptions; better to fix at the directive layer once than to absorb the gap into S0 ad hoc.

**Weaknesses:**
- Slowest path. Adds a Claude-Proper round-trip before any S0 code lands.

---

## Recommendation

**Path γ.** Reasons:

1. The mismatch is large enough that S0 cannot ship literally as written. Each of α and β requires real architectural choices (which field, what pagination semantics, what to do about non-converting impressions, whether posture-class representativeness gates the choice) that the directive §0.4 explicitly assigns to Claude Proper, not Claude Code.
2. S4 (permanent ingestion pipeline) is the long-lived consequence. S0 is one-shot. Fixing the schema in the directive once means S4 inherits a clean spec. Fixing it ad-hoc in S0 means S4 may also drift.
3. The bias-vs-representativeness question (α's conversion-only bias on the 4-rater corpus → G1 validity) is a methodology-level decision that interacts with criterion (ii) gate authority. That's exactly the kind of decision the §0.4 separation was designed for.

**Pragmatic concession to velocity:** if Claude Proper's amendment is non-trivial, an interim Path α extraction can be authorized as a calibration-only artifact (not for G1 closure) so something runs in parallel with the amendment cycle. Flag clearly in artifact metadata that it's calibration-only.

---

## Schema Findings — Reproducibility Pointer

All findings produced by three introspection rounds executed against `https://api.stackadapt.com/graphql` on 2026-05-04 by `python3` heredoc invocation using the existing `StackAdaptGraphQLClient`. To reproduce: re-run the heredocs in session 2026-05-04 #001 (full content preserved in `docs/MEMORY.md` EVE block + this report's body). No code committed.

---

## Binding Amendment (Chris, 2026-05-04 supplement)

**Posture-class diversity audit — added to S0 §1.5/§1.7 + S1 §1.8 entry-condition.** This binds whichever path (α / β / γ) Claude Proper selects.

### S0 amendment

After URL extraction completes and `unique_urls.jsonl` is written:

1. **Run `URLPostureClassifier`** (`adam/intelligence/posture_five_class.py`, the canonical URL-tfidf 5-class classifier — Chris's resolution 2026-05-04) against `unique_urls.jsonl` to produce per-URL posture-class predictions in the 5-class taxonomy: `INFORMATION_FORAGING / TASK_COMPLETION / LEISURE_BROWSING / SOCIAL_CONSUMPTION / TRANSACTIONAL_COMPARISON` (canonical names at `posture_five_class.py:106`).
   - **Round-3 checkpoint caveat (must be inscribed in the S0 emitted summary artifact, not just here):** the URLPostureClassifier checkpoint as of 2026-05-04 is the round-3-pre-rotation model. Its held-out evaluation produced macro-AUC 0.7980 and top-1 0.22, with 49/50 predictions collapsed to `INFORMATION_FORAGING` (the default-class behavior that reopened criterion (ii) in the EVE 2026-05-02 session). Implications for the diversity audit:
     - The classifier defaults to `INFORMATION_FORAGING` under uncertainty. High `INFORMATION_FORAGING` counts in the audit may overstate actual `INFORMATION_FORAGING` representation in the URL corpus.
     - Low non-INFO counts may under-state actual non-INFO representation (because the broken classifier routes their probability mass to `INFORMATION_FORAGING` by default).
     - **The diversity gate's bias is conservative for our purpose.** If the gate fires (`posture_diversity_inadequate = true`), the input corpus is almost certainly diversity-inadequate. If the gate passes, the per-class counts should still be read with the round-3-default-to-INFO bias in mind — a passing audit is a minimum-bar signal, not a representativeness certification.
     - The summary artifact emitted by S0 must include this caveat verbatim in its diversity-audit section so the rater team and downstream consumers don't over-interpret the counts.
2. **Emit per-posture-class URL counts in the §1.5 summary `.md` artifact.** Five rows, one per posture class, with count + percentage of total unique URLs.
3. **Apply the diversity gate.** If any posture class has fewer than **30 URLs** (5-class minimum total = 150 URLs), the extraction is **diversity-inadequate**:
   - The summary `.md` artifact records `posture_diversity_inadequate: true` with per-class counts.
   - The `READY_FOR_RATER_WORKSHEET.flag` queue marker is still written, but with the additional machine-readable line `posture_diversity_inadequate=true` (key=value, one per line, plain text).
   - When the gate passes (all five classes ≥ 30), the flag content includes `posture_diversity_inadequate=false`.

### S1 entry-condition amendment

S1.1 (worksheet generation) **must read `READY_FOR_RATER_WORKSHEET.flag` and parse the `posture_diversity_inadequate` key** before producing any rater worksheet. If the value is `true`:

- S1 stops and surfaces a `QUESTION:` block per directive §0.3 naming the under-served posture classes and per-class counts.
- S1 does **not** generate the rater worksheet against the inadequate URL set.

### Empirical motivation

`INFORMATION_FORAGING` and `LEISURE_BROWSING` are the two classes most likely to be under-served by Path α's conversion-path bias (both are non-conversion-y posture profiles — research-mode and entertainment-mode). They were also the under-classified classes in the round-3 held-out evaluation that reopened criterion (ii) (49/50 collapsed to `INFORMATION_FORAGING` — the classifier defaulted to one class because the others lacked sufficient calibration evidence). Pulling another corpus that under-represents these two classes would re-introduce the same gate-validity defect.

### Implementation note for whichever path wins

- **Path α (conversionPath):** the diversity gate is the primary integrity check. Expect `INFORMATION_FORAGING` and `LEISURE_BROWSING` to fail the 30-URL minimum on a pure conversion-path pull; the gate will likely fire `posture_diversity_inadequate=true` on the first attempt, which is the correct signal that Path α alone is insufficient.
- **Path β (adDelivery + campaignPageContext):** representative-by-design, but the diversity gate still serves as a forcing function for sample-size adequacy per class.
- **Path γ (directive amendment):** Claude Proper inherits this amendment as part of the spec.

---

## Status (per directive §0.3)

- **State:** BLOCKED
- **Slice ID:** S0
- **Commit SHA:** none for S0 (`9936cf6` is the directive transition only)
- **Test-suite delta:** +0 / -0 / =4380+ (no code touched)
- **Next concrete action:** Chris pastes this report (including the binding amendment above) into Claude Proper. Claude Proper adjudicates α / β / γ + writes the amended S0 prompt that incorporates the diversity-gate amendment.
- **Open QUESTIONs:**
  - **QUESTION 3:** Which path (α / β / γ) for S0 against the live StackAdapt GraphQL schema? Or other?
  - **(Not a question — binding constraint):** Whichever path is chosen, posture-class diversity audit + S1 entry-condition gate per the amendment above.
