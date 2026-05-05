# S0 Historical URL Extraction — Summary (2026-05-04)

**Slice:** S0 (amended)  
**Advertiser:** LUXY (id=122463)  
**LUXY campaigns visible:** 12  
**Extraction window:** 365 days  

## 1. Source Distribution

- `conversion_path`: 6 unique URLs (100.0% of total) from 285 raw rows.
- `pixel_postback`: **N/A** — no impression-time pixel log shipped on LUXY pilot. Documented as future S4 ingestion-pipeline requirement.
- `campaign_page_context`: 0 unique URLs (0.0% of total) from 0 raw rows.

## 2. URL Validation

- Total unique URLs after dedup: **6**
- `validated_live=true`: **6**
- `validated_live=false`: **0**


## 3. Domain Distribution

- Total unique URL-bearing domains: **1**
- Top 20 by served-impression weight:

  - `luxyride.com` — weight=1213

- Domains with `< 10` weighted impressions (`low_confidence_inventory`): **0**

## 4. Coverage Gap

Publisher domains observed in `conversion_path` records but for which we have NO URL captured (= S4 ingestion-pipeline gap):

- `accuweather.com`
- `acleanbake.com`
- `allmusic.com`
- `aol.com`
- `aternos.org`
- `baseball-reference.com`
- `billyparisi.com`
- `blueseatblogs.com`
- `bostonherald.com`
- `brides.com`
- `broccyourbody.com`
- `bundle/b01j62q632`
- `bundle/com.att.tv`
- `bundle/com.hulu.plus`
- `bundle/com.pixel.art.coloring.color.number`
- `bundle/com.tmobile.m1`
- `bundle/directv.stb`
- `bundle/fubo.firetv.screen`
- `bundle/g14363001012`
- `bundle/g15147002586`
- `buttermilkbysam.com`
- `buzzfeed.com`
- `cafedelites.com`
- `cardgames.io`
- `cbsnews.com`
- `cbssports.com`
- `celebritynetworth.com`
- `clevelandclinic.org`
- `closerweekly.com`
- `cnbc.com`
- `cnn.com`
- `cults3d.com`
- `dailyvoice.com`
- `deadline.com`
- `dictionary.com`
- `discoveryplus.com`
- `disneyplus.com`
- `e46fanatics.com`
- `earth.com`
- `eatingbirdfood.com`
- `espn.com`
- `ew.com`
- `ewrestlingnews.com`
- `familydestinationsguide.com`
- `fandom.com`
- `fangraphs.com`
- `feastingathome.com`
- `fool.com`
- `foolproofliving.com`
- `fortune.com`
- ... and 152 more

## 5. Posture-Class Diversity Audit

Classifier artifact: `artifacts/posture_classifier/posture_classifier_n100_1777759342.jsonl`

Classifier classes (from artifact): `['INFORMATION_FORAGING', 'LEISURE_BROWSING', 'SOCIAL_CONSUMPTION', 'TASK_COMPLETION', 'TRANSACTIONAL_COMPARISON']`

URLs scored: **6**

Per-class counts:
  - `INFORMATION_FORAGING`: **6** (minimum 30) ✗
  - `TASK_COMPLETION`: **0** (minimum 30) ✗
  - `LEISURE_BROWSING`: **0** (minimum 30) ✗
  - `SOCIAL_CONSUMPTION`: **0** (minimum 30) ✗
  - `TRANSACTIONAL_COMPARISON`: **0** (minimum 30) ✗

### Required caveat (verbatim per binding amendment)

> The posture predictions in this audit come from the round-3-pre-rotation `URLPostureClassifier` checkpoint, which produced held-out macro-AUC 0.7980 with top-1 0.22 and 49/50 cases collapsed to `INFORMATION_FORAGING`. These predictions are conservative-for-purpose: a firing diversity gate (= inadequate corpus signal) is high-confidence, but a passing gate clears the minimum bar with per-class counts that carry default-to-`INFORMATION_FORAGING` bias. Treat per-class counts as lower bounds for non-`INFORMATION_FORAGING` classes; treat the `INFORMATION_FORAGING` count as an upper bound. The audit's purpose is corpus-diversity gating, not posture-class assignment.

## 6. Diversity Gate Verdict

**FAIL** — under_threshold_classes=['INFORMATION_FORAGING', 'TASK_COMPLETION', 'LEISURE_BROWSING', 'SOCIAL_CONSUMPTION', 'TRANSACTIONAL_COMPARISON']

Under-threshold classes:
  - `INFORMATION_FORAGING`: count=6, shortfall=24
  - `TASK_COMPLETION`: count=0, shortfall=30
  - `LEISURE_BROWSING`: count=0, shortfall=30
  - `SOCIAL_CONSUMPTION`: count=0, shortfall=30
  - `TRANSACTIONAL_COMPARISON`: count=0, shortfall=30

Per directive §F + §I: this is a valid S0 closure state. The artifact is delivered; S1's worksheet generator will read the flag and surface a QUESTION before producing the rater corpus.

## 7. Bias Caveat (Calibration vs Gate-Grade)

`conversion_path` source contributes **100.0%** of unique URLs (> 70% threshold). Corpus declared `calibration_grade=true` regardless of diversity verdict. **NOT sufficient to close Gate G1.** Useful for S1 worksheet-generator tooling iteration only.
