#!/usr/bin/env python3
"""
Analyze premium airline travelers as LUXY Ride proxy audience.

Filters 105K airline annotations to premium-airline satisfied travelers,
maps to bilateral edge format, computes edges against LUXY Ride ad-side,
and runs archetype clustering with interaction effects.

Usage:
    python3 scripts/analyze_airline_premium_archetypes.py
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# ─── Configuration ───
ANNOTATIONS_FILE = Path("reviews_other/airline_reviews/airline_annotations_all.json")
AD_SIDE_FILE = Path("reviews/luxury_ad_side_annotated.json")
OUTPUT_DIR = Path("reviews_other/airline_reviews")

# Premium airlines (proxy for business/first class travelers)
PREMIUM_AIRLINES = {
    "Qatar Airways", "Emirates", "Singapore Airlines", "Cathay Pacific Airways",
    "ANA All Nippon Airways", "EVA Air", "Hainan Airlines", "Garuda Indonesia",
    "Asiana Airlines", "Japan Airlines", "Korean Air", "Thai Airways",
    "Swiss International Air Lines", "Lufthansa", "British Airways",
    "Virgin Atlantic Airways", "Air New Zealand", "Etihad Airways",
    "Turkish Airlines", "KLM Royal Dutch Airlines", "Qantas Airways",
    "Finnair", "Austrian Airlines", "SAS Scandinavian Airlines",
    "Air France", "Delta Air Lines",
}


def is_premium(airline: str) -> bool:
    return any(
        pa.lower() in airline.lower() or airline.lower() in pa.lower()
        for pa in PREMIUM_AIRLINES
    )


# ─── Dimension mapping: airline annotation → user-side format ───
# The airline annotations have 18 bare dims. Map them to user_ prefixed
# keys that compute_brand_buyer_edge expects.
def map_to_user_side(ann: dict) -> dict:
    """Map 18-dim airline annotation to full user-side format."""
    return {
        # Big Five personality
        "user_personality_openness": ann.get("openness", 0.5),
        "user_personality_conscientiousness": ann.get("conscientiousness", 0.5),
        "user_personality_extraversion": ann.get("extraversion", 0.5),
        "user_personality_agreeableness": ann.get("agreeableness", 0.5),
        "user_personality_neuroticism": ann.get("neuroticism", 0.5),
        # Regulatory focus
        "user_regulatory_focus_promotion": ann.get("promotion_focus", 0.5),
        "user_regulatory_focus_prevention": ann.get("prevention_focus", 0.5),
        # Cognitive
        "user_need_for_cognition": ann.get("need_for_cognition", 0.5),
        "user_negativity_bias": ann.get("negativity_bias", 0.5),
        "user_reactance": ann.get("reactance", 0.5),
        # Brand/Consumer
        "user_brand_trust_known_brand_trust": ann.get("brand_trust", 0.5),
        "user_brand_trust_unknown_brand_skepticism": 1.0 - ann.get("brand_trust", 0.5),
        "user_brand_trust_review_reliance": 0.5,  # not available, use neutral
        "user_spending_pain_sensitivity": ann.get("spending_pain", 0.5),
        "user_self_monitoring": ann.get("self_monitoring", 0.5),
        # Emotional (inferred from rating + outcome)
        "user_emotion_pleasure": _rating_to_pleasure(ann.get("rating", 5)),
        "user_emotion_arousal": ann.get("emotional_expressiveness", 0.5),
        "user_emotion_dominance": 0.5 + 0.3 * (ann.get("promotion_focus", 0.5) - 0.5),
        # Social/Identity
        "user_implicit_drivers_identity_signaling": ann.get("status_seeking", 0.3),
        "user_anchor_susceptibility": ann.get("anchor_susceptibility", 0.5),
        # Decision style (inferred)
        "user_decision_style_maximizer": ann.get("detail_orientation", 0.5),
        "user_decision_style_information_search_depth": ann.get("detail_orientation", 0.5),
        # Construal (inferred: high detail = concrete/low construal)
        "user_construal_level": 1.0 - ann.get("detail_orientation", 0.5) * 0.6,
        # Social proof
        "user_social_proof_reliance": ann.get("social_proof_reliance", 0.5),
        # Uniqueness needs (inferred from openness + status_seeking)
        "user_uniqueness_need_creative_choice": ann.get("openness", 0.5) * 0.7,
        "user_uniqueness_need_unpopular_choice": max(0, ann.get("openness", 0.5) - 0.3) * 0.5,
        "user_uniqueness_need_avoidance_of_similarity": ann.get("status_seeking", 0.3) * 0.6,
        "user_optimal_distinctiveness": (ann.get("openness", 0.5) + ann.get("status_seeking", 0.3)) / 2,
        # Purchase involvement (luxury = high involvement)
        "user_purchase_involvement": 0.7,
        "user_anticipated_regret": ann.get("neuroticism", 0.5) * 0.6,
        # Annotation metadata
        "annotation_confidence": 0.65,  # batch annotation = moderate confidence
    }


def _rating_to_pleasure(rating: float) -> float:
    """Convert 1-10 rating to pleasure scale [0, 1]."""
    return max(0.0, min(1.0, (rating - 1) / 9.0))


# ─── Phase 1: Filter premium satisfied ───
def filter_premium_satisfied(annotations: list) -> list:
    """Filter to premium airline travelers with rating >= 7."""
    filtered = [
        a for a in annotations
        if is_premium(a.get("airline", "")) and a.get("rating", 0) >= 7
    ]
    print(f"Filtered: {len(filtered)} premium satisfied (from {len(annotations)} total)")
    return filtered


# ─── Phase 2: Compute bilateral edges ───
def compute_edges(filtered: list, ad_annotation: dict) -> list:
    """Compute bilateral alignment edges against LUXY Ride ad-side."""
    from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge

    edges = []
    for ann in filtered:
        user_side = map_to_user_side(ann)
        review_meta = {
            "rating": ann.get("rating", 5),
            "helpful_vote": 0,
            "total_vote": 0,
            "text": "",
            "category": "Luxury Transportation",
            "timestamp": 0,
        }
        try:
            edge = compute_brand_buyer_edge(
                ad_annotation=ad_annotation,
                user_annotation=user_side,
                review_meta=review_meta,
            )
            edge["_review_id"] = ann.get("review_id", "")
            edge["_airline"] = ann.get("airline", "")
            edge["_rating"] = ann.get("rating", 0)
            edge["_country"] = ann.get("country", "")
            edge["_outcome"] = ann.get("outcome", "")
            # Carry forward raw dims for clustering
            for dim in ["openness", "conscientiousness", "extraversion", "agreeableness",
                        "neuroticism", "promotion_focus", "prevention_focus",
                        "need_for_cognition", "negativity_bias", "reactance",
                        "brand_trust", "spending_pain", "self_monitoring",
                        "emotional_expressiveness", "social_proof_reliance",
                        "anchor_susceptibility", "status_seeking", "detail_orientation"]:
                edge[f"_raw_{dim}"] = ann.get(dim, 0.5)
            edges.append(edge)
        except Exception as e:
            pass  # skip failures silently

    print(f"Computed {len(edges)} bilateral edges")
    return edges


# ─── Phase 3: Archetype clustering with interaction effects ───
def cluster_archetypes(edges: list) -> dict:
    """Run archetype clustering with interaction effects."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score

    # Build feature matrix from raw dims
    raw_dims = ["openness", "conscientiousness", "extraversion", "agreeableness",
                "neuroticism", "promotion_focus", "prevention_focus",
                "need_for_cognition", "negativity_bias", "reactance",
                "brand_trust", "spending_pain", "self_monitoring",
                "emotional_expressiveness", "social_proof_reliance",
                "anchor_susceptibility", "status_seeking", "detail_orientation"]

    X_raw = np.array([[e.get(f"_raw_{d}", 0.5) for d in raw_dims] for e in edges])

    # Add interaction terms (the key ones from LUXY Ride discovery)
    interactions = []
    for e in edges:
        r = lambda d: e.get(f"_raw_{d}", 0.5)
        interactions.append([
            r("openness") * r("promotion_focus"),              # Explorer
            r("agreeableness") * r("brand_trust"),             # Loyalist/Reliable Cooperator
            r("conscientiousness") * r("agreeableness"),       # Reliable Cooperator
            r("conscientiousness") * r("prevention_focus"),    # Prevention Planner
            r("neuroticism") * r("spending_pain"),             # Anxious Economist
            r("emotional_expressiveness") * r("reactance"),    # Vocal Resistor
            r("promotion_focus") * r("status_seeking"),        # Status-Seeking Promoter
            r("detail_orientation") * r("need_for_cognition"), # Analytical Evaluator
            r("openness") * r("status_seeking"),               # Aspirational Explorer
            (1.0 - r("neuroticism")) * r("brand_trust"),       # Confident Truster
        ])
    X_interactions = np.array(interactions)

    # Combined feature matrix
    X = np.hstack([X_raw, X_interactions])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Test K=2 through K=10
    print("\n=== Archetype Clustering ===")
    print(f"Features: {X.shape[1]} ({len(raw_dims)} raw + {X_interactions.shape[1]} interactions)")
    print(f"Samples: {X.shape[0]}")

    results = {}
    for k in range(2, 11):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels, sample_size=min(5000, len(X_scaled)))
        sizes = Counter(labels)
        results[k] = {
            "silhouette": sil,
            "labels": labels,
            "centers": km.cluster_centers_,
            "sizes": dict(sizes),
        }
        print(f"  K={k}: silhouette={sil:.4f}, sizes={dict(sorted(sizes.items()))}")

    # Find best K
    best_k = max(results, key=lambda k: results[k]["silhouette"])
    print(f"\nBest K={best_k} (silhouette={results[best_k]['silhouette']:.4f})")

    # Also test K=6 (to match LUXY Ride's 6 archetypes) and K=8 (original)
    for target_k in [6, 8]:
        if target_k in results:
            print(f"K={target_k} silhouette: {results[target_k]['silhouette']:.4f}")

    return results, X_raw, raw_dims, best_k


