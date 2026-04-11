#!/usr/bin/env python3
"""Build the LUXY Ride campaign handoff HTML document from bilateral data."""

import json
import csv
import html as html_mod
from pathlib import Path

CAMPAIGNS = Path('campaigns/ridelux')

# Load all data
with open(CAMPAIGNS / 'stackadapt_campaign_structure.json') as f:
    campaign = json.load(f)

briefs = {}
for name in ['status_seeker', 'easy_decider', 'careful_truster']:
    p = CAMPAIGNS / f'creative_brief_{name}.json'
    if p.exists():
        with open(p) as f:
            briefs[name] = json.load(f)

with open(CAMPAIGNS / 'bid_strategy.json') as f:
    bid = json.load(f)
with open(CAMPAIGNS / 'frequency_capping_strategy.json') as f:
    freq = json.load(f)
with open(CAMPAIGNS / 'negative_targeting.json') as f:
    neg = json.load(f)

retarget = {}
if (CAMPAIGNS / 'retargeting_strategy.json').exists():
    with open(CAMPAIGNS / 'retargeting_strategy.json') as f:
        retarget = json.load(f)

domains = []
with open(CAMPAIGNS / 'domain_whitelist_ALL.csv') as f:
    for row in csv.DictReader(f): domains.append(row)
blacklist = []
with open(CAMPAIGNS / 'domain_blacklist.csv') as f:
    for row in csv.DictReader(f): blacklist.append(row)
ctv = []
with open(CAMPAIGNS / 'ctv_targeting_list.csv') as f:
    for row in csv.DictReader(f): ctv.append(row)
dayparting = []
with open(CAMPAIGNS / 'dayparting_schedule.csv') as f:
    for row in csv.DictReader(f): dayparting.append(row)
measurement = []
with open(CAMPAIGNS / 'measurement_framework.csv') as f:
    for row in csv.DictReader(f): measurement.append(row)

def esc(s):
    return html_mod.escape(str(s)) if s else ''

COLORS = {
    'status_seeker': '#3b82f6',
    'easy_decider': '#10b981',
    'careful_truster': '#f59e0b',
    'skeptical_analyst': '#6b7280',
    'disillusioned': '#6b7280',
}

def track_label(name):
    return name.replace('_', ' ').title()

