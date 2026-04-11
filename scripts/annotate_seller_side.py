#!/usr/bin/env python3
"""
Annotate RideLux's seller-side profile in the same 20-dim edge space.

The seller-side profile answers: "What psychological dimensions does
RideLux's messaging activate?" This creates the SELLER half of the
bilateral edge. At bid time, the cascade computes alignment between
the buyer's psychological state and this seller profile.

Also analyzes competitor messaging for mechanism saturation to identify
differentiation opportunities.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adam.intelligence.annotation_engine import ANNOTATION_DIMENSIONS

REVIEWS_DIR = os.path.join(os.path.dirname(__file__), "..", "reviews")
EDGE_DIMS = list(ANNOTATION_DIMENSIONS.keys())


def build_seller_annotation_prompt(
    all_copy: list[dict],
    brand_name: str,
    buyer_stats: dict,
) -> str:
    """Build prompt for seller-side annotation.

    Unlike buyer-side (which annotates individual reviews), seller-side
    annotates the ENTIRE brand's messaging portfolio as a unified profile.
    """
    # Collect all copy text
    copy_texts = []
    for entry in all_copy:
        text = entry.get("body_copy") or entry.get("copy_text") or ""
        headline = entry.get("headline", "")
        combined = f"{headline}: {text}" if headline else text
        if combined.strip():
            copy_texts.append(combined.strip())

    copy_block = "\n".join(f"- {t}" for t in copy_texts)

    # Build dimension definitions
    dim_defs = []
    for prop, info in ANNOTATION_DIMENSIONS.items():
        dim_defs.append(
            f"  {prop} ({info['name']}):\n"
            f"    BUYER meaning: {info['definition']}\n"
            f"    SELLER meaning: How strongly does the brand's messaging ACTIVATE this dimension in a potential buyer?\n"
            f"    {info['anchor_low']}\n"
            f"    {info['anchor_high']}"
        )
    dims_text = "\n".join(dim_defs)

    # Include buyer-side stats for contrast
    buyer_context = ""
    if buyer_stats:
        buyer_context = "\nBUYER PSYCHOLOGICAL LANDSCAPE (from 1,492 annotated reviews):\n"
        for dim in EDGE_DIMS:
            stats = buyer_stats.get("dimensions", {}).get(dim, {})
            if stats:
                buyer_context += f"  {dim}: buyer avg={stats['mean']}, spread={stats['stdev']}\n"
        buyer_context += f"\nTop buyer mechanisms: {buyer_stats.get('mechanisms', {})}\n"
        buyer_context += f"Buyer regulatory focus: {buyer_stats.get('regulatory_focus', {})}\n"

    prompt = f"""You are a psycholinguistic brand analyst scoring a brand's COMPLETE advertising and messaging portfolio.

BRAND: {brand_name}
WEBSITE: luxyride.com (luxury ground transportation / black car service)

ALL MESSAGING COPY FROM {brand_name.upper()} AND COMPETITORS IN THE CATEGORY:
{copy_block}

{buyer_context}

YOUR TASK: Score {brand_name}'s messaging portfolio on the same 20 psychological dimensions used to score buyers.

For the SELLER side, each dimension means: "How strongly does this brand's messaging ACTIVATE or TARGET this psychological dimension?"

For example:
- regulatory_fit_score: Does the messaging appeal to promotion focus (aspirational) or prevention focus (safety/reliability)?
- emotional_resonance: Does the messaging create emotional engagement or stay transactional?
- spending_pain_match: Does the messaging address price concerns directly?

CRITICAL INSTRUCTIONS:
1. Score what the MESSAGING ACTUALLY DOES, not what it intends to do.
2. High scores mean the messaging STRONGLY activates that dimension. Low scores mean it doesn't address it.
3. Consider the ENTIRE portfolio together — the brand profile is the gestalt of all their messaging.
4. Where the brand's messaging ALIGNS with the buyer landscape (what buyers actually care about), note it. Where it MISSES, note it.

