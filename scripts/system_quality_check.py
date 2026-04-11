#!/usr/bin/env python3
"""
ADAM System Quality Check — Comprehensive Output Strength Inspection
====================================================================

Tests 4 consumer types:
1. DSP (StackAdapt Creative Intelligence) — brand + product
2. SSP (Bid Enrichment) — impression enrichment
3. Publisher (Page Profile) — page psychological profiling
4. Brand (Brand Profile) — brand psychology analysis

For each, inspects:
- Which intelligence layers activated
- Signal depth (how many dimensions populated)
- Reasoning trace quality
- Gaps and weak signals
"""

import json
import sys
import time

# ── Helpers ──────────────────────────────────────────────────────────

def section(title: str):
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}")

def subsection(title: str):
    print(f"\n  --- {title} ---")

def score_field(name: str, value, expected_type=None, min_val=None, max_val=None):
    """Score a field's quality: STRONG / WEAK / MISSING"""
    if value is None or value == "" or value == {} or value == []:
        print(f"    MISSING : {name}")
        return "MISSING"
    if expected_type and not isinstance(value, expected_type):
        print(f"    WEAK    : {name} — wrong type ({type(value).__name__})")
        return "WEAK"
    if isinstance(value, (int, float)) and min_val is not None and max_val is not None:
        if min_val <= value <= max_val:
            print(f"    STRONG  : {name} = {value}")
            return "STRONG"
        else:
            print(f"    WEAK    : {name} = {value} (outside [{min_val}, {max_val}])")
            return "WEAK"
    if isinstance(value, dict):
        non_empty = sum(1 for v in value.values() if v is not None and v != 0 and v != 0.0)
        total = len(value)
        if non_empty >= total * 0.7:
            print(f"    STRONG  : {name} — {non_empty}/{total} fields populated")
            return "STRONG"
        elif non_empty > 0:
            print(f"    WEAK    : {name} — only {non_empty}/{total} fields populated")
            return "WEAK"
        else:
            print(f"    MISSING : {name} — all fields empty")
            return "MISSING"
    if isinstance(value, list):
        if len(value) >= 2:
            print(f"    STRONG  : {name} — {len(value)} items")
            return "STRONG"
        elif len(value) == 1:
            print(f"    WEAK    : {name} — only 1 item")
            return "WEAK"
    if isinstance(value, str) and len(value) > 0:
        print(f"    STRONG  : {name} = '{value}'")
        return "STRONG"
    print(f"    OK      : {name} = {value}")
    return "STRONG"


def summarize_scores(scores: dict):
    strong = sum(1 for v in scores.values() if v == "STRONG")
    weak = sum(1 for v in scores.values() if v == "WEAK")
    missing = sum(1 for v in scores.values() if v == "MISSING")
    total = len(scores)
    pct = round(strong / total * 100) if total > 0 else 0
    print(f"\n  SCORE: {strong}/{total} strong ({pct}%), {weak} weak, {missing} missing")
    return {"strong": strong, "weak": weak, "missing": missing, "total": total, "pct": pct}


# ── Test 1: DSP Creative Intelligence ────────────────────────────────