def brief_section(name):
    b = briefs.get(name, {})
    t = campaign['tracks'].get(name, {})
    color = COLORS.get(name, '#6b7280')

    headlines = b.get('headlines', [])
    body_copies = b.get('body_copies', [])
    ctas = b.get('ctas', [])
    say = b.get('what_to_say', [])
    dont_say = b.get('what_not_to_say', [])

    headline_html = ''.join(f'<div class="headline-card">{esc(h)}</div>' for h in headlines[:5])

    body_html = ''
    for bc in body_copies[:3]:
        if isinstance(bc, dict):
            body_html += f'''<div class="copy-block">
                <div class="copy-approach">{esc(bc.get("approach",""))}</div>
                <div class="copy-rationale">{esc(bc.get("rationale",""))}</div>
                <div class="copy-text">{esc(bc.get("copy",""))}</div>
            </div>'''

    cta_html = ''.join(f'<span class="cta-pill">{esc(c)}</span>' for c in ctas[:3])
    say_html = ''.join(f'<li>{esc(s)}</li>' for s in say)
    dont_html = ''.join(f'<li>{esc(s)}</li>' for s in dont_say)

    bi = t.get('bilateral_intelligence', {})
    helps = bi.get('seller_helps', [])
    hurts = bi.get('seller_hurts', [])
    align = bi.get('alignment_drivers', [])

    helps_html = ''.join(f'<li><strong>{esc(s.get("dim",""))}</strong> (r={s.get("r",0):+.3f})</li>' for s in helps[:5])
    hurts_html = ''.join(f'<li><strong>{esc(s.get("dim",""))}</strong> (r={s.get("r",0):+.3f})</li>' for s in hurts[:5])
    align_html = ''.join(f'<li><strong>{esc(a.get("dim",""))}</strong> (r={a.get("r",0):+.3f}, conv={a.get("conv",0):.3f} vs fail={a.get("fail",0):.3f})</li>' for a in align[:5])

    return f'''
    <div class="brief-section" style="border-left:4px solid {color}">
        <h3 style="color:{color}">{track_label(name)}</h3>
        <p style="font-size:14px;margin-bottom:12px">{esc(t.get("description",""))}</p>
        <div class="brief-meta">
            <div><strong>Sample:</strong> {t.get("sample_size","")} edges ({t.get("pct_of_market","")}% of market)</div>
            <div><strong>Conversion:</strong> {t.get("conversion_rate",0):.1%}</div>
            <div><strong>Budget:</strong> {t.get("budget_allocation_pct","")}%</div>
            <div><strong>Bid:</strong> {t.get("bid_multiplier",1.0)}x</div>
            <div><strong>Freq Cap:</strong> {t.get("frequency_cap",{}).get("max_per_day","")}/day, {t.get("frequency_cap",{}).get("max_per_week","")}/week</div>
            <div><strong>Primary:</strong> {esc(b.get("primary_mechanism",""))}</div>
        </div>

        <div class="insight-callout"><strong>Bilateral Evidence:</strong> {esc(b.get("primary_evidence",""))}</div>
        <div class="insight-callout" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.2)"><strong>Anti-Mechanism (hurts conversion):</strong> {esc(b.get("anti_evidence",""))}</div>

        <h4>Seller Dims That HELP Conversion</h4>
        <ul style="font-size:13px">{helps_html if helps_html else '<li>No significant correlations at p<0.05 (cluster may be too uniform)</li>'}</ul>
        <h4>Seller Dims That HURT Conversion</h4>
        <ul style="font-size:13px">{hurts_html if hurts_html else '<li>No significant correlations</li>'}</ul>
        <h4>Alignment Dimensions That Predict Conversion</h4>
        <ul style="font-size:13px">{align_html}</ul>

        <h4>Headline Directions</h4>
        <div class="headline-grid">{headline_html}</div>
        <h4>Body Copy Approaches</h4>
        {body_html}
        <h4>Call-to-Action Options</h4>
        <div class="cta-row">{cta_html}</div>

        <div class="two-col">
            <div class="do-col"><h4 class="green-header">What to Say</h4><ul>{say_html}</ul></div>
            <div class="dont-col"><h4 class="red-header">What NOT to Say</h4><ul>{dont_html}</ul></div>
        </div>
    </div>'''


# Domain table
def domain_table():
    cols = list(domains[0].keys()) if domains else []
    th = ''.join(f'<th>{esc(c)}</th>' for c in cols)
    rows = ''.join('<tr>' + ''.join(f'<td>{esc(d.get(c,""))}</td>' for c in cols) + '</tr>' for d in domains)
    return f'<table><tr>{th}</tr>{rows}</table>'

# Dayparting
def dayparting_table():
    rows = ''
    for dp in dayparting:
        track = dp.get('track', '')
        color = COLORS.get(track, '#6b7280')
        rows += f'<tr><td>{esc(dp.get("hours",""))}</td><td>{esc(dp.get("day_type",""))}</td><td style="color:{color}">{track_label(track)}</td><td>{esc(dp.get("bid_multiplier",""))}</td><td style="font-size:12px">{esc(dp.get("reason",""))}</td></tr>'
    return f'<table><tr><th>Hours</th><th>Day</th><th>Track</th><th>Multiplier</th><th>Reason</th></tr>{rows}</table>'