# ─── Phase 4: Profile each archetype ───
def profile_archetypes(edges: list, results: dict, X_raw: np.ndarray,
                       raw_dims: list, k: int) -> list:
    """Profile each archetype cluster."""
    labels = results[k]["labels"]
    centers = results[k]["centers"]

    raw_dims_full = raw_dims  # base dims only for profiling

    print(f"\n=== Archetype Profiles (K={k}) ===")
    archetypes = []

    for cluster_id in range(k):
        mask = labels == cluster_id
        cluster_edges = [e for e, m in zip(edges, mask) if m]
        cluster_raw = X_raw[mask]
        n = len(cluster_edges)

        # Mean dims
        dim_means = {}
        for i, dim in enumerate(raw_dims_full):
            dim_means[dim] = float(cluster_raw[:, i].mean())

        # Edge alignment means
        edge_dims = ["composite_alignment", "regulatory_fit_score", "brand_trust_fit",
                     "emotional_resonance", "personality_brand_alignment",
                     "reactance_fit", "spending_pain_match", "negativity_bias_match"]
        edge_means = {}
        for ed in edge_dims:
            vals = [e.get(ed, 0) for e in cluster_edges]
            edge_means[ed] = float(np.mean(vals)) if vals else 0.0

        # Outcome distribution
        outcomes = Counter(e.get("_outcome", "") for e in cluster_edges)

        # Conversion proxy (satisfied + evangelized = converted)
        converted = outcomes.get("satisfied", 0) + outcomes.get("evangelized", 0)
        total = n
        conversion_rate = converted / total if total > 0 else 0

        # Identify dominant traits (>= 0.6) and weak traits (<= 0.4)
        high_traits = [(d, v) for d, v in dim_means.items() if v >= 0.6]
        low_traits = [(d, v) for d, v in dim_means.items() if v <= 0.4]

        # Interaction effects
        interactions = {
            "openness×promotion": dim_means["openness"] * dim_means["promotion_focus"],
            "agreeableness×brand_trust": dim_means["agreeableness"] * dim_means["brand_trust"],
            "conscientiousness×agreeableness": dim_means["conscientiousness"] * dim_means["agreeableness"],
            "conscientiousness×prevention": dim_means["conscientiousness"] * dim_means["prevention_focus"],
            "neuroticism×spending_pain": dim_means["neuroticism"] * dim_means["spending_pain"],
            "expressiveness×reactance": dim_means["emotional_expressiveness"] * dim_means["reactance"],
        }

        # Name the archetype based on dominant pattern
        archetype_name = _name_archetype(dim_means, interactions, conversion_rate)

        archetype = {
            "cluster_id": cluster_id,
            "name": archetype_name,
            "n": n,
            "pct": n / len(edges) * 100,
            "conversion_rate": conversion_rate,
            "dim_means": dim_means,
            "edge_means": edge_means,
            "outcomes": dict(outcomes),
            "interactions": interactions,
            "high_traits": sorted(high_traits, key=lambda x: -x[1]),
            "low_traits": sorted(low_traits, key=lambda x: x[1]),
        }
        archetypes.append(archetype)

        print(f"\n--- Cluster {cluster_id}: {archetype_name} ---")
        print(f"  N={n} ({archetype['pct']:.1f}%), conversion={conversion_rate:.1%}")
        print(f"  Composite alignment: {edge_means.get('composite_alignment', 0):.4f}")
        print(f"  High traits: {', '.join(f'{d}={v:.2f}' for d, v in high_traits[:5])}")
        print(f"  Low traits: {', '.join(f'{d}={v:.2f}' for d, v in low_traits[:5])}")
        print(f"  Key interactions: {', '.join(f'{k}={v:.3f}' for k, v in sorted(interactions.items(), key=lambda x: -x[1])[:3])}")
        print(f"  Outcomes: {dict(outcomes)}")

    return archetypes


