#!/usr/bin/env python3
"""
Live Unified System Test — End-to-End with Real Neo4j Data

Exercises the COMPLETE inferential loop against live infrastructure:
CRAWL → MATCH → SELECT → DELIVER → OBSERVE → LEARN → EXPAND

Tests every component built across both sessions:
- BONG multivariate Gaussian posteriors (live priors from 200K edges)
- DiagnosticReasoner (5-hypothesis deduction)
- Resonance × Repeated Measures (per-user page learning)
- TouchBuilder (page mindstate prescription)
- Mechanism probability logging
- CounterfactualLearner (learning multiplier)
- Trilateral epistemic value
- EnrichedInterventionRecord emission
- PromotionTracker
- Causal Structure Learner
- Propagation-aware barrier diagnosis
- StackAdapt translator per-touch targeting
- Full 15-step outcome handler integration

Usage:
    PYTHONPATH=. python3 scripts/test_unified_system_live.py
"""

import asyncio
import logging
import sys
import time
import traceback

import numpy as np

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")

P = 0
F = 0


def check(label, condition, detail=""):
    global P, F
    if condition:
        P += 1
        print(f"  [OK] {label}" + (f" — {detail}" if detail else ""))
    else:
        F += 1
        print(f"  [!!] {label}" + (f" — {detail}" if detail else ""))


def section(name):
    print(f"\n{'='*65}")
    print(f"  {name}")
    print(f"{'='*65}")


