#!/usr/bin/env python3
# =============================================================================
# End-to-End Simulation: Nonconscious Signal Intelligence + Methodological Upgrades
# =============================================================================

"""
Simulates a 7-touch retargeting sequence exercising EVERY new capability
built in this session:

  Enhancement #34 (6 Signals):
    1. Click Latency trajectory (resolving → building detection)
    2. Barrier Self-Report (section dwell → override)
    3. Organic Return (surge detection → INTENDING stage)
    4. Processing Depth (power posterior weighting 0.05-1.0)
    5. Device Compatibility (ELM mechanism-device matrix)
    6. Frequency Decay (reactance onset detection)

  Session 34-2:
    - Frustration scoring (27 frustrated pairs, r=-0.582)

  Session 34-3:
    - Neural-LinUCB (57-dim context, primary mechanism selector)

  Session 34-4:
    - Annotation confidence weighting

  CCA Follow-up:
    - Dimension compressor (25→7 PCs, PC1 r=-0.849)

  Session 34-6:
    - Options Framework (stage lifecycle management)

Usage:
    PYTHONPATH=. python scripts/simulate_nonconscious_signals.py
"""

import sys
import time
import numpy as np

CHECKS_PASSED = 0
CHECKS_TOTAL = 0


def check(name: str, condition: bool, detail: str = ""):
    global CHECKS_PASSED, CHECKS_TOTAL
    CHECKS_TOTAL += 1
    status = "PASS" if condition else "FAIL"
    if condition:
        CHECKS_PASSED += 1
    suffix = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if not condition:
        print(f"         *** FAILED ***")


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main():
    print("=" * 60)
    print("E2E SIMULATION: Nonconscious Signal Intelligence")
    print("=" * 60)

    # ══════════════════════════════════════════════════════════════
    section("1. SIGNAL ENGINES — Individual Verification")
    # ══════════════════════════════════════════════════════════════

    # Signal 1: Click Latency
    from adam.retargeting.engines.click_latency import (
        ClickLatencyTracker, ConflictClass, TrajectoryType,
    )
    tracker1 = ClickLatencyTracker()
    conflict = tracker1.classify_conflict(2.5, "desktop")
    check("Click latency: classify conflict", conflict == ConflictClass.MODERATE)

    traj = tracker1.compute_trajectory([5.0, 4.0, 3.0, 2.0, 1.5])
    check("Click latency: resolving trajectory",
          traj["trajectory_type"] == "resolving", f"slope={traj['slope']:.2f}")

    traj_build = tracker1.compute_trajectory([1.0, 2.0, 3.5, 5.0])
    check("Click latency: building trajectory",
          traj_build["trajectory_type"] == "building")

    # Signal 2: Barrier Self-Report
    from adam.retargeting.engines.barrier_self_report import BarrierSelfReportExtractor
    from adam.retargeting.models.telemetry import SectionEngagement
    extractor = BarrierSelfReportExtractor()

    barrier_result = extractor.extract_barrier([
        SectionEngagement(section_id="section-pricing", dwell_seconds=15.0, interactions=3),
        SectionEngagement(section_id="section-reviews", dwell_seconds=5.0),
    ])
    check("Barrier self-report: extraction",
          barrier_result["self_reported_barrier"] == "price_friction",
          f"conf={barrier_result['confidence']:.2f}")

    override = extractor.compare_to_algorithmic(barrier_result, "trust_deficit")
    check("Barrier self-report: override fires",
          override["override"] is True, f"barrier={override['barrier']}")

    # Signal 3: Organic Return
    from adam.retargeting.engines.organic_return import OrganicReturnTracker
    tracker3 = OrganicReturnTracker()

    stage = tracker3.get_stage_signal([False, True, True, True], 0.15)
    check("Organic return: INTENDING on surge",
          stage["stage"] == "intending", f"surge={stage['surge_multiplier']}x")

    stage_ext = tracker3.get_stage_signal([False, False, False, False], 0.15)
    check("Organic return: EXTERNALLY when all ad-prompted",
          stage_ext["stage"] == "evaluating_externally")

    # Signal 4: Processing Depth
    from adam.retargeting.engines.processing_depth import (
        ProcessingDepth, classify_processing_depth, get_processing_weight,
    )
    depth = classify_processing_depth(0.5, False)
    check("Processing depth: unprocessed < 1s",
          depth == ProcessingDepth.UNPROCESSED, f"w={get_processing_weight(depth)}")

    depth_click = classify_processing_depth(0.3, True)
    check("Processing depth: click always evaluated",
          depth_click == ProcessingDepth.EVALUATED)

    # Signal 5: Device Compatibility
    from adam.retargeting.engines.device_compat import DeviceEngagementTracker
    tracker5 = DeviceEngagementTracker()
    h1_mod = tracker5.get_h1_modifier("evidence_proof", "mobile")
    check("Device compat: central route on mobile = mismatch",
          h1_mod == 0.15, f"H1={h1_mod}")

    rec = tracker5.recommend_device("evidence_proof", {}, {})
    check("Device compat: evidence_proof → desktop",
          rec["recommended_device"] == "desktop")

    # Signal 6: Frequency Decay
    from adam.retargeting.engines.frequency_decay import FrequencyDecayDetector
    tracker6 = FrequencyDecayDetector()
    react = tracker6.detect_reactance([True, True, False, False, False, False, False])
    check("Frequency decay: reactance detected",
          react["reactance_detected"], f"onset=touch#{react['reactance_onset_touch']}")

    no_react = tracker6.detect_reactance([False, False, False, True, True, True])
    check("Frequency decay: improving = no reactance",
          not no_react["reactance_detected"], f"H4={no_react['h4_modifier']}")

    # ══════════════════════════════════════════════════════════════
    section("2. COMPOSITE PROFILE — Aggregation")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.models.telemetry import StoredSignalProfile
    from adam.retargeting.engines.nonconscious_profile import (
        NonconsciousProfile, build_from_stored_profile, enrich_diagnostic_input,
    )

    stored = StoredSignalProfile(
        user_id="sim_user_001",
        total_sessions=7, ad_attributed_sessions=4, organic_sessions=3,
        click_latencies=[5.0, 4.0, 3.0, 2.0],
        click_latency_trajectory="resolving", click_latency_slope=-1.0,
        latest_conflict_class="moderate",
        section_dwell_totals={"section-pricing": 30.0, "section-reviews": 10.0},
        section_interaction_totals={"section-pricing": 5},
        self_reported_barrier="price_friction",
        barrier_self_report_confidence=0.75,
        barrier_dimensions_to_target=["anchor_susceptibility_match"],
        visit_is_organic=[False, False, True, False, True, False, True],
        organic_stage="evaluating_with_interest",
        organic_surge_multiplier=2.5,
        device_impressions={"desktop": 4, "mobile": 3},
        device_clicks={"desktop": 2, "mobile": 0},
        touch_outcomes=[True, False, True, False, True, False],
        reactance_detected=False, reactance_h4_modifier=-0.10,
        hour_engagement_counts={9: 3, 14: 2, 20: 2},
    )

    nc = build_from_stored_profile(stored, last_mechanism="evidence_proof", last_device="mobile")
    check("NonconsciousProfile: built",
          nc.user_id == "sim_user_001")
    check("NonconsciousProfile: trajectory propagated",
          nc.click_latency_trajectory == "resolving")
    check("NonconsciousProfile: barrier override active",
          nc.barrier_override_active, f"conf={nc.barrier_confidence}")
    check("NonconsciousProfile: device mismatch detected",
          nc.device_mechanism_mismatch, "evidence_proof on mobile")

    h_mods = nc.compute_aggregate_h_modifiers()
    check("H-modifiers: H4 negative (resolving + no reactance)",
          h_mods["H4"] < 0, f"H4={h_mods['H4']:.2f}")
    check("H-modifiers: H1 positive (device mismatch)",
          h_mods["H1"] > 0, f"H1={h_mods['H1']:.2f}")
    check("H-modifiers: all clamped [-0.5, 0.5]",
          all(-0.5 <= v <= 0.5 for v in h_mods.values()))

    # ══════════════════════════════════════════════════════════════
    section("3. DIAGNOSTIC INPUT ENRICHMENT")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.models.diagnostic_assessment import DiagnosticInput

    bilateral = {
        "regulatory_fit_score": 0.75, "emotional_resonance": 0.85,
        "brand_trust_fit": 0.80, "reactance_fit": 0.20,
        "value_alignment": 0.70, "anchor_susceptibility_match": 0.65,
        "appeal_resonance": 0.60, "personality_brand_alignment": 0.70,
        "negativity_bias_match": 0.15, "spending_pain_match": 0.30,
    }

    inp = DiagnosticInput(
        user_id="sim_user_001", brand_id="luxy_ride",
        archetype_id="careful_truster",
        bilateral_edge=bilateral,
        current_barrier="trust_deficit",
    )
    enriched = enrich_diagnostic_input(inp, nc)

    check("Enrichment: H-modifiers applied",
          len(enriched.external_h_modifiers) == 5)
    check("Enrichment: barrier override flagged",
          enriched.behavioral_signals.get("barrier_self_report_override") == 1.0)
    check("Enrichment: frustration score computed",
          enriched.frustration_score > 0, f"frust={enriched.frustration_score:.3f}")

    # ══════════════════════════════════════════════════════════════
    section("4. FRUSTRATION SCORING")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.engines.frustration import FrustrationScorer
    scorer = FrustrationScorer()

    frust = scorer.score(bilateral)
    check("Frustration: score computed", frust > 0, f"score={frust:.3f}")

    tensions = scorer.identify_tensions(bilateral)
    check("Frustration: tensions identified", len(tensions) > 0, f"n={len(tensions)}")

    seq_rec = scorer.recommend_sequence(bilateral, "anchor_susceptibility_match")
    check("Frustration: sequencing recommendation",
          isinstance(seq_rec["should_defer"], bool),
          f"defer={seq_rec['should_defer']}")

    # ══════════════════════════════════════════════════════════════
    section("5. DIMENSION COMPRESSOR")
    # ══════════════════════════════════════════════════════════════

    from adam.intelligence.dimension_compressor import get_dimension_compressor
    comp = get_dimension_compressor()

    check("Compressor: fitted", comp.is_fitted)

    pcs = comp.compress(bilateral)
    check("Compressor: 7 PCs", len(pcs) == 7, f"PC1={pcs[0]:.2f}")

    conv_good = comp.get_conversion_score(bilateral)
    conv_bad = comp.get_conversion_score({
        "reactance_fit": 0.9, "emotional_resonance": 0.1,
        "brand_trust_fit": 0.1, "negativity_bias_match": 0.8,
    })
    check("Compressor: good edge > bad edge",
          conv_good > conv_bad, f"good={conv_good:.3f}, bad={conv_bad:.3f}")

    # ══════════════════════════════════════════════════════════════
    section("6. NEURAL-LINUCB (57-dim context)")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.engines.neural_linucb import NeuralLinUCBSelector, BILATERAL_CONTEXT_DIMS

    check("LinUCB context dims", len(BILATERAL_CONTEXT_DIMS) == 57,
          f"n={len(BILATERAL_CONTEXT_DIMS)}")

    selector = NeuralLinUCBSelector()
    check("LinUCB: PCA auto-enrichment",
          "pca_pc1" in selector._enrich_with_pca(bilateral))

    candidates = ["evidence_proof", "narrative_transportation", "social_proof_matched", "loss_framing"]

    # Cold start: uniform UCB
    r1 = selector.select(bilateral_edge=bilateral, candidate_mechanisms=candidates)
    check("LinUCB: cold start select", r1.selected_mechanism in candidates,
          f"mech={r1.selected_mechanism}, UCB={r1.ucb_score:.4f}")

    # Train with outcomes
    for _ in range(5):
        selector.update(bilateral, "evidence_proof", 1.0)
        selector.update(bilateral, "narrative_transportation", 0.2)

    r2 = selector.select(bilateral_edge=bilateral, candidate_mechanisms=candidates)
    check("LinUCB: learns from outcomes",
          r2.selected_mechanism == "evidence_proof",
          f"mech={r2.selected_mechanism}, UCB={r2.ucb_score:.4f}")

    check("LinUCB: latency < 50ms", r2.latency_ms < 50, f"{r2.latency_ms:.1f}ms")

    # ══════════════════════════════════════════════════════════════
    section("7. PROCESSING DEPTH → POSTERIOR WEIGHTING")
    # ══════════════════════════════════════════════════════════════

    from adam.cold_start.models.priors import BetaDistribution

    # 100 unprocessed vs 100 processed non-clicks
    unproc = BetaDistribution(alpha=5.0, beta=5.0)
    proc = BetaDistribution(alpha=5.0, beta=5.0)
    for _ in range(100):
        unproc = unproc.weighted_update(False, weight=0.05)
        proc = proc.weighted_update(False, weight=1.0)

    check("Posterior: unprocessed barely shifts",
          unproc.mean > 0.25, f"mean={unproc.mean:.4f}")
    check("Posterior: processed shifts strongly",
          proc.mean < 0.10, f"mean={proc.mean:.4f}")
    check("Posterior: divergence is large",
          abs(unproc.mean - proc.mean) > 0.2,
          f"delta={abs(unproc.mean - proc.mean):.3f}")

    # ══════════════════════════════════════════════════════════════
    section("8. OPTIONS FRAMEWORK (Stage Lifecycle)")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.engines.options_framework import OptionsController
    from adam.retargeting.models.enums import ConversionStage, BarrierCategory

    ctrl = OptionsController()
    opt = ctrl.get_active_option(ConversionStage.EVALUATING)
    check("Options: EVALUATING option loaded",
          opt.stage == ConversionStage.EVALUATING, f"max_touches={opt.max_touches}")

    allowed = ctrl.get_allowed_mechanisms(opt, BarrierCategory.TRUST_DEFICIT)
    check("Options: mechanisms filtered by stage+barrier",
          len(allowed) > 0, f"n={len(allowed)}")

    # Advance signal
    term = ctrl.check_termination(opt, {"booking_start": 1.0}, touches_in_stage=2)
    check("Options: advance on booking signal",
          term[0] is True, f"reason={term[1]}, next={term[2]}")

    # Max touches
    term2 = ctrl.check_termination(opt, {}, touches_in_stage=10)
    check("Options: terminate on max touches",
          term2[0] is True, f"reason={term2[1]}")

    # ══════════════════════════════════════════════════════════════
    section("9. SIGNAL COLLECTOR PIPELINE")
    # ══════════════════════════════════════════════════════════════

    from adam.retargeting.engines.signal_collector import NonconsciousSignalCollector
    from adam.retargeting.models.telemetry import (
        TelemetrySessionPayload, DeviceType, ReferralType,
    )

    # Test derived signal computation (no Redis needed)
    collector = NonconsciousSignalCollector.__new__(NonconsciousSignalCollector)

    profile = StoredSignalProfile(
        user_id="pipe_test",
        click_latencies=[6.0, 4.0, 2.5],
        section_dwell_totals={"section-pricing": 20.0},
        section_interaction_totals={"section-pricing": 3},
        visit_is_organic=[False, True, True, False, True],
        touch_outcomes=[True, True, False, False, False, False],
    )
    payload = TelemetrySessionPayload(
        visitor_id="pipe_test", session_id="s1",
        device_type=DeviceType.DESKTOP,
        referral_type=ReferralType.DIRECT,
        arrival_timestamp=time.time(), landing_page="/",
    )

    collector._compute_click_latency_trajectory(profile, payload)
    collector._compute_barrier_self_report(profile, payload)
    collector._compute_organic_return(profile, 0.15)
    collector._compute_frequency_decay(profile)

    check("Pipeline: trajectory computed",
          profile.click_latency_trajectory == "resolving")
    check("Pipeline: barrier extracted",
          profile.self_reported_barrier == "price_friction")
    check("Pipeline: organic stage computed",
          profile.organic_stage == "intending",
          f"surge={profile.organic_surge_multiplier}")
    check("Pipeline: reactance detected",
          profile.reactance_detected, f"onset={profile.reactance_onset_touch}")

    # Serialization roundtrip
    json_str = profile.model_dump_json()
    restored = StoredSignalProfile.model_validate_json(json_str)
    check("Pipeline: serialization roundtrip",
          restored.click_latency_trajectory == "resolving"
          and restored.reactance_detected
          and restored.self_reported_barrier == "price_friction")

    # ══════════════════════════════════════════════════════════════
    section("10. API ROUTES")
    # ══════════════════════════════════════════════════════════════

    from adam.api.signals.router import router
    routes = sorted(r.path for r in router.routes)
    expected = [
        "/api/v1/signals/health",
        "/api/v1/signals/population",
        "/api/v1/signals/session",
        "/api/v1/signals/user/{user_id}",
        "/api/v1/signals/user/{user_id}/nonconscious-profile",
    ]
    check("API: all 5 routes registered",
          routes == expected, f"routes={routes}")

    # ══════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════

    print()
    print("=" * 60)
    if CHECKS_PASSED == CHECKS_TOTAL:
        print(f"  ALL {CHECKS_TOTAL} CHECKS PASS")
    else:
        print(f"  {CHECKS_PASSED}/{CHECKS_TOTAL} CHECKS PASS")
        print(f"  {CHECKS_TOTAL - CHECKS_PASSED} FAILURES")
    print("=" * 60)

    return 0 if CHECKS_PASSED == CHECKS_TOTAL else 1


if __name__ == "__main__":
    sys.exit(main())