def _name_archetype(dims: dict, interactions: dict, conv_rate: float) -> str:
    """Heuristic archetype naming based on dominant psychological pattern."""
    # Check interaction patterns first
    if interactions["openness×promotion"] > 0.35 and dims["openness"] > 0.6:
        return "Explorer"
    if interactions["neuroticism×spending_pain"] > 0.3 and dims["neuroticism"] > 0.6:
        return "Anxious Economist"
    if interactions["expressiveness×reactance"] > 0.3 and dims["reactance"] > 0.6:
        return "Vocal Resistor"
    if interactions["conscientiousness×prevention"] > 0.35 and dims["prevention_focus"] > 0.6:
        return "Prevention Planner"
    if interactions["conscientiousness×agreeableness"] > 0.45 and dims["brand_trust"] > 0.6:
        return "Reliable Cooperator"
    if interactions["agreeableness×brand_trust"] > 0.5:
        return "Trusting Loyalist"

    # Fall back to single-dimension dominance
    if dims["brand_trust"] > 0.7 and dims["agreeableness"] > 0.7:
        return "Status Seeker"
    if dims["negativity_bias"] > 0.7:
        return "Skeptical Evaluator"
    if dims["promotion_focus"] > 0.6 and dims["status_seeking"] > 0.5:
        return "Aspirational Striver"
    if dims["conscientiousness"] > 0.7 and dims["detail_orientation"] > 0.7:
        return "Analytical Decider"
    if conv_rate > 0.85:
        return "Easy Decider"
    if conv_rate < 0.15:
        return "Resistant Non-Converter"

    return f"Segment ({conv_rate:.0%} conv)"


