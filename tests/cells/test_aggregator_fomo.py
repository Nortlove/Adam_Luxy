"""M.1 — aggregator-side fomo_score derivation tests.

Pin: compute_fomo_score correctness across the 4-modifier ×
scarcity-on/off × arousal-range matrix; aggregator integration
populates CellFeatureSet.fomo_score from priming inputs (replacing
W.2c-stub's 0.0 default); Q31 two-path consistency invariant
(M.1 aggregator-side compute equals C's PageMindstateVector
@property for matching logical inputs); FOMO seed predicates
fire end-to-end on real bid data.
"""
import random
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from adam.cells.aggregator import (
    CellFeaturesAggregator,
    FOMO_REGULATORY_NEUTRAL_MODIFIER,
    FOMO_REGULATORY_PREVENTION_MODIFIER,
    FOMO_REGULATORY_PROMOTION_MODIFIER,
    FOMO_SCARCITY_FRAME_NAME,
    compute_fomo_score,
)
from adam.cells.taxonomy import ConversionStage, RegulatoryFocus
from adam.cold_start.models.enums import ArchetypeID


# ---------------------------------------------------------------------------
# compute_fomo_score correctness
# ---------------------------------------------------------------------------

class TestComputeFomoScore:

    def test_high_arousal_scarcity_promotion_yields_0p96(self):
        """Matches C's smoke test: arousal=0.8 × 1.0 × 1.2 = 0.96."""
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=("scarcity",),
            regulatory_focus_priming=RegulatoryFocus.PROMOTION,
        )
        assert result == pytest.approx(0.96)

    def test_high_arousal_scarcity_prevention_yields_0p64(self):
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=("scarcity",),
            regulatory_focus_priming=RegulatoryFocus.PREVENTION,
        )
        assert result == pytest.approx(0.64)

    def test_high_arousal_scarcity_neutral_yields_0p8(self):
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=("scarcity",),
            regulatory_focus_priming=RegulatoryFocus.NEUTRAL,
        )
        assert result == pytest.approx(0.8)

    def test_no_scarcity_yields_zero(self):
        """Scarcity gates: no scarcity_indicator → product zeros."""
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=("social_proof",),
            regulatory_focus_priming=RegulatoryFocus.PROMOTION,
        )
        assert result == 0.0

    def test_zero_arousal_yields_zero(self):
        """Arousal gates: zero arousal → product zeros."""
        result = compute_fomo_score(
            arousal=0.0,
            activated_frames=("scarcity",),
            regulatory_focus_priming=RegulatoryFocus.PROMOTION,
        )
        assert result == 0.0

    def test_clips_at_one(self):
        """Saturation: arousal=0.95 × 1.0 × 1.2 = 1.14 → clipped to 1.0."""
        result = compute_fomo_score(
            arousal=0.95,
            activated_frames=("scarcity",),
            regulatory_focus_priming=RegulatoryFocus.PROMOTION,
        )
        assert result == 1.0

    def test_handles_string_regulatory_focus(self):
        """Caller may pass either RegulatoryFocus enum or raw string."""
        enum_result = compute_fomo_score(
            0.8, ("scarcity",), RegulatoryFocus.PROMOTION,
        )
        string_result = compute_fomo_score(
            0.8, ("scarcity",), "promotion",
        )
        assert enum_result == string_result == pytest.approx(0.96)

    def test_handles_none_activated_frames(self):
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=None,
            regulatory_focus_priming=RegulatoryFocus.PROMOTION,
        )
        assert result == 0.0

    def test_unknown_regulatory_focus_falls_to_neutral_modifier(self):
        """Defensive: unknown reg-focus value → NEUTRAL modifier (1.0)."""
        result = compute_fomo_score(
            arousal=0.8,
            activated_frames=("scarcity",),
            regulatory_focus_priming="not_a_real_focus",
        )
        assert result == pytest.approx(0.8)  # 0.8 × 1.0 × 1.0

    @pytest.mark.parametrize("arousal", [0.0, 0.25, 0.5, 0.75, 1.0])
    @pytest.mark.parametrize("scarcity_present", [True, False])
    @pytest.mark.parametrize("focus", [
        RegulatoryFocus.PROMOTION, RegulatoryFocus.PREVENTION,
        RegulatoryFocus.NEUTRAL,
    ])
    def test_range_invariant_fuzz(
        self, arousal, scarcity_present, focus,
    ):
        """Across realistic combinations, fomo_score ∈ [0, 1]."""
        frames = ("scarcity",) if scarcity_present else ()
        result = compute_fomo_score(arousal, frames, focus)
        assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# Q31 two-path consistency invariant — pinned
# ---------------------------------------------------------------------------