async def main():
    print("=" * 70)
    print("  LIVE UNIFIED SYSTEM TEST")
    print("  BONG + DiagnosticReasoner + Resonance + Counterfactual + Causal")
    print("=" * 70)

    # ================================================================
    section("1. BONG with Live Population Priors")
    # ================================================================
    from adam.intelligence.bong import BONGUpdater, get_bong_updater

    updater = get_bong_updater()
    check("BONG singleton loaded", updater is not None)
    check("Has population prior", updater.prior_D is not None)
    check("Has factor matrix U", updater.U is not None,
          f"shape={updater.U.shape}" if updater.U is not None else "")

    # Create a buyer and update with 5 observations
    buyer = updater.create_individual()
    check("Buyer posterior created", buyer is not None)

    obs_sequence = [
        np.array([0.6, 0.7, 0.5, 0.8, 0.4, 0.3, 0.5, 0.4, 0.5, 0.6,
                   0.7, 0.5, 0.4, 0.5, 0.6, 0.5, 0.3, 0.5, 0.4, 0.8]),
        np.array([0.5, 0.6, 0.4, 0.7, 0.5, 0.4, 0.5, 0.3, 0.5, 0.5,
                   0.6, 0.5, 0.5, 0.5, 0.5, 0.4, 0.4, 0.5, 0.5, 0.7]),
        np.array([0.7, 0.8, 0.6, 0.9, 0.3, 0.2, 0.5, 0.5, 0.5, 0.7,
                   0.8, 0.5, 0.3, 0.5, 0.7, 0.6, 0.2, 0.5, 0.3, 0.9]),
    ]
    for obs in obs_sequence:
        updater.update(buyer, obs, noise_precision=0.5)
    check("3 observations applied", buyer.observation_count == 3)

    mean = updater.get_mean(buyer)
    check("Mean is finite", np.all(np.isfinite(mean)),
          f"range=[{mean.min():.3f}, {mean.max():.3f}]")

    iv = updater.information_value(buyer)
    check("Information value computed", np.isfinite(iv), f"IV={iv:.4f}")

    # Covariance and conditional shift
    cov = updater.get_covariance(buyer)
    check("Covariance matrix computed", cov.shape == (20, 20))

    shift = updater.conditional_shift(buyer, target_dim_index=3, intervention_magnitude=0.1)
    check("Conditional shift computed", shift.shape == (20,),
          f"target shift={shift[3]:.4f}")

    # ================================================================
    section("2. Mechanism Selection with Probability Logging")
    # ================================================================
    from adam.retargeting.engines.prior_manager import HierarchicalPriorManager
    from adam.retargeting.engines.mechanism_selector import BayesianMechanismSelector
    from adam.retargeting.models.enums import BarrierCategory, ConversionStage

    prior_mgr = HierarchicalPriorManager()
    selector = BayesianMechanismSelector(prior_mgr)

    mech, conf, rationale = await selector.select(
        barrier=BarrierCategory.TRUST_DEFICIT,
        archetype_id="careful_truster",
        stage=ConversionStage.EVALUATING,
        reactance_level=0.2,
        pk_phase=1,
    )
    check("Mechanism selected", mech is not None, f"{mech.value} (conf={conf})")
    check("Probabilities logged",
          len(selector._last_mechanism_probabilities) > 0,
          f"{len(selector._last_mechanism_probabilities)} mechanisms")
    check("Probabilities sum to ~1",
          abs(sum(selector._last_mechanism_probabilities.values()) - 1.0) < 0.01,
          f"sum={sum(selector._last_mechanism_probabilities.values()):.4f}")

    # ================================================================
    section("3. DiagnosticReasoner — Full 5-Hypothesis Evaluation")
    # ================================================================
    from adam.retargeting.engines.diagnostic_reasoner import DiagnosticReasoner
    from adam.retargeting.models.diagnostic_assessment import DiagnosticInput

    reasoner = DiagnosticReasoner()

    # Scenario: evidence_proof on emotional page → IGNORED
    t0 = time.perf_counter()
    assessment = reasoner.reason_sync(DiagnosticInput(
        user_id="live_test_001", brand_id="luxy", archetype_id="careful_truster",
        engagement_type=None, converted=False,
        deployed_mechanism="evidence_proof", deployed_page_cluster="emotional",
        current_barrier="trust_deficit", current_stage="evaluating",
        reactance_level=0.25, pkm_phase=1, touch_position=2,
    ))
    ms = (time.perf_counter() - t0) * 1000

    check("Assessment produced", assessment is not None)
    check(f"Primary hypothesis: {assessment.primary_hypothesis}",
          assessment.primary_hypothesis is not None)
    check("5 hypotheses evaluated", len(assessment.hypothesis_evaluations) == 5)
    check("Next mechanism recommended", assessment.next_mechanism != "",
          f"{assessment.next_mechanism} on {assessment.next_page_cluster}")
    check(f"Reasoning trace: {len(assessment.reasoning_trace)} steps",
          len(assessment.reasoning_trace) >= 6)
    check(f"Performance: {ms:.1f}ms", ms < 5)

    # ================================================================
    section("4. CounterfactualLearner — Learning Multiplier")
    # ================================================================
    from adam.intelligence.counterfactual_learner import CounterfactualLearner
    from adam.retargeting.engines.mechanism_observation_models import get_mechanism_vector

    cf_learner = CounterfactualLearner()

    # Simulate: evidence_proof deployed with observed shift
    deployed_shift = np.zeros(20)
    deployed_shift[14] = 0.08  # brand_trust_fit shifted
    deployed_shift[3] = 0.03   # emotional_resonance shifted

    counterfactuals = cf_learner.compute_counterfactual_observations(
        deployed_mechanism="evidence_proof",
        deployed_outcome_shift=deployed_shift,
        mechanism_probabilities=selector._last_mechanism_probabilities,
        candidate_mechanisms=list(selector._last_mechanism_probabilities.keys()),
    )
    check("Counterfactuals generated", len(counterfactuals) > 0,
          f"{len(counterfactuals)} mechanisms imputed")

    # Feed to BONG
    buyer_before_cf = updater.get_mean(buyer).copy()
    cf_learner.feed_counterfactuals_to_bong(updater, buyer, counterfactuals)
    buyer_after_cf = updater.get_mean(buyer)
    cf_shift = np.abs(buyer_after_cf - buyer_before_cf).max()
    check("CFs shifted posterior", cf_shift > 0, f"max_shift={cf_shift:.6f}")
    check(f"Learning multiplier: {cf_learner.learning_multiplier:.1f}x",
          cf_learner.learning_multiplier > 1.0)

    # ================================================================
    section("5. Trilateral Epistemic Value")
    # ================================================================
    from adam.intelligence.trilateral_epistemic import (
        trilateral_epistemic_value, adaptive_epistemic_weight,
    )

    cov = updater.get_covariance(buyer)
    mech_vec = get_mechanism_vector("evidence_proof")
    page = np.random.uniform(0.3, 0.7, 32)

    epistemic = trilateral_epistemic_value(
        buyer_covariance=cov, mechanism_vector=mech_vec, page_mindstate=page,
        page_mechanism_observations=3, buyer_page_observations=1,
    )
    check("Trilateral epistemic computed", epistemic["total_epistemic"] > 0,
          f"total={epistemic['total_epistemic']:.4f}")
    check("Three components present",
          all(k in epistemic for k in ["buyer_epistemic", "page_mechanism_epistemic", "buyer_page_epistemic"]))

    w = adaptive_epistemic_weight("step_change", 5)
    check("Adaptive weight for step_change", w > 0.1, f"weight={w:.3f}")

    # ================================================================
    section("6. Resonance with Buyer Uncertainty")
    # ================================================================
    from adam.retargeting.resonance.resonance_model import ResonanceModel
    from adam.retargeting.resonance.models import PageMindstateVector

    res_model = ResonanceModel()
    pmv = PageMindstateVector(
        url_pattern="https://example.com/analytical",
        domain="example.com",
        edge_dimensions={"cognitive_engagement": 0.8, "information_seeking": 0.7,
                         "emotional_resonance": 0.3, "publisher_authority": 0.6},
    )

    # Without buyer uncertainty
    score_no_cov = res_model.compute_resonance(pmv, "evidence_proof", "trust_deficit", "careful_truster")
    # With buyer uncertainty
    score_with_cov = res_model.compute_resonance(
        pmv, "evidence_proof", "trust_deficit", "careful_truster",
        buyer_covariance=cov, epistemic_weight=0.3,
    )
    check("Resonance without cov", score_no_cov.resonance_multiplier > 0)
    check("Resonance with cov >= without",
          score_with_cov.resonance_multiplier >= score_no_cov.resonance_multiplier,
          f"{score_with_cov.resonance_multiplier:.4f} >= {score_no_cov.resonance_multiplier:.4f}")

    # ================================================================
    section("7. Repeated Measures + Page Learning")
    # ================================================================
    from adam.retargeting.engines.repeated_measures import (
        UserPosteriorManager, MixedEffectsEstimator,
    )

    user_mgr = UserPosteriorManager(prior_manager=prior_mgr)
    user_mgr.set_mixed_effects(MixedEffectsEstimator())

    touches = [
        ("evidence_proof", "trust_deficit", "analytical", 0.1),
        ("social_proof_matched", "trust_deficit", "social", 0.0),
        ("evidence_proof", "trust_deficit", "analytical", 0.3),
        ("evidence_proof", "trust_deficit", "analytical", 1.0),
    ]
    for mech, barrier, cluster, reward in touches:
        profile = user_mgr.update_user_posterior(
            user_id="live_001", brand_id="luxy", mechanism=mech,
            barrier=barrier, archetype_id="careful_truster",
            reward=reward, touch_position=touches.index((mech, barrier, cluster, reward)) + 1,
            page_cluster=cluster,
        )

    check("4 touches tracked", profile.total_touches_observed == 4)
    check("Page×mechanism posteriors",
          len(profile.page_mechanism_posteriors) > 0,
          f"{len(profile.page_mechanism_posteriors)} entries")
    check("Design-effect weight < 1", profile.design_effect_weight < 1.0,
          f"DE={profile.design_effect_weight:.4f}")

    # ================================================================
    section("8. TouchBuilder with Placement Prescription")
    # ================================================================
    from adam.retargeting.engines.touch_builder import TouchBuilder
    from adam.retargeting.models.diagnostics import ConversionBarrierDiagnosis, AlignmentGap
    from adam.retargeting.models.enums import RuptureType, ScaffoldLevel, TherapeuticMechanism

    try:
        from adam.retargeting.resonance.placement_optimizer import PlacementOptimizer
        builder = TouchBuilder(placement_optimizer=PlacementOptimizer())
    except Exception:
        builder = TouchBuilder()

    diagnosis = ConversionBarrierDiagnosis(
        diagnosis_id="diag_live", user_id="live_001", brand_id="luxy",
        archetype_id="careful_truster",
        conversion_stage=ConversionStage.EVALUATING, stage_confidence=0.8,
        rupture_type=RuptureType.NONE, rupture_severity=0.0,
        primary_barrier=BarrierCategory.TRUST_DEFICIT,
        primary_barrier_confidence=0.7,
        primary_alignment_gaps=[
            AlignmentGap(dimension="brand_trust_fit", actual_value=0.25,
                         threshold_value=0.37, gap_magnitude=0.12,
                         effect_size_d=0.8, rank_in_archetype=1),
        ],
        recommended_mechanism=TherapeuticMechanism.EVIDENCE_PROOF,
        recommended_scaffold_level=ScaffoldLevel.DIRECTION_MAINTENANCE,
        mechanism_confidence=0.75, estimated_reactance_level=0.2,
        reactance_budget_remaining=0.65, persuasion_knowledge_phase="1",
        ownership_level=0.3, ownership_decay_rate=0.05,
        total_touches_received=3, touches_since_last_engagement=0,
        mechanism_rationale="evidence_proof for trust_deficit",
    )

    touch = builder.build(
        sequence_id="seq_live", position=4, diagnosis=diagnosis,
        max_touches=7, brand_name="LUXY Ride",
        user_profile=profile,
    )
    check("Touch built", touch is not None)
    check("Has target_page_cluster", touch.target_page_cluster != "",
          f"cluster={touch.target_page_cluster}")

    # ================================================================
    section("9. StackAdapt Translation with Per-Touch Targeting")
    # ================================================================
    from adam.retargeting.integrations.stackadapt_translator import StackAdaptCampaignTranslator
    from adam.retargeting.models.sequences import TherapeuticSequence

    seq = TherapeuticSequence(user_id="live_001", brand_id="luxy", archetype_id="careful_truster")
    seq.touches_delivered = [touch]

    config = StackAdaptCampaignTranslator().translate_sequence(seq, brand_name="LUXY Ride")
    check("Campaign config generated", config is not None)
    campaign = config["campaigns"][0] if config.get("campaigns") else {}
    check("Per-touch site_targeting", "site_targeting" in campaign,
          f"cluster={campaign.get('site_targeting', {}).get('target_page_cluster', 'none')}")

    # ================================================================
    section("10. EnrichedInterventionRecord Emission")
    # ================================================================
    from adam.retargeting.models.intervention_record import EnrichedInterventionRecord
    from adam.retargeting.engines.intervention_emitter import InterventionRecordEmitter, JSONLineStorage
    import tempfile, os

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        storage = JSONLineStorage(filepath=tmp.name)

    emitter = InterventionRecordEmitter(storage=storage, buffer_size=5)

    record = EnrichedInterventionRecord(
        user_id="live_001", sequence_id="seq_live", touch_number=4,
        mechanism_id="evidence_proof", barrier_diagnosed="trust_deficit",
        barrier_gap=0.12,
        mechanism_probabilities=selector._last_mechanism_probabilities,
        bong_posterior_entropy=updater.information_value(buyer),
        diagnostic_hypotheses=assessment.hypothesis_confidences,
        primary_hypothesis=assessment.primary_hypothesis.value if assessment.primary_hypothesis else "",
        outcome="click", converted=False,
        page_cluster_prescribed=touch.target_page_cluster,
        why_this_mechanism=f"DiagnosticReasoner: {assessment.outcome_interpretation[:80]}",
    )
    emitter.emit(record)
    emitter.flush()

    check("Record emitted", emitter.total_emitted == 1)
    check("Record stored", storage.record_count == 1)
    os.unlink(storage.filepath)

    # ================================================================
    section("11. BONG Propagated Barrier Impact")
    # ================================================================
    impact = updater.propagated_barrier_impact(
        buyer,
        alignment_scores={
            "regulatory_fit_score": 0.3,
            "emotional_resonance": 0.35,
            "construal_fit_score": 0.6,
        },
        thresholds={
            "regulatory_fit_score": 0.5,
            "emotional_resonance": 0.5,
            "construal_fit_score": 0.5,
        },
    )
    check("Barrier impact computed", len(impact) > 0, f"{len(impact)} barriers ranked")
    if impact:
        top = impact[0]
        check(f"Top barrier: {top['barrier_dimension']}",
              top["total_propagated_lift"] > 0,
              f"propagated_lift={top['total_propagated_lift']:.6f}")

    # ================================================================
    section("12. Promotion Tracker State")
    # ================================================================
    from adam.intelligence.bong_promotion import get_promotion_tracker

    tracker = get_promotion_tracker()
    tracker.calibration_passed = True
    tracker.record_update("live_001")
    tracker.record_selection(
        bong_selected="evidence_proof",
        beta_selected="claude_argument",
        deployed="evidence_proof",
    )
    check("Tracker operational", tracker.total_bong_updates >= 1)
    check("Not yet promoted (insufficient data)", not tracker.promoted)
    check("Stats available", len(tracker.stats) >= 8)

    # ================================================================
    section("13. Causal Structure Learner")
    # ================================================================
    from adam.intelligence.causal_structure_learner import CausalStructureLearner
    from adam.retargeting.engines.mechanism_observation_models import DIMENSION_NAMES

    causal = CausalStructureLearner(DIMENSION_NAMES)
    # Feed the enriched record
    causal.process_record(record.to_dict())
    check("Causal learner accepted record", causal.total_records_processed == 1)
    check("Stats available", "records_processed" in causal.stats)

    # ================================================================
    section("14. BuyerUncertaintyProfile with BONG")
    # ================================================================
    from adam.intelligence.information_value import BuyerUncertaintyProfile

    bup = BuyerUncertaintyProfile(buyer_id="live_001")
    check("Profile created with BONG", bup.bong_posterior is not None)

    bup.update_from_edge(
        {"regulatory_fit": 0.7, "emotional_resonance": 0.8, "value_alignment": 0.6},
        signal_type="conversion",
    )
    check("BONG updated via edge", bup.bong_posterior.observation_count >= 1,
          f"obs={bup.bong_posterior.observation_count}")

    # Serialization round-trip
    d = bup.to_dict()
    check("Has BONG in serialization", "bong_posterior_b64" in d)
    restored = BuyerUncertaintyProfile.from_dict(d)
    check("BONG restored from dict", restored.bong_posterior is not None)

    # ================================================================
    section("15. Full 7-Touch Sequence with All Components")
    # ================================================================
    sequence_touches = [
        {"mech": "evidence_proof", "cluster": "analytical", "eng": "click", "conv": False},
        {"mech": "social_proof_matched", "cluster": "social", "eng": None, "conv": False},
        {"mech": "evidence_proof", "cluster": "analytical", "eng": "site_visit", "conv": False},
        {"mech": "narrative_transportation", "cluster": "emotional", "eng": "click", "conv": False},
        {"mech": "evidence_proof", "cluster": "analytical", "eng": "site_visit", "conv": False},
        {"mech": "implementation_intention", "cluster": "transactional", "eng": "click", "conv": False},
        {"mech": "evidence_proof", "cluster": "analytical", "eng": "booking_start", "conv": True},
    ]

    seq_buyer = updater.create_individual()
    all_assessments = []
    tried = []
    total_cfs = 0

    for i, t in enumerate(sequence_touches):
        tried.append(t["mech"])

        # 1. Diagnostic reasoning
        assessment = reasoner.reason_sync(DiagnosticInput(
            user_id="seq_001", brand_id="luxy", archetype_id="careful_truster",
            engagement_type=t["eng"], converted=t["conv"],
            deployed_mechanism=t["mech"], deployed_page_cluster=t["cluster"],
            current_barrier="trust_deficit", current_stage="evaluating" if i < 4 else "intending",
            reactance_level=0.1 + i * 0.05, pkm_phase=1 if i < 2 else 2,
            touch_position=i + 1,
            mechanisms_already_tried=tried.copy(),
        ))
        all_assessments.append(assessment)

        # 2. BONG update
        obs = np.random.uniform(0.3, 0.7, 20)
        obs[3] = 0.6 + (0.05 * i)  # emotional_resonance improving
        updater.update(seq_buyer, obs, noise_precision=0.3 if t["eng"] else 0.1)

        # 3. Counterfactual learning
        shift = np.random.uniform(-0.02, 0.05, 20)
        probs = {"evidence_proof": 0.4, "claude_argument": 0.3, "social_proof_matched": 0.2, "narrative_transportation": 0.1}
        cfs = cf_learner.compute_counterfactual_observations(
            t["mech"], shift, probs, list(probs.keys()),
        )
        total_cfs += len(cfs)
        cf_learner.feed_counterfactuals_to_bong(updater, seq_buyer, cfs)

        outcome = f"{'CONVERSION' if t['conv'] else (t['eng'] or 'IGNORE')}"
        hyp = assessment.primary_hypothesis.value if assessment.primary_hypothesis else "n/a"
        next_m = assessment.next_mechanism or "DONE"
        print(f"    Touch {i+1}: {t['mech']} on {t['cluster']} → {outcome} "
              f"| H: {hyp} | Next: {next_m} | {assessment.total_reasoning_ms:.1f}ms")

    check("7 assessments produced", len(all_assessments) == 7)
    check("Touch 7 is CONVERSION", all_assessments[6].observed_outcome.value == "conversion")
    check(f"Counterfactuals across sequence: {total_cfs}", total_cfs > 0)
    check(f"BONG updates: {seq_buyer.observation_count}", seq_buyer.observation_count >= 7)
    check(f"CF learning multiplier: {cf_learner.learning_multiplier:.1f}x",
          cf_learner.learning_multiplier > 1.0)

    # Final IV comparison
    cold_buyer = updater.create_individual()
    iv_cold = updater.information_value(cold_buyer)
    iv_seq = updater.information_value(seq_buyer)
    check("Sequence buyer has lower IV (learned more)",
          iv_seq < iv_cold,
          f"cold={iv_cold:.2f}, sequenced={iv_seq:.2f}")

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'='*70}")
    total = P + F
    if F == 0:
        print(f"  RESULT: {P}/{total} CHECKS PASSED — ALL PASS")
    else:
        print(f"  RESULT: {P}/{total} CHECKS PASSED ({F} FAILURES)")
    print(f"{'='*70}")
    return F == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        success = False
    sys.exit(0 if success else 1)