# ─── Phase 5: Compare with LUXY Ride archetypes ───
def compare_with_luxy(archetypes: list):
    """Compare airline-derived archetypes with LUXY Ride originals."""
    print("\n\n=== COMPARISON: Airline Premium vs LUXY Ride Archetypes ===")

    # LUXY Ride original archetypes (from previous analysis)
    luxy_archetypes = {
        "Careful Truster": {"brand_trust": 0.78, "neuroticism": 0.38, "spending_pain": 0.42,
                            "prevention_focus": 0.55, "conv": 0.72},
        "Status Seeker": {"brand_trust": 0.82, "status_seeking": 0.65, "promotion_focus": 0.72,
                          "spending_pain": 0.25, "conv": 0.85},
        "Easy Decider": {"brand_trust": 0.70, "conscientiousness": 0.55, "detail_orientation": 0.45,
                         "neuroticism": 0.30, "conv": 0.90},
        "Explorer": {"openness": 0.78, "promotion_focus": 0.70, "status_seeking": 0.55,
                     "brand_trust": 0.60, "conv": 0.82},
        "Prevention Planner": {"prevention_focus": 0.72, "conscientiousness": 0.75,
                               "detail_orientation": 0.78, "neuroticism": 0.48, "conv": 0.65},
        "Reliable Cooperator": {"conscientiousness": 0.72, "agreeableness": 0.75,
                                "brand_trust": 0.70, "promotion_focus": 0.55, "conv": 0.78},
    }

    for airline_arch in archetypes:
        print(f"\n  {airline_arch['name']} (N={airline_arch['n']}, conv={airline_arch['conversion_rate']:.1%})")
        # Find closest LUXY match
        best_match, best_sim = None, -1
        for luxy_name, luxy_dims in luxy_archetypes.items():
            shared_dims = set(airline_arch["dim_means"].keys()) & set(luxy_dims.keys()) - {"conv"}
            if not shared_dims:
                continue
            diffs = [abs(airline_arch["dim_means"].get(d, 0.5) - luxy_dims.get(d, 0.5)) for d in shared_dims]
            sim = 1.0 - (sum(diffs) / len(diffs))
            if sim > best_sim:
                best_sim = sim
                best_match = luxy_name
        if best_match:
            print(f"    → Closest LUXY match: {best_match} (similarity={best_sim:.3f})")
            # Show dimension gaps
            luxy_d = luxy_archetypes[best_match]
            for d in sorted(luxy_d.keys()):
                if d == "conv":
                    continue
                airline_val = airline_arch["dim_means"].get(d, 0.5)
                gap = airline_val - luxy_d[d]
                if abs(gap) > 0.05:
                    print(f"      {d}: airline={airline_val:.2f} luxy={luxy_d[d]:.2f} gap={gap:+.2f}")