# ── ASSEMBLE HTML ──

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LUXY Ride — Bilateral Intelligence Campaign Brief</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
:root {{ --bg:#0a0e1a; --surface:#111827; --surface2:#1a2236; --border:#2a3548;
  --text:#e2e8f0; --dim:#8892a4; --accent:#3b82f6; --green:#10b981; --red:#ef4444;
  --amber:#f59e0b; --purple:#8b5cf6; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--text); line-height:1.7; }}
.page {{ max-width:1100px; margin:0 auto; padding:0 40px; }}
.cover {{ min-height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; border-bottom:1px solid var(--border); }}
.cover .logo {{ font-size:14px; letter-spacing:6px; text-transform:uppercase; color:var(--accent); margin-bottom:40px; }}
.cover h1 {{ font-size:42px; font-weight:300; margin-bottom:8px; }}
.cover h1 strong {{ font-weight:700; }}
.cover .subtitle {{ font-size:18px; color:var(--dim); margin-bottom:40px; }}
.cover .meta {{ font-size:13px; color:var(--dim); line-height:2; }}
.cover .confidential {{ margin-top:60px; font-size:11px; letter-spacing:2px; text-transform:uppercase; color:var(--red); opacity:0.7; }}
.toc {{ padding:60px 0; border-bottom:1px solid var(--border); }}
.toc h2 {{ font-size:24px; margin-bottom:24px; }}
.toc-list {{ list-style:none; }}
.toc-list li {{ padding:8px 0; border-bottom:1px solid rgba(42,53,72,0.3); }}
.toc-list li a {{ color:var(--text); text-decoration:none; font-size:15px; }}
.toc-list li a:hover {{ color:var(--accent); }}
.toc-list .num {{ color:var(--dim); margin-right:12px; font-weight:600; }}
section {{ padding:60px 0; border-bottom:1px solid var(--border); }}
section h2 {{ font-size:28px; font-weight:600; margin-bottom:8px; }}
section .section-sub {{ font-size:14px; color:var(--dim); margin-bottom:30px; }}
section h3 {{ font-size:20px; margin:30px 0 12px; }}
section h4 {{ font-size:14px; color:var(--dim); text-transform:uppercase; letter-spacing:0.5px; margin:20px 0 8px; }}
.stat-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:16px; margin:20px 0; }}
.stat-card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:20px; text-align:center; }}
.stat-card .val {{ font-size:32px; font-weight:700; }}
.stat-card .label {{ font-size:12px; color:var(--dim); margin-top:4px; }}
.insight-callout {{ background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.2); border-radius:8px; padding:16px 20px; margin:16px 0; font-size:14px; line-height:1.7; }}
.brief-section {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:28px; margin:20px 0; }}
.brief-meta {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:8px; margin:12px 0 20px; font-size:13px; }}
.brief-meta div {{ padding:6px 10px; background:var(--surface2); border-radius:4px; }}
.headline-grid {{ display:grid; gap:8px; margin:8px 0 16px; }}
.headline-card {{ background:var(--surface2); border:1px solid var(--border); border-radius:6px; padding:12px 16px; font-size:14px; font-style:italic; }}
.copy-block {{ background:var(--surface2); border-radius:8px; padding:16px 20px; margin:10px 0; }}
.copy-approach {{ font-weight:600; font-size:14px; margin-bottom:4px; color:var(--accent); }}
.copy-rationale {{ font-size:12px; color:var(--dim); margin-bottom:10px; }}
.copy-text {{ font-size:14px; line-height:1.7; border-left:3px solid var(--border); padding-left:14px; }}
.cta-row {{ display:flex; gap:10px; margin:8px 0; flex-wrap:wrap; }}
.cta-pill {{ background:var(--accent); color:white; padding:8px 20px; border-radius:6px; font-size:13px; font-weight:600; }}
.two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:16px; }}
.do-col,.dont-col {{ padding:16px; background:var(--surface2); border-radius:8px; }}
.do-col ul,.dont-col ul {{ padding-left:18px; font-size:13px; }}
.do-col li,.dont-col li {{ margin:6px 0; }}
.green-header {{ color:var(--green) !important; }}
.red-header {{ color:var(--red) !important; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }}
th {{ text-align:left; padding:10px 12px; font-size:11px; color:var(--dim); text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid var(--border); background:var(--surface); }}
td {{ padding:8px 12px; border-bottom:1px solid rgba(42,53,72,0.3); }}
tr:hover td {{ background:rgba(59,130,246,0.03); }}
.footer {{ padding:30px 0; text-align:center; font-size:11px; color:var(--dim); }}
@media print {{ body {{ background:white; color:#1a1a1a; }} section {{ page-break-inside:avoid; }} }}
@media (max-width:900px) {{ .two-col {{ grid-template-columns:1fr; }} .brief-meta {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>

<div class="cover">
  <div class="logo">INFORMATIV</div>
  <h1><strong>Bilateral Intelligence</strong> Campaign Brief</h1>
  <div class="subtitle">Data-Driven Psycholinguistic Targeting for LUXY Ride</div>
  <div class="meta">
    <div><strong>Brand:</strong> LUXY Ride — luxyride.com</div>
    <div><strong>Platform:</strong> StackAdapt Programmatic (Display + Native + CTV)</div>
    <div><strong>Intelligence:</strong> 3,103 bilateral edges × 27 alignment dimensions × 14 brands</div>
    <div><strong>Prepared by:</strong> INFORMATIV</div>
    <div><strong>Date:</strong> March 2026</div>
  </div>
  <div class="confidential">CONFIDENTIAL — FOR AGENCY USE ONLY</div>
</div>

<div class="page">

<div class="toc">
  <h2>Contents</h2>
  <ol class="toc-list">
    <li><a href="#exec"><span class="num">1</span> Executive Summary</a></li>
    <li><a href="#arch"><span class="num">2</span> Campaign Architecture — 5 Archetypes, 3 Active Tracks</a></li>
    <li><a href="#segments"><span class="num">3</span> Audience Segment Definitions</a></li>
    <li><a href="#creative"><span class="num">4</span> Creative Briefs with Bilateral Evidence</a></li>
    <li><a href="#placements"><span class="num">5</span> Placement Strategy</a></li>
    <li><a href="#ctv"><span class="num">6</span> CTV Strategy</a></li>
    <li><a href="#dayparting"><span class="num">7</span> Dayparting Schedule</a></li>
    <li><a href="#bidding"><span class="num">8</span> Bid Strategy</a></li>
    <li><a href="#frequency"><span class="num">9</span> Frequency Capping</a></li>
    <li><a href="#negative"><span class="num">10</span> Negative Targeting</a></li>
    <li><a href="#retargeting"><span class="num">11</span> Retargeting Strategy — Sequential Mechanism Deployment</a></li>
    <li><a href="#measurement"><span class="num">12</span> Measurement Framework</a></li>
    <li><a href="#timeline"><span class="num">13</span> Campaign Timeline</a></li>
    <li><a href="#science"><span class="num">14</span> Appendix: The Bilateral Science</a></li>
  </ol>
</div>

<section id="exec">
  <h2>1. Executive Summary</h2>
  <p class="section-sub">What this document is and what makes it different from every other campaign brief.</p>

  <p>This brief is built on <strong>3,103 bilateral psychological edges</strong> — computed alignments between 65-dimension buyer profiles and 65-dimension seller profiles across 14 luxury transportation brands. It identifies <strong>5 psychologically distinct buyer types</strong> through data-driven clustering on 31 identity-stable dimensions, then determines which <strong>specific seller positioning</strong> converts each type using inferential statistics.</p>

  <div class="stat-grid">
    <div class="stat-card"><div class="val">3,103</div><div class="label">Bilateral Edges Analyzed</div></div>
    <div class="stat-card"><div class="val">5</div><div class="label">Buyer Archetypes (3 active)</div></div>
    <div class="stat-card"><div class="val">65×65</div><div class="label">Buyer × Seller Dimensions</div></div>
    <div class="stat-card"><div class="val">97.9%</div><div class="label">Classifier Accuracy</div></div>
  </div>

  <div class="insight-callout">
    <strong>The Breakthrough Finding:</strong> The <strong>Careful Truster</strong> segment (21% of market, 65% conversion) is the largest opportunity. Bilateral analysis reveals that warmth, sincerity, and narrative appeals <strong>HURT</strong> conversion for this group (liking r=-0.229, narrative r=-0.226), while rational, comparative, evidence-based positioning <strong>HELPS</strong> (brand_trust_fit r=+0.619, comparative r=+0.163). This is the opposite of what intuition suggests — and the kind of insight that only comes from computing the bilateral interaction between buyer psychology and seller positioning.
  </div>
</section>

<section id="arch">
  <h2>2. Campaign Architecture</h2>
  <p class="section-sub">5 buyer archetypes identified from identity-stable psychological dimensions. 3 active campaign tracks + 2 suppression targets.</p>

  <div class="stat-grid">
    <div class="stat-card" style="border-top:3px solid {COLORS['status_seeker']}">
      <div class="val" style="font-size:22px;color:{COLORS['status_seeker']}">Status Seeker</div>
      <div class="label">22% · 94.5% conv · 30% budget</div>
    </div>
    <div class="stat-card" style="border-top:3px solid {COLORS['careful_truster']}">
      <div class="val" style="font-size:22px;color:{COLORS['careful_truster']}">Careful Truster</div>
      <div class="label">21% · 65.0% conv · 40% budget — SWING</div>
    </div>
    <div class="stat-card" style="border-top:3px solid {COLORS['easy_decider']}">
      <div class="val" style="font-size:22px;color:{COLORS['easy_decider']}">Easy Decider</div>
      <div class="label">17% · 90.9% conv · 15% budget</div>
    </div>
    <div class="stat-card" style="border-top:3px solid {COLORS['skeptical_analyst']}">
      <div class="val" style="font-size:18px;color:{COLORS['skeptical_analyst']}">Skeptical Analyst</div>
      <div class="label">24% · 0.8% conv · SUPPRESS</div>
    </div>
    <div class="stat-card" style="border-top:3px solid {COLORS['disillusioned']}">
      <div class="val" style="font-size:18px;color:{COLORS['disillusioned']}">Disillusioned</div>
      <div class="label">16% · 0.8% conv · SUPPRESS</div>
    </div>
  </div>

  <div class="insight-callout">
    <strong>Why 3 active tracks, not 5:</strong> Skeptical Analyst (0.8% conv) and Disillusioned (0.8% conv) are psychologically resistant to advertising. Their high reactance, negativity bias, and attachment avoidance mean ad spend is wasted. The campaign allocates 85% of budget to the 3 convertible segments and either suppresses or minimally targets the other 2.
  </div>
</section>

<section id="segments">
  <h2>3. Audience Segment Definitions</h2>
  <p class="section-sub">How to build each segment in StackAdapt. Each definition is derived from the buyer's identity-stable psychological profile.</p>

  <div class="brief-section" style="border-left:4px solid {COLORS['status_seeker']}">
    <h3 style="color:{COLORS['status_seeker']}">Status Seeker (30% budget)</h3>
    <p><strong>Psychology:</strong> High promotion focus (z=+1.09), high status motive (z=+0.90), high affiliation (z=+0.90), low spending pain (z=-1.03). They book luxury because it's who they are.</p>
    <h4>StackAdapt Targeting</h4>
    <ul style="font-size:13px;padding-left:20px">
      <li><strong>Behavioral:</strong> Frequent business travel, high-value purchases, LinkedIn active, premium content consumption</li>
      <li><strong>Contextual:</strong> Business/finance news, leadership content, luxury lifestyle editorial</li>
      <li><strong>Demographic:</strong> HHI $150K+, professional/executive, 30-60, major metro markets</li>
    </ul>
  </div>

  <div class="brief-section" style="border-left:4px solid {COLORS['careful_truster']}">
    <h3 style="color:{COLORS['careful_truster']}">Careful Truster (40% budget) — THE SWING SEGMENT</h3>
    <p><strong>Psychology:</strong> High agreeableness (z=+0.55), high brand trust (z=+0.48), high disease avoidance (z=+0.58), low impulse (z=-0.44). They evaluate quietly and convert when trust is established through EVIDENCE — not warmth.</p>
    <h4>StackAdapt Targeting</h4>
    <ul style="font-size:13px;padding-left:20px">
      <li><strong>Behavioral:</strong> Travel planning, comparison shopping, review reading, weather/flight checking</li>
      <li><strong>Contextual:</strong> Travel comparison, review sites, airport/flight information</li>
      <li><strong>Demographic:</strong> HHI $100K+, mixed age, research-oriented travelers</li>
    </ul>
    <div class="insight-callout"><strong>Critical:</strong> brand_trust_fit has the strongest correlation with conversion (r=+0.619) of ANY dimension in ANY archetype. But trust here means EVIDENCE, not WARMTH. Sincerity hurts (r=-). Comparative and rational appeals help (r=+).</div>
  </div>

  <div class="brief-section" style="border-left:4px solid {COLORS['easy_decider']}">
    <h3 style="color:{COLORS['easy_decider']}">Easy Decider (15% budget)</h3>
    <p><strong>Psychology:</strong> Low maximizer (z=-1.51), low self-protection (z=-1.28), low information search (z=-1.27). They don't overthink. Remove friction and they convert.</p>
    <h4>StackAdapt Targeting</h4>
    <ul style="font-size:13px;padding-left:20px">
      <li><strong>Behavioral:</strong> Quick booking patterns, returning visitors, app users, short decision cycles</li>
      <li><strong>Contextual:</strong> Entertainment, lifestyle, low-cognitive-load content</li>
      <li><strong>Retargeting:</strong> Site visitors, app users, past bookers</li>
    </ul>
  </div>
</section>

<section id="creative">
  <h2>4. Creative Briefs</h2>
  <p class="section-sub">Each brief is grounded in bilateral evidence: which seller-side dimensions correlate with conversion for this specific buyer type.</p>
  {brief_section('status_seeker')}
  {brief_section('careful_truster')}
  {brief_section('easy_decider')}
</section>

<section id="placements">
  <h2>5. Placement Strategy</h2>
  <p class="section-sub">Domains selected for the psychological environment they create.</p>
  <h3>Domain Whitelist ({len(domains)} domains)</h3>
  {domain_table()}
  <h3>Domain Blacklist ({len(blacklist)} domains)</h3>
  <table><tr><th>Domain</th><th>Reason</th></tr>
  {''.join(f"<tr><td>{esc(d.get('domain',''))}</td><td>{esc(d.get('reason',''))}</td></tr>" for d in blacklist)}</table>
</section>

<section id="ctv">
  <h2>6. CTV Strategy</h2>
  <table><tr>{''.join(f"<th>{esc(k)}</th>" for k in (ctv[0].keys() if ctv else []))}</tr>
  {''.join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row.values()) + "</tr>" for row in ctv)}</table>
</section>

<section id="dayparting">
  <h2>7. Dayparting Schedule</h2>
  {dayparting_table()}
</section>

<section id="bidding">
  <h2>8. Bid Strategy</h2>
  <table><tr><th>Track</th><th>Base CPM</th><th>Multiplier</th><th>Peak Boost</th><th>CTV Premium</th><th>Rationale</th></tr>
  {''.join(f"""<tr><td style="color:{COLORS.get(name,'#6b7280')}">{track_label(name)}</td>
  <td>${d.get("base_cpm","")}</td><td>{d.get("multiplier","")}x</td>
  <td>{d.get("peak_boost","")}x</td><td>{d.get("ctv_premium","")}x</td>
  <td style="font-size:12px">{esc(d.get("rationale",""))}</td></tr>"""
  for name, d in bid.get("tracks",{}).items())}</table>
</section>

<section id="frequency">
  <h2>9. Frequency Capping</h2>
  <table><tr><th>Track</th><th>Max/Day</th><th>Max/Week</th><th>Rationale</th></tr>
  {''.join(f"""<tr><td style="color:{COLORS.get(name,'#6b7280')}">{track_label(name)}</td>
  <td>{d.get("max_day","")}</td><td>{d.get("max_week","")}</td>
  <td style="font-size:12px">{esc(d.get("reason",""))}</td></tr>"""
  for name, d in freq.items() if isinstance(d, dict) and 'max_day' in d)}</table>
  <div class="insight-callout"><strong>Cross-track:</strong> {esc(freq.get("cross_track",{}).get("rule",""))}</div>
  <div class="insight-callout"><strong>Reactance recovery:</strong> {esc(freq.get("reactance_recovery",{}).get("rule",""))}</div>
</section>

<section id="negative">
  <h2>10. Negative Targeting</h2>
  <div class="brief-section">
    <h4>Keyword Exclusions</h4><p style="font-size:13px">{', '.join(neg.get('keyword_exclusions',[]))}</p>
    <h4>Contextual Exclusions</h4><ul style="font-size:13px">{''.join(f"<li>{esc(c)}</li>" for c in neg.get('contextual_exclusions',[]))}</ul>
    <h4>Audience Exclusions</h4><ul style="font-size:13px">{''.join(f"<li>{esc(a)}</li>" for a in neg.get('audience_exclusions',[]))}</ul>
  </div>
</section>

<section id="retargeting">
  <h2>11. Retargeting Strategy — Sequential Mechanism Deployment</h2>
  <p class="section-sub">Each retargeting touch addresses the specific bilateral alignment threshold that FAILED on the previous touch. This is NOT standard retargeting — each impression deploys a DIFFERENT mechanism.</p>

  <div class="insight-callout">
    <strong>Principle:</strong> Standard retargeting shows the same ad again. This system identifies WHY the buyer didn't convert (which alignment dimension was sub-threshold) and deploys a DIFFERENT mechanism on the next touch specifically targeting that failure. The sequence is statistically derived from non-converter sub-cluster analysis.
  </div>

''' + ''.join(f'''
  <div class="brief-section" style="border-left:4px solid {COLORS.get(arch, "#6b7280")}">
    <h3 style="color:{COLORS.get(arch, "#6b7280")}">{track_label(arch)} Retargeting</h3>
    <p style="font-size:14px"><strong>{retarget.get(arch,{}).get("non_converter_count","")} non-converters ({retarget.get(arch,{}).get("non_converter_pct","")})</strong> — {esc(retarget.get(arch,{}).get("why_they_fail",""))}</p>

    <h4>Non-Converter Sub-Clusters</h4>
    {''.join(f"""<div style="background:var(--surface2);border-radius:6px;padding:12px 16px;margin:6px 0">
      <strong>{esc(sc.get("label",""))}</strong> (n={sc.get("n","")}): {esc(sc.get("description",""))}
      <div style="margin-top:6px;font-size:13px;color:var(--accent)">Mechanism: {esc(sc.get("retargeting_mechanism",""))}</div>
      <div style="font-size:13px;color:var(--dim)">{esc(sc.get("creative",""))}</div>
    </div>""" for sc_name, sc in retarget.get(arch,{}).get("sub_clusters",{}).items())}

    <h4>Retargeting Sequence</h4>
    <table><tr><th>Touch</th><th>Trigger</th><th>Mechanism</th><th>Creative Direction</th><th>Alignment Target</th></tr>
    {''.join(f"""<tr>
      <td><strong>Touch {t.get("touch","")}</strong><br><span style="font-size:11px;color:var(--dim)">{t.get("type","")}</span></td>
      <td style="font-size:12px">{esc(t.get("trigger",""))}</td>
      <td style="font-size:12px;font-weight:600">{esc(t.get("mechanism",""))}</td>
      <td style="font-size:12px">{esc(t.get("creative_type",""))}</td>
      <td style="font-size:11px;color:var(--dim)">{esc(t.get("alignment_target",""))}</td>
    </tr>""" for t in retarget.get(arch,{}).get("sequence",[]))}
    </table>

    <h4>Suppression Rules</h4>
    <ul style="font-size:13px">{''.join(f"<li>{esc(r)}</li>" for r in retarget.get(arch,{}).get("suppression_rules",[]))}</ul>
  </div>
''' for arch in ['careful_truster', 'status_seeker', 'easy_decider']) + '''

  <div class="brief-section">
    <h3>Cross-Archetype Rules</h3>
    ''' + ''.join(f'<div class="stat-row" style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid rgba(42,53,72,0.3)"><strong style="min-width:200px">{esc(k.replace("_"," ").title())}</strong><span style="font-size:13px">{esc(v)}</span></div>' for k,v in retarget.get('cross_archetype_rules',{}).items()) + '''
  </div>

  <div class="brief-section">
    <h3>StackAdapt Implementation</h3>
    <h4>Pixel Setup</h4>
    <p style="font-size:13px">''' + esc(retarget.get('implementation_in_stackadapt',{}).get('pixel_setup','')) + '''</p>
    <h4>Audience Segments</h4>
    <ul style="font-size:13px">''' + ''.join(f'<li>{esc(s)}</li>' for s in retarget.get('implementation_in_stackadapt',{}).get('audience_segments',[])) + '''</ul>
    <h4>Creative Rotation</h4>
    <p style="font-size:13px">''' + esc(retarget.get('implementation_in_stackadapt',{}).get('creative_rotation','')) + '''</p>
    <h4>Measurement</h4>
    <p style="font-size:13px">''' + esc(retarget.get('implementation_in_stackadapt',{}).get('measurement','')) + '''</p>
  </div>
</section>

<section id="measurement">
  <h2>12. Measurement Framework</h2>
  <table><tr>{''.join(f"<th>{esc(k)}</th>" for k in (measurement[0].keys() if measurement else []))}</tr>
  {''.join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row.values()) + "</tr>" for row in measurement)}</table>
</section>

<section id="timeline">
  <h2>12. Campaign Timeline</h2>
  <div class="brief-section">
    <h4>Pre-Launch (Agency)</h4>
    <ol style="font-size:14px;padding-left:20px">
      <li>Create 3 audience segments in StackAdapt (Status Seeker, Careful Truster, Easy Decider)</li>
      <li>Brief creative team with bilateral-evidence creative directions (Section 4)</li>
      <li>Upload domain whitelist/blacklist</li>
      <li>Configure dayparting and bid rules</li>
      <li>Set frequency caps per Section 9</li>
      <li>Install conversion pixel on luxyride.com booking confirmation</li>
      <li>Set UTM: utm_source=stackadapt&amp;utm_campaign=informativ_[track]</li>
      <li>Configure suppression for skeptical_analyst and disillusioned audiences</li>
    </ol>
    <h4>Week 1: Observation</h4><p style="font-size:14px">Run all 3 tracks. Daily monitoring. No optimization.</p>
    <h4>Week 2: First Optimization</h4><p style="font-size:14px">Shift budget toward highest-converting track. Pause underperforming domains. Validate careful_truster evidence-based creative outperforms warmth-based.</p>
    <h4>Ongoing</h4><p style="font-size:14px">Weekly optimization. Monthly creative refresh (same mechanisms, new executions).</p>
  </div>
</section>

<section id="science">
  <h2>13. Appendix: The Bilateral Science</h2>
  <p style="font-size:14px">Each of the 3,103 edges represents a COMPUTED INTERACTION between a buyer's 65-dimension psychological profile and a seller's 65-dimension positioning profile. The 27 alignment dimensions on each edge are derived from research-backed formulas — regulatory fit (Higgins), construal matching (Trope & Liberman), personality-brand alignment (Aaker → Big Five mapping), and 24 more.</p>
  <p style="font-size:14px;margin-top:12px">The 5 buyer archetypes were identified by k-means clustering on 31 identity-stable psychological dimensions (personality traits, motives, decision styles — NOT emotional states or outcomes). The classifier achieves 97.9% cross-validated accuracy.</p>
  <p style="font-size:14px;margin-top:12px">For each archetype, we computed point-biserial correlations between every seller-side dimension and conversion outcome to determine the OPTIMAL SELLER POSITIONING per buyer type. This is what makes the creative briefs actionable — not intuition about "what works," but statistical evidence of which specific seller attributes predict conversion for each specific buyer psychology.</p>
  <table>
    <tr><td>Bilateral edges</td><td><strong>3,103</strong></td></tr>
    <tr><td>Buyer dimensions per review</td><td><strong>65</strong></td></tr>
    <tr><td>Seller dimensions per brand</td><td><strong>65</strong></td></tr>
    <tr><td>Alignment dimensions per edge</td><td><strong>27</strong> (14 with discriminating variance)</td></tr>
    <tr><td>Brands profiled</td><td><strong>14</strong> (from website crawls + ad copy)</td></tr>
    <tr><td>Archetype classifier accuracy</td><td><strong>97.9%</strong> (5-fold CV)</td></tr>
    <tr><td>Statistical method</td><td>Point-biserial correlation (p&lt;0.05)</td></tr>
  </table>
</section>

<div class="footer">
  <p>CONFIDENTIAL — INFORMATIV Bilateral Psycholinguistic Intelligence</p>
  <p>Prepared for LUXY Ride (luxyride.com) · March 2026</p>
</div>

</div></body></html>'''

(CAMPAIGNS / 'LUXY_Ride_Campaign_Handoff.html').write_text(html)
print(f'Written: {CAMPAIGNS / "LUXY_Ride_Campaign_Handoff.html"} ({len(html)//1024}KB)')
