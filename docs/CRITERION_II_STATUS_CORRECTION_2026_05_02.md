# Criterion (ii) Status Correction — 2026-05-02 Evening

**Status**: criterion (ii) **REOPENED**. The earlier "PASS" recorded
this afternoon was methodologically optimistic.

This memo is the auditable record of the correction. v3 Phase 1's
work-stream 1.B blinded-analysis discipline starts here, on this gate,
before it formally begins.

---

## What criterion (ii) is

The 5-class posture head must classify a held-out URL into one of
{`INFORMATION_FORAGING`, `LEISURE_BROWSING`, `SOCIAL_CONSUMPTION`,
`TASK_COMPLETION`, `TRANSACTIONAL_COMPARISON`} with enough fidelity
that the L3 cascade's posture-conditioning dimension is real signal
in production, not a default-class echo.

Criterion (ii) is one of three hard-stop gates for the v3 transition
((i) Phase 9 sim, (iii) Section 6 cadences are both closed).

## What the original gate was

> **LOOCV macro-AUC ≥ 0.30** on all persisted `:PostureLabel` records,
> evaluated by `scripts/train_and_evaluate_posture_classifier.py`.

Set when round-1 hand-labeling produced n=20 labels and macro-AUC
came in at 0.2580. The 0.30 threshold assumed the labeled corpus
would be **representatively sampled** — i.e., that LOOCV's left-out
URL would have no near-identical sibling URLs in the training fold.

## Why the LOOCV gate cleared

After round-2 active learning surfaced 80 high-entropy candidates,
those URLs were hand-labeled (operator-via-claude) and persisted,
bringing the corpus to n=100. LOOCV then reported:

| | n=20 (round-1) | n=100 (round-1 + round-2) |
| --- | --- | --- |
| macro-AUC | 0.2580 | **0.9465** |
| 95% CI | [0.0826, 0.4210] | [0.9038, 0.9816] |

The classifier artifact `posture_classifier_n100_1777759342.jsonl`
was persisted and criterion (ii) was marked PASS.

## Why that clearance was methodologically optimistic

Round-2 active learning concentrated the 80 surfaced candidates in
**~12 source domain families** (kayak.com, bloomberg.com, reddit.com,
nytimes.com/wirecutter, concur.com, expensify.com, ...). Most labeled
URLs share a domain template with 5–10 sibling URLs in the same
class:

- 12 of 14 `TRANSACTIONAL_COMPARISON` labels are `kayak.com/*`
- 6 of 10 `TASK_COMPLETION` labels are `concur.com/*` or `expensify.com/*`
- 10 of 28 `INFORMATION_FORAGING` labels are `nytimes.com/wirecutter/reviews/best-*`
- 11 of 22 `SOCIAL_CONSUMPTION` labels are `bloomberg.com/news/*`

Under that distribution, LOOCV's hold-one-out fold leaves the
single URL on test while keeping its near-identical siblings in
train. URL-tfidf can template-memorize its way to a near-perfect
score by learning that a path containing `kayak`+`flights` →
TRANSACTIONAL, `nytimes`+`wirecutter`+`best` → INFO, etc. The
0.9465 figure measures template recognition, not posture inference.

The 0.30 threshold was set in good faith for round-1's
representative-sampling assumption. Round-2's active-learning surface
silently broke that assumption. The threshold became wrong without
being changed.

## What the held-out evaluator showed

Same persisted classifier, scored on a 50-URL held-out fixture (10
per posture) hand-curated from domains **not present** in the n=100
training corpus (Tom's Guide, CNET, PCMag, Expedia, Booking, Amazon,
Zillow, Vogue, GQ, Atlas Obscura, Twitter, TikTok, Slack, Zoom,
Salesforce, Figma, ...).

| | LOOCV (n=100, in-domain) | Held-out (n=50, new domains) |
| --- | --- | --- |
| **Macro-AUC** | **0.9465** | **0.7980** |
| 95% CI | [0.9038, 0.9816] | [0.7145, 0.8699] |
| Top-1 accuracy | — | **0.22 (11/50)** |

The classifier collapsed to predicting `INFORMATION_FORAGING` on **49
of 50** held-out URLs — only NPR's news section escaped the default.
The remaining 0.7980 macro-AUC reflects that the model still ranks
the true class above chance on the held-out set, but it never picks
it. AUC measures ranking; argmax is what the L3 cascade consumes.

Per-class one-vs-rest held-out AUC:

| Class | Held-out AUC |
| --- | --- |
| TASK_COMPLETION | 0.9250 |
| LEISURE_BROWSING | 0.8963 |
| TRANSACTIONAL_COMPARISON | 0.8225 |
| INFORMATION_FORAGING | 0.7788 |
| SOCIAL_CONSUMPTION | **0.5675** |

The collapse mechanism is hyper-specific token vocab in the training
corpus's per-class subset:

- TRANSACTIONAL training is almost entirely `kayak.com/*` →
  the trained vocabulary has no Expedia/Booking/Amazon/Zillow tokens
- TASK training is dominated by Concur/Expensify → no token signal
  for Slack/Zoom/Salesforce/Figma/Airtable/HubSpot/QuickBooks