# ─── Phase 6: Conversion prediction analysis ───
def conversion_analysis(edges: list):
    """Analyze which dimensions predict conversion in airline data."""
    print("\n\n=== CONVERSION PREDICTION ANALYSIS ===")

    raw_dims = ["openness", "conscientiousness", "extraversion", "agreeableness",
                "neuroticism", "promotion_focus", "prevention_focus",
                "need_for_cognition", "negativity_bias", "reactance",
                "brand_trust", "spending_pain", "self_monitoring",
                "emotional_expressiveness", "social_proof_reliance",
                "anchor_susceptibility", "status_seeking", "detail_orientation"]

    # Binary conversion: satisfied/evangelized = 1, warned/regret = 0
    converted = []
    non_converted = []
    for e in edges:
        outcome = e.get("_outcome", "")
        if outcome in ("satisfied", "evangelized"):
            converted.append(e)
        elif outcome in ("warned", "regret"):
            non_converted.append(e)

    print(f"Converted: {len(converted)}, Non-converted: {len(non_converted)}")
    print(f"(Excluding {len(edges) - len(converted) - len(non_converted)} neutral)")

    # Dimension gaps
    print(f"\n{'Dimension':<28} {'Converted':>10} {'Non-conv':>10} {'Gap':>8} {'Predictive':>12}")
    print("-" * 70)

    predictive_dims = []
    for dim in raw_dims:
        conv_vals = [e.get(f"_raw_{dim}", 0.5) for e in converted]
        nonc_vals = [e.get(f"_raw_{dim}", 0.5) for e in non_converted]
        conv_mean = np.mean(conv_vals) if conv_vals else 0
        nonc_mean = np.mean(nonc_vals) if nonc_vals else 0
        gap = conv_mean - nonc_mean
        predictive = "***" if abs(gap) > 0.3 else ("**" if abs(gap) > 0.15 else ("*" if abs(gap) > 0.05 else ""))
        print(f"{dim:<28} {conv_mean:>10.3f} {nonc_mean:>10.3f} {gap:>+8.3f} {predictive:>12}")
        predictive_dims.append((dim, gap))

    # Edge dimension gaps
    print(f"\n{'Edge Dimension':<35} {'Converted':>10} {'Non-conv':>10} {'Gap':>8}")
    print("-" * 65)
    edge_dims = ["composite_alignment", "regulatory_fit_score", "brand_trust_fit",
                 "emotional_resonance", "personality_brand_alignment",
                 "reactance_fit", "spending_pain_match", "negativity_bias_match",
                 "appeal_resonance", "value_alignment"]
    for ed in edge_dims:
        conv_vals = [e.get(ed, 0) for e in converted]
        nonc_vals = [e.get(ed, 0) for e in non_converted]
        conv_mean = np.mean(conv_vals) if conv_vals else 0
        nonc_mean = np.mean(nonc_vals) if nonc_vals else 0
        gap = conv_mean - nonc_mean
        print(f"{ed:<35} {conv_mean:>10.4f} {nonc_mean:>10.4f} {gap:>+8.4f}")

    # Top interaction effects
    print("\n--- Interaction Effect Gaps ---")
    interaction_pairs = [
        ("openness", "promotion_focus", "Explorer"),
        ("agreeableness", "brand_trust", "Loyalist"),
        ("conscientiousness", "agreeableness", "Reliable Cooperator"),
        ("conscientiousness", "prevention_focus", "Prevention Planner"),
        ("neuroticism", "spending_pain", "Anxious Economist"),
        ("emotional_expressiveness", "reactance", "Vocal Resistor"),
        ("promotion_focus", "status_seeking", "Status Promoter"),
        ("openness", "status_seeking", "Aspirational Explorer"),
        ("detail_orientation", "need_for_cognition", "Analytical"),
        ("brand_trust", "promotion_focus", "Confident Promoter"),
    ]
    for d1, d2, name in interaction_pairs:
        conv_vals = [e.get(f"_raw_{d1}", 0.5) * e.get(f"_raw_{d2}", 0.5) for e in converted]
        nonc_vals = [e.get(f"_raw_{d1}", 0.5) * e.get(f"_raw_{d2}", 0.5) for e in non_converted]
        conv_mean = np.mean(conv_vals)
        nonc_mean = np.mean(nonc_vals)
        gap = conv_mean - nonc_mean
        lift = conv_mean / nonc_mean if nonc_mean > 0 else float("inf")
        flag = " ← SUPPRESS" if gap < -0.1 else (" ← TARGET" if gap > 0.1 else "")
        print(f"  {name} ({d1}×{d2}): conv={conv_mean:.3f} nonconv={nonc_mean:.3f} "
              f"gap={gap:+.3f} lift={lift:.2f}x{flag}")