DIMENSIONS:
{dims_text}

ALSO DETERMINE:
- primary_mechanism_deployed: Which Cialdini principle does the messaging deploy most? (authority, social_proof, loss_aversion, commitment, liking, cognitive_ease, reciprocity, scarcity, curiosity)
- secondary_mechanism_deployed: Second most deployed
- mechanism_gaps: Which mechanisms are ABSENT from the messaging but present in buyer psychology? (list)
- messaging_strengths: What the brand does well psychologically (string)
- messaging_weaknesses: What the brand fails to address (string)
- alignment_with_buyers: Where does brand messaging match what buyers actually respond to? (string)
- differentiation_opportunity: Given competitor messaging saturation, what psychological angle is UNDERSERVED? (string)
- recommended_ad_angle: If you could write ONE ad for this brand based on the buyer data and messaging gaps, what would it say? (string)

Return ONLY valid JSON with these exact keys:
{{
  "regulatory_fit_score": 0.0-1.0,
  "construal_fit_score": 0.0-1.0,
  "personality_brand_alignment": 0.0-1.0,
  "emotional_resonance": 0.0-1.0,
  "value_alignment": 0.0-1.0,
  "evolutionary_motive_match": 0.0-1.0,
  "linguistic_style_matching": 0.0-1.0,
  "spending_pain_match": 0.0-1.0,
  "reactance_fit": 0.0-1.0,
  "self_monitoring_fit": 0.0-1.0,
  "processing_route_match": 0.0-1.0,
  "mental_simulation_resonance": 0.0-1.0,
  "optimal_distinctiveness_fit": 0.0-1.0,
  "involvement_weight_modifier": 0.0-1.0,
  "brand_trust_fit": 0.0-1.0,
  "identity_signaling_match": 0.0-1.0,
  "anchor_susceptibility_match": 0.0-1.0,
  "lay_theory_alignment": 0.0-1.0,
  "negativity_bias_match": 0.0-1.0,
  "persuasion_confidence_multiplier": 0.0-1.0,
  "primary_mechanism_deployed": "string",
  "secondary_mechanism_deployed": "string",
  "mechanism_gaps": ["string"],
  "messaging_strengths": "string",
  "messaging_weaknesses": "string",
  "alignment_with_buyers": "string",
  "differentiation_opportunity": "string",
  "recommended_ad_angle": "string"
}}"""

    return prompt


def main():
    import anthropic
    client = anthropic.Anthropic()

    # Load all ad copy
    with open(os.path.join(REVIEWS_DIR, "luxury_car_service_ads.json")) as f:
        ads_original = json.load(f)

    with open(os.path.join(REVIEWS_DIR, "luxury_car_service_ads_expanded.json")) as f:
        ads_expanded = json.load(f)

    # Load buyer stats for context
    with open(os.path.join(REVIEWS_DIR, "luxury_transportation_complete.json")) as f:
        complete = json.load(f)
    buyer_stats = complete["category_stats"]

    # Separate RideLux/LUXY copy from competitors
    ridelux_copy = []
    competitor_copy = []

    for ad in ads_original["advertisements"]:
        company = ad.get("company", "").lower()
        if "luxy" in company or "ridelux" in company or "lux ride" in company:
            ridelux_copy.append(ad)
        else:
            competitor_copy.append(ad)

    for ad in ads_expanded["ads"]:
        company = ad.get("company", "").lower()
        if "luxy" in company or "ridelux" in company or "lux ride" in company:
            ridelux_copy.append(ad)

    print(f"RideLux copy entries: {len(ridelux_copy)}")
    print(f"Competitor copy entries: {len(competitor_copy) + len(ads_expanded['ads'])}")

    # Add the known RideLux brand positioning from the brand deep dive
    ridelux_copy.extend([
        {"headline": "The smarter way to book black car service", "body_copy": ""},
        {"headline": "Skip the rideshare roulette", "body_copy": "Always available, always on time. 24/7 email and chat support. Reliable drivers, nationwide. No hidden fees and the best pricing in your area."},
        {"headline": "LUXY IS ECO-CONSCIOUS EXECUTIVE TRANSPORT", "body_copy": "Our commitment to a sustainable future"},
        {"headline": "400+ Companies trust and travel with LUXY Ride", "body_copy": "LUXY's Safety PIN verification system makes rides safer and more secure."},
        {"headline": "The LUXY experience is a step up from the rest", "body_copy": "Chauffeurs always go above and beyond. Customer service is always quick to help."},
        {"headline": "Top Rated Booking Platform For Black Car Service", "body_copy": "Professional Chauffeurs. Upfront Pricing. Technology Built For Booking Seamless Rides."},
    ])

    # Combine all copy for the prompt (RideLux + competitor for full context)
    all_copy = ridelux_copy + competitor_copy[:30]  # Top 30 competitor for context

    prompt = build_seller_annotation_prompt(all_copy, "RideLux", buyer_stats)

    print(f"\nPrompt length: {len(prompt)} chars")
    print("Calling Claude Sonnet for deep seller-side analysis...")

    # Use Sonnet for this — it's a single high-stakes annotation
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    resp_text = response.content[0].text.strip()
    if resp_text.startswith("```"):
        resp_text = resp_text.split("\n", 1)[1].rsplit("```", 1)[0]

    result = json.loads(resp_text)

    # Validate dimensions
    for dim in EDGE_DIMS:
        val = result.get(dim)
        if val is None or not isinstance(val, (int, float)):
            result[dim] = 0.5
        else:
            result[dim] = max(0.0, min(1.0, float(val)))

    # Print results
    print("\n" + "=" * 60)
    print("RIDELUX SELLER-SIDE PROFILE (20 dimensions)")
    print("=" * 60)

    for dim in EDGE_DIMS:
        buyer_avg = buyer_stats.get("dimensions", {}).get(dim, {}).get("mean", 0.5)
        seller_val = result[dim]
        gap = abs(seller_val - buyer_avg)
        alignment = "✓" if gap < 0.15 else "△" if gap < 0.25 else "✗"
        print(f"  {dim:40s}  seller={seller_val:.2f}  buyer_avg={buyer_avg:.2f}  {alignment}")

    print(f"\nPrimary mechanism: {result.get('primary_mechanism_deployed')}")
    print(f"Secondary mechanism: {result.get('secondary_mechanism_deployed')}")
    print(f"Mechanism gaps: {result.get('mechanism_gaps')}")
    print(f"\nStrengths: {result.get('messaging_strengths')}")
    print(f"Weaknesses: {result.get('messaging_weaknesses')}")
    print(f"Alignment: {result.get('alignment_with_buyers')}")
    print(f"Differentiation: {result.get('differentiation_opportunity')}")
    print(f"Recommended angle: {result.get('recommended_ad_angle')}")

    # Compute alignment score
    total_gap = 0
    for dim in EDGE_DIMS:
        buyer_avg = buyer_stats.get("dimensions", {}).get(dim, {}).get("mean", 0.5)
        total_gap += abs(result[dim] - buyer_avg)
    avg_gap = total_gap / len(EDGE_DIMS)
    alignment_score = 1.0 - avg_gap
    print(f"\nOverall buyer-seller alignment: {alignment_score:.3f}")

    # Save
    output = {
        "brand": "RideLux",
        "website": "luxyride.com",
        "seller_profile": result,
        "alignment_score": round(alignment_score, 4),
        "annotation_model": "claude-sonnet-4-20250514",
    }

    output_path = os.path.join(REVIEWS_DIR, "ridelux_seller_profile.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {output_path}")

    return result


if __name__ == "__main__":
    main()