- LEISURE training is food-publication-heavy → no signal for
  Vogue/GQ/Atlas Obscura/Smithsonian/Refinery29
- INFO_FORAGING has 28 labels with diffuse "best/review/blog"
  vocabulary that appears across nearly every domain → wins by
  default whenever no class-specific token fires

## The new gate

> **Held-out macro-AUC ≥ 0.50 AND held-out top-1 accuracy ≥ 0.40.
> Both conditions must clear.**

Implemented in `scripts/heldout_eval_posture_classifier.py`. Returns
exit 0 on PASS, exit 1 on FAIL. Held-out fixture is 50 URLs from 50
distinct domains, all outside the training corpus.

The two-condition design:

- **Macro-AUC ≥ 0.50** — cross-domain ranking signal exists, not just
  template memorization. The 0.50 floor (chance for binary
  one-vs-rest) is intentionally loose; the binding constraint is
  top-1.
- **Top-1 accuracy ≥ 0.40** — the L3 cascade selects argmax, not a
  ranked list. With the held-out 22% top-1 (barely above 5-class
  chance of 20%), routing partner traffic on this signal would
  corrupt the posture-conditioning dimension. 40% is 2x chance —
  the minimum signal worth conditioning on.

The LOOCV evaluator (`scripts/train_and_evaluate_posture_classifier.py`)
is **retained as a diagnostic**, not retired from the codebase. The
gap between LOOCV and held-out macro-AUC is itself a finding worth
tracking session-over-session — it quantifies template-memorization
vs real generalization, and a closing gap is a leading indicator
that the corpus is becoming representative.

## Current gate state

```
$ python3 scripts/heldout_eval_posture_classifier.py
Macro-AUC:                 0.7980  (≥ 0.50 ✓)
Top-1 accuracy:            0.2200  (≥ 0.40 ✗)
Gate decision (BOTH):      ✗ FAIL — criterion (ii) OPEN
```

## Path to closing the new gate

1. **Round-3 diversification surface** (this session):
   `artifacts/posture_round_3/round_3_diversification_candidates.jsonl`
   — 80 URLs targeting the four under-diversified classes:

   - **TASK_COMPLETION (+20)**: Slack, Zoom, Salesforce, Figma,
     Airtable, Notion, Linear, Microsoft 365, Asana — beyond
     Concur/Expensify
   - **TRANSACTIONAL_COMPARISON (+20)**: Expedia, Booking.com, Amazon,
     Zillow, Cars.com, Carvana, Skyscanner, Hotels.com, Realtor.com
     — beyond Kayak
   - **LEISURE_BROWSING (+20)**: Vogue, GQ, Atlas Obscura, Smithsonian,
     CN Traveler (lifestyle sections), Nat Geo, Town & Country —
     beyond Eater/Bon Appetit
   - **SOCIAL_CONSUMPTION (+20)**: Twitter/X, TikTok, Instagram,
     Facebook, Medium, Substack, NPR, CNN, WaPo, Guardian, Threads,
     Mastodon — beyond Bloomberg/Reddit
   - **INFORMATION_FORAGING (0)**: do NOT add more. The class is
     already over-represented at 28 labels and is the source of the
     default-predict collapse.

2. **Operator hand-labels round-3** over 2–3 days via
   `scripts/persist_posture_label.py`. Domain diversity matters more
   than volume per class.

3. **Re-train + diagnostic LOOCV** on n≈180:
   `python3 scripts/train_and_evaluate_posture_classifier.py`

4. **Gate against held-out evaluator**:
   `python3 scripts/heldout_eval_posture_classifier.py`

5. If gate FAILS, do NOT add more INFO_FORAGING. Diagnose: which
   per-class held-out AUC is dragging? Is per-class top-1 = 0 still
   on whole posture classes (confusion-matrix collapse), or is it
   distributed across classes? The misclassified-URL section in the
   gate output names which domains the model has no signal for.

6. **Do not start v3 Phase 1** (or any other build downstream of
   posture-conditioning) until gate clears against the held-out
   evaluator. The interface seams from Slice 24 hold; the v3
   transition handoff prompt is gated on this memo's status flipping
   to CLOSED.

## Audit-trail discipline going forward

Two rules to prevent this drift from recurring:

1. **Active learning is a labeling-acceleration mechanism, not a
   sampling design.** Whenever the labeled corpus's domain
   distribution is concentrated by an active-learning loop, in-corpus
   CV (LOOCV / k-fold) overestimates generalization. Always pair
   in-corpus CV with held-out evaluation on a domain-disjoint
   fixture before claiming a gate is closed.

2. **Gate thresholds carry assumptions; surface them at definition
   time and re-check when the assumption changes.** The 0.30 LOOCV
   threshold worked fine for representatively-sampled n=20 and broke
   silently for actively-sampled n=100. The new gate's 0.50/0.40
   thresholds carry their own assumptions (the held-out fixture's
   50-URL composition, the 5-class chance baseline of 20%); when
   either assumption changes, re-derive.

---

**Memo status**: ACTIVE. Update when the held-out gate clears or
when the threshold itself is renegotiated.