# ─── Main ───
def main():
    print("=" * 70)
    print("PREMIUM AIRLINE → LUXY RIDE PROXY ANALYSIS")
    print("=" * 70)

    # Load data
    print("\nLoading annotations...")
    with open(ANNOTATIONS_FILE) as f:
        all_annotations = json.load(f)
    print(f"  Total annotations: {len(all_annotations)}")

    print("Loading LUXY Ride ad-side annotations...")
    with open(AD_SIDE_FILE) as f:
        ad_annotations = json.load(f)
    luxy_ad = ad_annotations.get("LUXY Ride") or ad_annotations.get("LUXYRide")
    if not luxy_ad:
        print("ERROR: LUXY Ride ad-side annotation not found")
        return
    print(f"  LUXY Ride ad-side: {len([k for k in luxy_ad if k.startswith('ad_')])} dimensions")

    # Phase 1: Filter
    filtered = filter_premium_satisfied(all_annotations)

    # Phase 2: Compute edges
    print("\nComputing bilateral edges against LUXY Ride ad-side...")
    edges = compute_edges(filtered, luxy_ad)

    # Phase 3: Cluster
    results, X_raw, raw_dims, best_k = cluster_archetypes(edges)

    # Phase 4: Profile archetypes (for best K AND K=6)
    for k_val in [best_k, 6]:
        if k_val in results:
            archetypes = profile_archetypes(edges, results, X_raw, raw_dims, k_val)

    # Phase 5: Compare with LUXY
    archetypes_6 = profile_archetypes(edges, results, X_raw, raw_dims, 6)
    compare_with_luxy(archetypes_6)

    # Phase 6: Conversion analysis
    conversion_analysis(edges)

    # Save results
    output = {
        "filter": "premium_airlines_rating_gte_7",
        "total_filtered": len(filtered),
        "total_edges": len(edges),
        "best_k": best_k,
        "best_silhouette": results[best_k]["silhouette"],
        "clustering_results": {
            str(k): {"silhouette": v["silhouette"], "sizes": {str(sk): sv for sk, sv in v["sizes"].items()}}
            for k, v in results.items()
        },
        "archetypes_k6": [
            {k: v for k, v in a.items() if k != "centers"}
            for a in archetypes_6
        ],
    }
    output_file = OUTPUT_DIR / "premium_airline_archetype_analysis.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