class TestTwoPathConsistencyInvariant:
    """Per Q31: aggregator-side compute_fomo_score must produce
    IDENTICAL values to C's PageMindstateVector.fomo_score @property
    for matching logical inputs. This is the structural contract
    keeping the bid-time and learning-time paths in sync."""

    @pytest.mark.parametrize("arousal", [0.0, 0.3, 0.5, 0.8, 1.0])
    @pytest.mark.parametrize("scarcity_present", [True, False])
    @pytest.mark.parametrize("focus_str", [
        "promotion", "prevention", "neutral",
    ])
    def test_aggregator_compute_matches_c_property_value(
        self, arousal, scarcity_present, focus_str,
    ):
        from adam.retargeting.resonance.models import PageMindstateVector

        # Build C-side PageMindstateVector
        c_pmv = PageMindstateVector(
            emotional_arousal=arousal,
            scarcity_frame_present=scarcity_present,
            regulatory_focus_priming=focus_str,
        )
        c_fomo = c_pmv.fomo_score

        # Build M.1-side aggregator inputs (logically equivalent)
        frames = ("scarcity",) if scarcity_present else ()
        m1_fomo = compute_fomo_score(
            arousal=arousal,
            activated_frames=frames,
            regulatory_focus_priming=focus_str,
        )

        assert m1_fomo == pytest.approx(c_fomo), (
            f"Q31 two-path consistency broken: "
            f"C @property = {c_fomo}, M.1 compute = {m1_fomo} "
            f"for arousal={arousal}, scarcity={scarcity_present}, "
            f"focus={focus_str}"
        )

    def test_constants_match_c_constants(self):
        """Pin: M.1 module-level constants exactly match C's
        PageMindstateVector @property constants. Drift here would
        silently break two-path consistency."""
        from adam.retargeting.resonance import models as c_module
        assert FOMO_REGULATORY_PROMOTION_MODIFIER == (
            c_module.FOMO_REGULATORY_PROMOTION_MODIFIER
        )
        assert FOMO_REGULATORY_PREVENTION_MODIFIER == (
            c_module.FOMO_REGULATORY_PREVENTION_MODIFIER
        )
        assert FOMO_REGULATORY_NEUTRAL_MODIFIER == (
            c_module.FOMO_REGULATORY_NEUTRAL_MODIFIER
        )
        assert FOMO_SCARCITY_FRAME_NAME == (
            c_module.FOMO_SCARCITY_FRAME_NAME
        )


# ---------------------------------------------------------------------------
# Aggregator integration
# ---------------------------------------------------------------------------

def _aggregator_with_priming(priming_obj):
    return CellFeaturesAggregator(
        archetype_accessor=lambda buyer_id: ArchetypeID.PRAGMATIST,
        posture_accessor=lambda url_hash: "INFORMATION_FORAGING",
        journey_accessor=lambda buyer_id: ConversionStage.UNAWARE,
        priming_accessor=lambda url_hash: priming_obj,
        mindstate_accessor=lambda buyer_id, url_hash: None,
        cohort_accessor=lambda buyer_id: (False, 0.5),
        maximizer_prior_accessor=lambda buyer_id, arch: (0.5, 10.0),
    )


class TestAggregatorIntegration:

    def test_priming_with_scarcity_promotion_populates_real_fomo(self):
        """W.2c stub left fomo_score=0.0; M.1 populates from priming."""
        priming = SimpleNamespace(
            valence=0.5, arousal=0.8,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("scarcity",),
        )
        agg = _aggregator_with_priming(priming)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.fomo_score == pytest.approx(0.96)

    def test_priming_none_yields_zero_fomo(self):
        """Cold-start (no priming) → fomo_score=0.0 (fail-soft)."""
        agg = _aggregator_with_priming(None)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.fomo_score == 0.0

    def test_priming_without_scarcity_yields_zero_fomo(self):
        priming = SimpleNamespace(
            valence=0.5, arousal=0.8,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("social_proof", "authority"),
        )
        agg = _aggregator_with_priming(priming)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.fomo_score == 0.0

    def test_explicit_mindstate_takes_precedence(self):
        """If a future M.2/M.3 wires a real mindstate accessor, its
        fomo_score takes precedence over the M.1 inline compute
        (preserves substrate-side override path)."""
        priming = SimpleNamespace(
            valence=0.5, arousal=0.8,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("scarcity",),
        )
        # Build aggregator with explicit mindstate having fomo_score=0.5
        # (which differs from M.1's compute of 0.96)
        explicit_mindstate = SimpleNamespace(
            fomo_score=0.5,
            psych_ownership_proxy=0.0,
            depletion_proxy=0.0,
            session_position_seconds=0.0,
            browsing_momentum=0.5,
        )
        agg = CellFeaturesAggregator(
            archetype_accessor=lambda buyer_id: ArchetypeID.PRAGMATIST,
            posture_accessor=lambda url_hash: "INFORMATION_FORAGING",
            journey_accessor=lambda buyer_id: ConversionStage.UNAWARE,
            priming_accessor=lambda url_hash: priming,
            mindstate_accessor=lambda buyer_id, url_hash: explicit_mindstate,
            cohort_accessor=lambda buyer_id: (False, 0.5),
            maximizer_prior_accessor=lambda buyer_id, arch: (0.5, 10.0),
        )
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        # Explicit mindstate's 0.5 overrides M.1's compute of 0.96
        assert fs.fomo_score == 0.5

    def test_aggregator_p99_latency_under_15ms_with_m1_compute(self):
        """Q22-revised aggregator budget: p99 < 15ms with M.1
        included (M.1 adds <100μs per call)."""
        priming = SimpleNamespace(
            valence=0.5, arousal=0.8,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("scarcity",),
        )
        agg = _aggregator_with_priming(priming)
        rng = random.Random(2026)
        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            agg.aggregate(
                buyer_id=f"u{rng.randint(1, 1000)}",
                url_hash=f"h{rng.randint(1, 1000)}",
            )
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 15000, (
            f"aggregator p99 {p99:.1f}μs with M.1 included exceeds "
            f"Q22-revised 15ms budget"
        )