def test_dsp_creative_intelligence():
    section("TEST 1: DSP (StackAdapt Creative Intelligence)")
    print("  Scenario: Sephora beauty product, mobile, evening, Vogue placement")

    from adam.api.stackadapt.bilateral_cascade import (
        run_bilateral_cascade,
        CreativeIntelligence,
    )

    t0 = time.time()
    result = run_bilateral_cascade(
        segment_id="informativ_connector_social_proof_beauty_t1",
        asin="B07XYZ123",
        device_type="mobile",
        time_of_day=19,
        iab_category="beauty",
        page_url="https://vogue.com/article/summer-beauty-trends",
        buyer_id="test_buyer_001",
    )
    elapsed = (time.time() - t0) * 1000

    scores = {}

    subsection("Cascade Level & Evidence")
    scores["cascade_level"] = score_field("cascade_level", result.cascade_level, int, 1, 5)
    scores["evidence_source"] = score_field("evidence_source", result.evidence_source)
    scores["confidence"] = score_field("confidence", result.confidence, float, 0.0, 1.0)
    scores["edge_count"] = score_field("edge_count", result.edge_count, int, 0, 100000)

    subsection("Creative Parameters")
    scores["primary_mechanism"] = score_field("primary_mechanism", result.primary_mechanism)
    scores["secondary_mechanism"] = score_field("secondary_mechanism", result.secondary_mechanism)
    scores["framing"] = score_field("framing", result.framing)
    scores["construal_level"] = score_field("construal_level", result.construal_level)
    scores["tone"] = score_field("tone", result.tone)
    scores["urgency_level"] = score_field("urgency_level", result.urgency_level, float, 0.0, 1.0)
    scores["social_proof_density"] = score_field("social_proof_density", result.social_proof_density, float, 0.0, 1.0)
    scores["emotional_intensity"] = score_field("emotional_intensity", result.emotional_intensity, float, 0.0, 1.0)
    scores["copy_length"] = score_field("copy_length", result.copy_length)

    subsection("Mechanism Scores (all 10)")
    scores["mechanism_scores"] = score_field("mechanism_scores", result.mechanism_scores)
    if result.mechanism_scores:
        ranked = sorted(result.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
        for mech, s in ranked:
            print(f"      {mech:20s}  {s:.4f}")

    subsection("Lift Estimates")
    scores["ctr_lift_pct"] = score_field("ctr_lift_pct", result.ctr_lift_pct, float, 0.0, 100.0)
    scores["conversion_lift_pct"] = score_field("conversion_lift_pct", result.conversion_lift_pct, float, 0.0, 100.0)

    subsection("Edge Dimensions (20)")
    scores["edge_dimensions"] = score_field("edge_dimensions", result.edge_dimensions)
    if result.edge_dimensions:
        for dim, val in sorted(result.edge_dimensions.items()):
            print(f"      {dim:30s}  {val:.4f}")

    subsection("Advanced Intelligence")
    scores["gradient_intelligence"] = score_field("gradient_intelligence", result.gradient_intelligence)
    scores["information_value"] = score_field("information_value", result.information_value)
    scores["context_intelligence"] = score_field("context_intelligence", result.context_intelligence)
    scores["mechanism_portfolio"] = score_field("mechanism_portfolio", result.mechanism_portfolio)
    scores["decision_probability"] = score_field("decision_probability", result.decision_probability)
    scores["category_deviation"] = score_field("category_deviation", result.category_deviation)

    subsection("Reasoning Trace")
    scores["reasoning"] = score_field("reasoning", result.reasoning)
    if result.reasoning:
        for r in result.reasoning:
            print(f"      {r}")

    print(f"\n  Latency: {elapsed:.1f}ms")
    return summarize_scores(scores)


# ── Test 2: DSP with different archetype ──────────────────────────────

def test_dsp_analyst():
    section("TEST 2: DSP — Analyst Archetype, Electronics, Desktop")
    print("  Scenario: Sony headphones, desktop, afternoon, tech review site")

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    t0 = time.time()
    result = run_bilateral_cascade(
        segment_id="informativ_analyst_authority_electronics_t2",
        asin="B09HEADPHONE",
        device_type="desktop",
        time_of_day=14,
        iab_category="technology",
        page_url="https://theverge.com/review/sony-wh1000xm5",
        buyer_id="test_buyer_002",
    )
    elapsed = (time.time() - t0) * 1000

    scores = {}
    subsection("Cascade & Mechanisms")
    scores["cascade_level"] = score_field("cascade_level", result.cascade_level, int, 1, 5)
    scores["primary_mechanism"] = score_field("primary_mechanism", result.primary_mechanism)
    scores["secondary_mechanism"] = score_field("secondary_mechanism", result.secondary_mechanism)
    scores["mechanism_scores"] = score_field("mechanism_scores", result.mechanism_scores)

    # For analyst: authority and cognitive_ease should rank high
    if result.mechanism_scores:
        auth = result.mechanism_scores.get("authority", 0)
        cog = result.mechanism_scores.get("cognitive_ease", 0)
        social = result.mechanism_scores.get("social_proof", 0)
        print(f"\n    Archetype check (analyst should favor authority/cognitive_ease):")
        print(f"      authority={auth:.3f}, cognitive_ease={cog:.3f}, social_proof={social:.3f}")
        if auth > social:
            print(f"      CORRECT: authority > social_proof for analyst")
        else:
            print(f"      WARNING: social_proof > authority for analyst (unexpected)")

    subsection("Context Modulation")
    scores["context_intelligence"] = score_field("context_intelligence", result.context_intelligence)
    scores["framing"] = score_field("framing", result.framing)
    scores["tone"] = score_field("tone", result.tone)

    subsection("Reasoning")
    if result.reasoning:
        for r in result.reasoning:
            print(f"      {r}")

    print(f"\n  Latency: {elapsed:.1f}ms")
    return summarize_scores(scores)


# ── Test 3: Publisher Page Profile ────────────────────────────────────

def test_publisher_page_profile():
    section("TEST 3: Publisher Page Profile")
    print("  Scenario: NYT article about inflation fears")

    from adam.intelligence.page_intelligence import profile_page_content

    page_text = """
    Federal Reserve Signals Prolonged Rate Hikes as Inflation Persists

    The Federal Reserve signaled Wednesday that interest rates would remain
    elevated for longer than previously expected, as inflation continues to
    run above the central bank's 2% target. Chair Jerome Powell warned that
    the path back to price stability could be "bumpy" and that additional
    rate increases might be needed.

    Markets reacted sharply to the hawkish tone, with the S&P 500 falling
    1.2% and Treasury yields climbing to their highest levels since 2007.
    Economists now expect rates to remain above 5% through mid-2027.

    For consumers, the implications are significant. Mortgage rates have
    already climbed above 7.5%, putting homeownership further out of reach
    for many Americans. Credit card interest rates have hit record highs,
    and auto loan costs continue to rise.

    Financial advisors recommend that consumers focus on building emergency
    savings, paying down high-interest debt, and avoiding major discretionary
    purchases until rate cuts begin. "This is a time for financial prudence,
    not speculation," said wealth advisor Jennifer Chen.
    """

    t0 = time.time()
    profile = profile_page_content(
        url="https://nytimes.com/business/fed-rate-hikes-inflation.html",
        text_content=page_text,
        title="Federal Reserve Signals Prolonged Rate Hikes as Inflation Persists",
        meta_description="The Fed warns rates will stay high as inflation remains stubborn",
    )
    elapsed = (time.time() - t0) * 1000

    scores = {}

    subsection("Profile Basics")
    scores["confidence"] = score_field("confidence", profile.confidence, float, 0.0, 1.0)
    scores["content_type"] = score_field("content_type", profile.content_type)
    scores["primary_topic"] = score_field("primary_topic", profile.primary_topic)
    scores["mindset"] = score_field("mindset", profile.mindset)

    subsection("Layer 1: Activated Needs")
    scores["activated_needs"] = score_field("activated_needs", profile.activated_needs)
    if profile.activated_needs:
        for need, strength in sorted(profile.activated_needs.items(), key=lambda x: -x[1]):
            print(f"      {need:25s}  {strength:.3f}")

    subsection("Layer 2: Emotional Field")
    scores["emotional_valence"] = score_field("emotional_valence", profile.emotional_valence, float, -1.0, 1.0)
    scores["emotional_arousal"] = score_field("emotional_arousal", profile.emotional_arousal, float, 0.0, 1.0)
    scores["dominant_emotions"] = score_field("dominant_emotions", profile.dominant_emotions)
    if profile.dominant_emotions:
        print(f"      Emotions: {', '.join(profile.dominant_emotions)}")

    subsection("Layer 3: Cognitive State")
    scores["cognitive_load"] = score_field("cognitive_load", profile.cognitive_load, float, 0.0, 1.0)
    scores["remaining_bandwidth"] = score_field("remaining_bandwidth", profile.remaining_bandwidth, float, 0.0, 1.0)

    subsection("Layer 4: Credibility")
    scores["publisher_authority"] = score_field("publisher_authority", profile.publisher_authority, float, 0.0, 1.0)

    subsection("Layer 5: Primed Categories")
    scores["primed_categories"] = score_field("primed_categories", profile.primed_categories)

    subsection("Layer 6: Persuasion Channels")
    scores["open_channels"] = score_field("open_channels", profile.open_channels)
    scores["closed_channels"] = score_field("closed_channels", profile.closed_channels)
    scores["mechanism_adjustments"] = score_field("mechanism_adjustments", profile.mechanism_adjustments)
    if profile.open_channels:
        print(f"      Open:   {', '.join(profile.open_channels)}")
    if profile.closed_channels:
        print(f"      Closed: {', '.join(profile.closed_channels)}")
    if profile.mechanism_adjustments:
        for mech, mult in sorted(profile.mechanism_adjustments.items(), key=lambda x: -x[1]):
            direction = "BOOST" if mult > 1.0 else "DAMPEN" if mult < 1.0 else "NEUTRAL"
            print(f"      {mech:20s}  x{mult:.2f}  ({direction})")

    subsection("Layer 8: Decision-Making Style")
    scores["primed_decision_style"] = score_field("primed_decision_style", profile.primed_decision_style)
    if profile.primed_decision_style:
        for k, v in profile.primed_decision_style.items():
            print(f"      {k:25s}  {v}")

    subsection("NDF Construct Activations")
    ca = getattr(profile, "construct_activations", {})
    scores["construct_activations"] = score_field("construct_activations", ca)
    if ca:
        for dim, val in sorted(ca.items()):
            print(f"      {dim:25s}  {val:.3f}")

    print(f"\n  Latency: {elapsed:.1f}ms")
    return summarize_scores(scores)


# ── Test 4: Brand Profile ─────────────────────────────────────────────

def test_brand_profile():
    section("TEST 4: Brand Profile Analysis")
    print("  Scenario: Apple iPhone product psychology")

    # Test the content profiler directly
    try:
        from adam.intelligence.page_intelligence import profile_page_content

        brand_text = """
        iPhone 16 Pro Max — The most advanced iPhone ever.

        Featuring the revolutionary A18 Pro chip, a stunning 48MP camera system
        with 5x optical zoom, and an aerospace-grade titanium design. The always-on
        ProMotion display delivers buttery smooth scrolling at up to 120Hz.

        Capture cinema-quality video with ProRes recording. Experience desktop-class
        performance with the new 6-core GPU. And with all-day battery life, you can
        do more than ever before.

        Starting at $1,199. Available in Natural Titanium, Blue Titanium, White
        Titanium, and Black Titanium.

        Trade in your old device and save. Free shipping. Order now — limited stock
        for launch colors.
        """

        t0 = time.time()
        profile = profile_page_content(
            url="https://apple.com/iphone-16-pro",
            text_content=brand_text,
            title="iPhone 16 Pro Max — Apple",
            meta_description="The most advanced iPhone ever with A18 Pro chip",
        )
        elapsed = (time.time() - t0) * 1000

        scores = {}

        subsection("Brand Page Psychology")
        scores["confidence"] = score_field("confidence", profile.confidence, float, 0.0, 1.0)
        scores["mindset"] = score_field("mindset", profile.mindset)
        scores["activated_needs"] = score_field("activated_needs", profile.activated_needs)
        scores["dominant_emotions"] = score_field("dominant_emotions", profile.dominant_emotions)
        scores["open_channels"] = score_field("open_channels", profile.open_channels)
        scores["mechanism_adjustments"] = score_field("mechanism_adjustments", profile.mechanism_adjustments)
        scores["primed_decision_style"] = score_field("primed_decision_style", profile.primed_decision_style)

        if profile.activated_needs:
            subsection("Activated Needs (Brand Page)")
            for need, strength in sorted(profile.activated_needs.items(), key=lambda x: -x[1]):
                print(f"      {need:25s}  {strength:.3f}")

        if profile.mechanism_adjustments:
            subsection("Mechanism Adjustments (Brand Page)")
            for mech, mult in sorted(profile.mechanism_adjustments.items(), key=lambda x: -x[1]):
                print(f"      {mech:20s}  x{mult:.2f}")

        print(f"\n  Latency: {elapsed:.1f}ms")
        return summarize_scores(scores)

    except Exception as e:
        print(f"  ERROR: {e}")
        return {"strong": 0, "weak": 0, "missing": 0, "total": 0, "pct": 0}


# ── Test 5: Cold Start (No Data) ──────────────────────────────────────

def test_cold_start():
    section("TEST 5: Cold Start — No Product Data, No Buyer History")
    print("  Scenario: Unknown brand, unknown buyer, generic page")

    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    t0 = time.time()
    result = run_bilateral_cascade(
        segment_id="informativ_explorer",
        device_type="desktop",
        time_of_day=10,
    )
    elapsed = (time.time() - t0) * 1000

    scores = {}
    scores["cascade_level"] = score_field("cascade_level", result.cascade_level, int, 1, 1)
    scores["primary_mechanism"] = score_field("primary_mechanism", result.primary_mechanism)
    scores["mechanism_scores"] = score_field("mechanism_scores", result.mechanism_scores)
    scores["confidence"] = score_field("confidence", result.confidence, float, 0.0, 0.5)

    # For explorer: curiosity should be high
    if result.mechanism_scores:
        curiosity = result.mechanism_scores.get("curiosity", 0)
        top = max(result.mechanism_scores.values())
        print(f"\n    Archetype check (explorer should favor curiosity):")
        print(f"      curiosity={curiosity:.3f}, top_score={top:.3f}")
        print(f"      primary={result.primary_mechanism}")

    subsection("Reasoning (should show L1 only)")
    if result.reasoning:
        for r in result.reasoning:
            print(f"      {r}")

    print(f"\n  Latency: {elapsed:.1f}ms")
    return summarize_scores(scores)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    section("ADAM SYSTEM QUALITY CHECK")
    print("  Running comprehensive output strength inspection...")

    all_results = {}

    try:
        all_results["dsp_connector"] = test_dsp_creative_intelligence()
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["dsp_connector"] = {"pct": 0}

    try:
        all_results["dsp_analyst"] = test_dsp_analyst()
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["dsp_analyst"] = {"pct": 0}

    try:
        all_results["publisher"] = test_publisher_page_profile()
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["publisher"] = {"pct": 0}

    try:
        all_results["brand"] = test_brand_profile()
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["brand"] = {"pct": 0}

    try:
        all_results["cold_start"] = test_cold_start()
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback; traceback.print_exc()
        all_results["cold_start"] = {"pct": 0}

    # ── Overall Summary ──
    section("OVERALL QUALITY SUMMARY")
    for name, result in all_results.items():
        pct = result.get("pct", 0)
        strong = result.get("strong", 0)
        total = result.get("total", 0)
        bar = "#" * (pct // 5) + "." * (20 - pct // 5)
        print(f"  {name:20s}  [{bar}]  {pct}% ({strong}/{total})")

    overall_pct = sum(r.get("pct", 0) for r in all_results.values()) / max(1, len(all_results))
    print(f"\n  OVERALL: {overall_pct:.0f}% signal strength")

    if overall_pct >= 70:
        print("  Status: GOOD — core intelligence activating")
    elif overall_pct >= 50:
        print("  Status: MODERATE — gaps in advanced intelligence layers")
    else:
        print("  Status: WEAK — critical intelligence not flowing")

    # Identify weakest areas
    print("\n  GAPS TO STRENGTHEN:")
    for name, result in all_results.items():
        missing = result.get("missing", 0)
        weak = result.get("weak", 0)
        if missing > 0 or weak > 0:
            print(f"    {name}: {missing} missing, {weak} weak signals")


if __name__ == "__main__":
    main()
