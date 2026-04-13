# Session Prompts — April 12-13, 2026

Every analysis, script, and command used in this session, in order.
Run these from the project root: `/Users/chrisnocera/Sites/adam-platform/`

---

## 1. Cross-Category Archetype Validation (Airline Data)

**Analyze premium airline annotations for archetype validation:**
```bash
python3 scripts/analyze_airline_premium_archetypes.py
```
This filters 105K airline annotations to premium airline satisfied travelers (rating >= 7), maps to bilateral edge format, computes edges against LUXY Ride ad-side, and runs archetype clustering.

**Load airline edges into Neo4j:**
```bash
source .env
python3 scripts/load_airline_edges_to_neo4j.py
```
Loads 11,805 cross-category edges with archetype classification.

---

## 2. Derive Data-Based Fulfillment Strengths

**Compute which goals actually drive conversion per archetype:**
```bash
python3 -c "
import json, numpy as np
from collections import defaultdict

with open('reviews_other/airline_reviews/airline_annotations_all.json') as f:
    all_ann = json.load(f)

# Premium airlines
PREMIUM = {
    'Qatar Airways', 'Emirates', 'Singapore Airlines', 'Cathay Pacific Airways',
    'ANA All Nippon Airways', 'EVA Air', 'Hainan Airlines', 'Garuda Indonesia',
    'Asiana Airlines', 'Japan Airlines', 'Korean Air', 'Thai Airways',
    'Swiss International Air Lines', 'Lufthansa', 'British Airways',
    'Virgin Atlantic Airways', 'Air New Zealand', 'Etihad Airways',
    'Turkish Airlines', 'KLM Royal Dutch Airlines', 'Qantas Airways',
    'Finnair', 'Austrian Airlines', 'SAS Scandinavian Airlines',
    'Air France', 'Delta Air Lines',
}
def is_premium(a):
    return any(pa.lower() in a.lower() or a.lower() in pa.lower() for pa in PREMIUM)

# Moderate segment (rating 4-6) — where there's actual variance
moderate = [a for a in all_ann if is_premium(a.get('airline','')) and 4 <= a.get('rating',0) <= 6]
print(f'Moderate segment: {len(moderate)} travelers')

dims = ['openness', 'conscientiousness', 'extraversion', 'agreeableness',
        'neuroticism', 'promotion_focus', 'prevention_focus',
        'need_for_cognition', 'negativity_bias', 'reactance',
        'brand_trust', 'spending_pain', 'self_monitoring',
        'emotional_expressiveness', 'social_proof_reliance',
        'anchor_susceptibility', 'status_seeking', 'detail_orientation']

# For each archetype, find people matching the interaction effect
# and compute which dimensions separate their converters from non-converters
archetype_defs = {
    'trusting_loyalist': {'agreeableness': ('>', 0.6), 'brand_trust': ('>', 0.6)},
    'dependable_loyalist': {'brand_trust': ('>', 0.6), 'conscientiousness': ('>', 0.6)},
    'consensus_seeker': {'agreeableness': ('>', 0.5), 'social_proof_reliance': ('>', 0.4)},
    'explorer': {'openness': ('>', 0.6), 'promotion_focus': ('>', 0.5)},
    'prevention_planner': {'conscientiousness': ('>', 0.6), 'prevention_focus': ('>', 0.6)},
    'reliable_cooperator': {'conscientiousness': ('>', 0.6), 'agreeableness': ('>', 0.6)},
    'careful_truster': {'brand_trust': ('>', 0.5), 'prevention_focus': ('>', 0.5)},
}

for arch, defn in archetype_defs.items():
    matches = [a for a in moderate if all(
        a.get(d, 0.5) > t if op == '>' else a.get(d, 0.5) < t
        for d, (op, t) in defn.items()
    )]
    conv = [a for a in matches if a.get('outcome') in ('satisfied', 'evangelized')]
    nonc = [a for a in matches if a.get('outcome') in ('warned', 'regret')]
    if len(conv) < 5: continue
    
    print(f'\n{arch}: {len(matches)} matches, conv={len(conv)}, nonconv={len(nonc)}')
    for dim in dims:
        cv = np.mean([a.get(dim, 0.5) for a in conv])
        nv = np.mean([a.get(dim, 0.5) for a in nonc]) if nonc else np.mean([a.get(dim, 0.5) for a in moderate])
        gap = cv - nv
        if abs(gap) > 0.03:
            print(f'  {dim:<25} gap={gap:+.3f}')
"
```