# ---------------------------------------------------------------------------
# Predicate fire-rate end-to-end (M.0 Q30 correction → 5/6 post-M.1)
# ---------------------------------------------------------------------------

class TestPredicateFireRate:

    def test_high_fomo_promotion_predicate_fires_end_to_end(self):
        """Synthetic bid: priming(arousal=0.85, scarcity, promotion) →
        fomo_score=1.02 → 1.0 (clipped) → > 0.7 threshold +
        PROMOTION → high_fomo_promotion fires."""
        from adam.cells import evaluate_predicates
        priming = SimpleNamespace(
            valence=0.5, arousal=0.85,
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="promotion",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("scarcity",),
        )
        agg = _aggregator_with_priming(priming)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)
        assert "high_fomo_promotion" in modulation.fired_predicates
        assert modulation.class_boosts.get("scarcity") == 1.5

    def test_high_fomo_prevention_predicate_fires_end_to_end(self):
        """Synthetic bid with PREVENTION focus: fomo_score=0.85×0.8=0.68
        — JUST below 0.7 threshold. Need higher arousal to fire."""
        from adam.cells import evaluate_predicates
        priming = SimpleNamespace(
            valence=0.5, arousal=1.0,  # max arousal: 1.0×1.0×0.8=0.8
            cognitive_load_estimate=0.4,
            regulatory_focus_priming="prevention",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=("scarcity",),
        )
        agg = _aggregator_with_priming(priming)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)
        assert "high_fomo_prevention" in modulation.fired_predicates
        assert modulation.class_boosts.get("loss_aversion") == 1.4

    def test_neutral_priming_no_fomo_predicate_fires(self):
        """No scarcity in priming → fomo_score=0.0 → no FOMO predicate
        fires (regression invariant for cold-start path)."""
        from adam.cells import evaluate_predicates
        priming = SimpleNamespace(
            valence=0.0, arousal=0.5,
            cognitive_load_estimate=0.5,
            regulatory_focus_priming="neutral",
            persuasion_knowledge_activation=0.0,
            confidence_persuasion_knowledge=0.5,
            activated_frames=(),
        )
        agg = _aggregator_with_priming(priming)
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        modulation = evaluate_predicates(fs)
        assert "high_fomo_promotion" not in modulation.fired_predicates
        assert "high_fomo_prevention" not in modulation.fired_predicates


# ---------------------------------------------------------------------------
# Zero-regression on locked surfaces
# ---------------------------------------------------------------------------

class TestZeroRegressionOnLockedSurfaces:

    def test_pmv_fomo_property_unchanged(self):
        """C's PageMindstateVector.fomo_score @property is untouched
        per Q31 — outcome_handler learning paths still consume it."""
        from adam.retargeting.resonance.models import PageMindstateVector
        pmv = PageMindstateVector(
            emotional_arousal=0.8,
            scarcity_frame_present=True,
            regulatory_focus_priming="promotion",
        )
        assert pmv.fomo_score == pytest.approx(0.96)

    def test_w_chain_accessors_still_resolve(self):
        from adam.cells.accessors import (
            make_archetype_accessor, make_cohort_accessor,
            make_maximizer_prior_accessor,
        )
        for fn in [make_archetype_accessor, make_cohort_accessor,
                   make_maximizer_prior_accessor]:
            assert callable(fn)

    def test_default_aggregator_unchanged(self):
        """default_aggregator() factory still produces a working
        aggregator with all neutral defaults; no priming → fomo=0.0."""
        from adam.cells import default_aggregator
        agg = default_aggregator()
        fs = agg.aggregate(buyer_id="u", url_hash="h")
        assert fs.fomo_score == 0.0
        assert fs.archetype == ArchetypeID.PRAGMATIST

    def test_s62_cellfeatureset_schema_unchanged(self):
        """M.1 doesn't add a CellFeatureSet field — fomo_score
        existed pre-M.1 (defaulted to 0.0). Pin schema invariant."""
        from adam.cells.features import CellFeatureSet
        import dataclasses
        fields_by_name = {f.name: f for f in dataclasses.fields(CellFeatureSet)}
        assert "fomo_score" in fields_by_name
        assert fields_by_name["fomo_score"].default == 0.0