---

## 3. Domain Crawl & Whitelist Generation

**Full crawl pipeline (homepage + article-level):**
```bash
python3 scripts/crawl_domains_for_targeting.py
```

This:
1. Defines 108 domains across 8 categories
2. Crawls each homepage
3. For each successful domain, finds article URLs via RSS or link extraction
4. Crawls up to 8 articles per domain
5. Scores each article's real text through the Goal Activation Model
6. Computes crossover scores per archetype
7. Generates per-archetype whitelist CSVs

**To add more domains:** Edit the `DOMAIN_UNIVERSE` dict in the script.
**To adjust sensitivity:** Change `MIN_CROSSOVER` (default 0.08).

---

## 4. Goal Activation Model Test

**Score any page text for goal activation:**
```bash
python3 -c "
from adam.intelligence.goal_activation import score_page_goal_activation, rank_archetypes_for_page

text = '''Your text here — paste any article content'''

result = score_page_goal_activation(text, page_affect_valence=0.5)
print(f'Dominant goal: {result.dominant_goal} ({result.dominant_strength:.3f})')
for goal, score in sorted(result.goal_scores.items(), key=lambda x: -x[1]):
    if score > 0.05:
        print(f'  {goal}: {score:.3f}')

rankings = rank_archetypes_for_page(result)
print(f'\nBest archetypes for this page:')
for arch, score in rankings[:5]:
    print(f'  {arch}: {score:.3f}')
"
```

---

## 5. Test Server Endpoints

**Health check:**
```bash
curl -s https://focused-encouragement-production.up.railway.app/health/ready
```

**Creative intelligence with goal activation:**
```bash
curl -s -X POST https://focused-encouragement-production.up.railway.app/api/v1/stackadapt/creative-intelligence \
  -H "Content-Type: application/json" \
  -d '{"segment_id":"informativ_trusting_loyalist_social_proof_luxury_transportation_t1","page_title":"Top Executives Trust Reliable Partners","device_type":"desktop","time_of_day":9}'
```

**Signals health:**
```bash
curl -s https://focused-encouragement-production.up.railway.app/api/v1/signals/health
```

**Ops dashboard:**
```bash
curl -s https://focused-encouragement-production.up.railway.app/api/v1/ops/recommendations
```

---

## 6. Deploy to Railway

**Push code to GitHub (triggers auto-deploy):**
```bash
git push origin main
```

**Or force-push from branch:**
```bash
git push origin 2026-01-26-fxqi:main -f
```

**Manual redeploy (same code, new instance):**
```bash
npx @railway/cli redeploy --service focused-encouragement
```

**Check logs:**
```bash
npx @railway/cli logs --service focused-encouragement --latest -n 50
```

---

## 7. Neo4j Seed (if needed)

```bash
source .env
python3 scripts/seed_neo4j_pilot.py
```

---

## 8. Cognitive Bias Analysis

**Extract goal-relevant markers from the 140 bias spreadsheet:**
```bash
python3 -c "
import openpyxl, json, re

wb = openpyxl.load_workbook('Cognitive Biases/Cognitive Bias with Code 2.xlsx')
ws = wb['Sheet1']

for row_idx in range(2, ws.max_row + 1):
    name = ws.cell(row=row_idx, column=1).value
    code = ws.cell(row=row_idx, column=2).value or ''
    desc = ws.cell(row=row_idx, column=3).value or ''
    print(f'{name}: {len(code)} chars of code, {desc[:80]}')
"
```

---

## Key Files Created This Session

| File | Purpose |
|------|---------|
| `adam/intelligence/goal_activation.py` | Goal Activation Model (scoring + learning) |
| `scripts/crawl_domains_for_targeting.py` | Domain crawler for whitelist generation |
| `scripts/analyze_airline_premium_archetypes.py` | Cross-category archetype validation |
| `scripts/load_airline_edges_to_neo4j.py` | Load airline edges into Neo4j |
| `data/derived_fulfillment_strengths.json` | Data-derived goal-archetype fulfillment |
| `data/deep_article_crawl.json` | 370 article crawl results |
| `data/domain_universe.json` | 108 domains across 8 categories |
| `docs/NONCONSCIOUS_GOAL_PRIMING_RESEARCH.md` | Research synthesis |
| `campaigns/ridelux_v6/START_HERE.md` | Becca's guide |
| `static/portal/index.html` | Sam's portal home page |
| `static/portal/overview.html` | Full investor presentation |
